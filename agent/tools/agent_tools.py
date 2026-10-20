import os
from utils.logger_handler import logger
from langchain_core.tools import tool

from rag.rag_service import RagSummarizeService
import random
from db.repository import (available_months, list_known_users, query_usage_range,
                          query_usage_record)
from utils.config_handler import agent_conf
from utils.path_tool import get_abs_path


def _build_tavily_client():
    """
    构建 Tavily 搜索客户端。

    没配 Key 时不抛异常，而是返回 None：工具会回一句「不可用」，
    这样本地没配 Key 也能正常启动和演示其他功能。
    """
    if not os.getenv("TAVILY_API_KEY"):
        logger.warning("[web_search]未配置 TAVILY_API_KEY，联网搜索工具不可用")
        return None

    try:
        from langchain_tavily import TavilySearch
    except ImportError:
        logger.warning("[web_search]未安装 langchain-tavily，联网搜索工具不可用")
        return None

    return TavilySearch(max_results=agent_conf.get("tavily_max_results", 3))


rag = RagSummarizeService()
_tavily_client = _build_tavily_client()

month_arr = ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06",
             "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12", ]


# 记录最近一次 RAG 检索命中的来源，供前端做引用溯源。
# rag_summarize 返回给模型的是「总结后的答案」，本身不含文件名，
# 所以这里在工具内部把命中的片段留存下来，由 ReactAgent 在流结束后取走。
# ponytail: 模块级单键存储，不支持并发会话；多人同时用时需要按会话隔离。
last_rag_sources: list[dict] = []


@tool(description="从本地知识库（向量存储）中检索扫地/扫拖机器人的专业资料，适用于产品功能、故障排查、维护保养、选购建议等已有文档覆盖的问题")
def rag_summarize(query: str) -> str:
    answer, docs = rag.rag_summarize_with_sources(query)

    last_rag_sources.clear()
    last_rag_sources.extend(RagSummarizeService.format_sources(docs))

    return answer


@tool(description="联网搜索实时信息，适用于本地知识库没有覆盖的内容，例如具体型号对比、最新价格、上市新品、近期新闻或时效性要求高的信息")
def web_search(query: str) -> str:
    """调用 Tavily 联网搜索，返回拼接后的结果摘要字符串。"""
    if _tavily_client is None:
        # 没配 Key 时给出明确提示，让模型知道该工具不可用，而不是静默失败
        return "联网搜索不可用：未配置 TAVILY_API_KEY"

    try:
        response = _tavily_client.invoke({"query": query})
    except Exception as e:
        logger.error(f"[web_search]搜索失败：{str(e)}", exc_info=True)
        return f"联网搜索失败：{str(e)}"

    return _format_search_results(response)


def _format_search_results(response) -> str:
    """
    把 Tavily 的返回整理成紧凑的纯文本。

    工具返回值会原样进入模型的上下文，因此这里只保留标题、链接和正文摘要，
    并截断过长的正文，避免几条搜索结果就把上下文占满。
    """
    if isinstance(response, str):
        return response or "未搜索到相关内容"

    if not isinstance(response, dict):
        return str(response)

    results = response.get("results") or []
    if not results:
        return response.get("answer") or "未搜索到相关内容"

    parts = []
    for i, item in enumerate(results, start=1):
        title = item.get("title") or "无标题"
        url = item.get("url") or ""
        content = (item.get("content") or "").strip().replace("\n", " ")
        if len(content) > 300:
            content = content[:300] + "..."
        parts.append(f"【搜索结果{i}】{title}\n链接：{url}\n摘要：{content}")

    return "\n\n".join(parts)


# 不再提供写死的假天气/假定位：演示时无法自圆其说。
# 需要真实天气时让模型走 web_search 查，这样工具链是可验证的。


@tool(description="获取当前登录用户的ID，以纯字符串形式返回")
def get_user_id() -> str:
    """
    返回当前用户编号。

    用户集合来自数据库（原先是从写死的列表里 random.choice 随机挑一个）。
    ponytail: 尚未接入登录体系，这里仍取列表首个作为"当前用户"；
    接入认证后改成从会话上下文取真实 user_code 即可。
    """
    try:
        users = list_known_users(limit=1)
    except Exception as e:
        logger.error(f"[get_user_id]读取用户失败：{str(e)}", exc_info=True)
        return ""

    return users[0] if users else ""


@tool(description="获取当前月份，以纯字符串形式返回")
def get_current_month() -> str:
    """
    返回当前月份（YYYY-MM）。

    原实现是 random.choice 随机挑一个月份 —— 报告会随机落在任意月份，
    和「当前」这个语义不符，这里改为真实系统时间。
    """
    from datetime import datetime

    return datetime.now().strftime("%Y-%m")


@tool(description="从数据库中获取指定用户在指定月份的使用记录，以纯字符串形式返回，如果未检索到返回空字符串")
def fetch_external_data(user_id: str, month: str) -> str:
    """
    查询用户月度使用记录。

    数据来自数据库（原先是全量读进内存的 CSV）：
    CSV 方案每次都要把整份文件读成 dict，且多进程/多实例各读一份；
    换成表之后按 (user_id, month) 联合索引精确命中，只取需要的那一行。

    数据准备：首次使用前执行 python -m db.import_records 导入历史数据。
    """
    try:
        record = query_usage_record(user_id, month)
    except Exception as e:
        # 数据库不可用时不能让整个问答崩掉，返回空串由模型决定是否补查
        logger.error(f"[fetch_external_data]查询失败：{str(e)}", exc_info=True)
        return ""

    if record is None:
        logger.warning(f"[fetch_external_data]未能检索到用户：{user_id}在{month}的使用记录数据")

        # 关键：查不到时不能只回空串。示例数据的月份往往不是当前月份，
        # 只回空串会让模型凭空编一份报告；把「该用户实际有数据的月份」告诉它，
        # 模型才能改用正确的月份重查，或如实说明没有数据。
        try:
            months = available_months(user_id)
        except Exception:
            months = []

        if months:
            return (f"未找到用户{user_id}在{month}的记录。"
                    f"该用户有数据的月份为：{', '.join(months)}。"
                    f"请改用上述月份重新查询，不要臆造数据。")

        return f"未找到用户{user_id}在{month}的记录，且该用户没有任何历史数据。"

    return str(record)


@tool(description="按月份区间批量查询指定用户的使用记录，入参为start_month和end_month（格式YYYY-MM），返回按月排序的记录列表，用于分析使用趋势")
def fetch_usage_range(user_id: str, start_month: str, end_month: str) -> str:
    """
    区间查询。

    这是换成数据库之后才有的能力：CSV 方案要么全量加载再筛，
    要么逐个文件解析，都无法用一条 SQL 直接拿到一段时间的数据。
    """
    try:
        rows = query_usage_range(user_id, start_month, end_month)
    except Exception as e:
        logger.error(f"[fetch_usage_range]查询失败：{str(e)}", exc_info=True)
        return ""

    if not rows:
        logger.warning(f"[fetch_usage_range]用户{user_id}在{start_month}~{end_month}无记录")
        return ""

    return str(rows)

@tool(description="无入参，无返回值，调用后触发中间件自动为报告生成的场景动态注入上下文信息，为后续提示词切换提供上下文信息")
def fill_context_for_report():
    return "fill_context_for_report已调用"
