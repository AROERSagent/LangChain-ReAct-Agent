"""
智扫通 · 智能客服前端。

界面能力：
- 实时推理过程：思考 / 工具调用 / 工具结果在流式过程中即时显示（方案 A）
- 会话列表：历史会话可切换、新建、删除（方案 B）
"""
import uuid

import streamlit as st
from agent.react_agent import ReactAgent
from db.database import init_db
from db.repository import (add_message, clear_conversation, conversation_exists,
                           create_conversation, delete_conversation,
                           get_or_create_conversation, list_conversations, load_messages)

st.set_page_config(page_title="智扫通 · 智能客服", page_icon="🤖", layout="centered")

# 建表幂等，放启动时执行，避免首次运行忘记初始化
init_db()

TOOL_LABELS = {
    "rag_summarize": "检索知识库",
    "web_search": "联网搜索",
    "get_user_id": "获取用户ID",
    "get_current_month": "获取当前月份",
    "fetch_external_data": "查询使用记录",
    "fetch_usage_range": "查询区间记录",
    "fill_context_for_report": "切换报告模式",
}


@st.cache_resource
def get_agent():
    """Agent 构建较重（模型 + 向量库），整个进程复用一份。"""
    return ReactAgent()


def get_session_key():
    """
    会话归属标识。

    ponytail: 浏览器会话级随机 key，未接登录体系 —— 清缓存即丢失，
    也不是真正的多用户隔离。接入认证后换成真实 user_id 即可，
    表结构不用改（靠 conversations.session_key 承载）。
    """
    if "session_key" not in st.session_state:
        st.session_state["session_key"] = uuid.uuid4().hex
    return st.session_state["session_key"]


def current_conversation_id():
    """取当前会话 id，首次进入时创建。"""
    key = get_session_key()

    cid = st.session_state.get("conversation_id")
    # 会话可能已在侧边栏被删除，这里做一次校验，避免指向不存在的 id
    if cid is None or not conversation_exists(cid):
        cid = get_or_create_conversation(key)
        st.session_state["conversation_id"] = cid

    return cid


def switch_conversation(cid: int):
    """切换当前会话。"""
    st.session_state["conversation_id"] = cid


def render_sources(sources):
    """渲染引用来源，显示命中文件和 rerank 分数。"""
    if not sources:
        return
    with st.expander(f"📚 引用来源（{len(sources)} 条）"):
        for s in sources:
            score = s.get("rerank_score")
            score_text = f" · 相关度 {score}" if score is not None else ""
            st.markdown(f"**{s['index']}. {s['file']}**{score_text}")
            st.caption(s["preview"])


# ------------------------------------------------------------------ 侧边栏：会话列表（方案 B）
with st.sidebar:
    st.subheader("💬 会话")

    if st.button("➕ 新建对话", use_container_width=True, type="primary"):
        new_id = create_conversation(get_session_key())
        switch_conversation(new_id)
        st.rerun()

    st.divider()

    conversations = list_conversations(get_session_key())
    active_id = current_conversation_id()

    if not conversations:
        st.caption("还没有对话，开始提问即可")
    else:
        for conv in conversations:
            is_active = conv["id"] == active_id
            # 当前会话加 ▶ 前缀做视觉标识
            label = f"{'▶ ' if is_active else ''}{conv['title']}"
            if len(label) > 28:
                label = label[:28] + "…"

            col_title, col_del = st.columns([5, 1])

            with col_title:
                if st.button(
                    label,
                    key=f"conv_{conv['id']}",
                    use_container_width=True,
                    help=f"{conv['message_count']} 条消息 · {conv['updated_at']:%Y-%m-%d %H:%M}",
                ):
                    switch_conversation(conv["id"])
                    st.rerun()

            with col_del:
                if st.button("🗑", key=f"del_{conv['id']}", help="删除该会话"):
                    delete_conversation(conv["id"])
                    # 删的是当前会话时，清掉指针让它重建
                    if conv["id"] == active_id:
                        st.session_state.pop("conversation_id", None)
                    st.rerun()

    st.divider()
    if st.button("清空当前对话", use_container_width=True):
        removed = clear_conversation(current_conversation_id())
        st.success(f"已删除 {removed} 条消息")
        st.rerun()

    st.caption("对话已存入数据库，刷新或重启都不会丢")


conversation_id = current_conversation_id()

# ------------------------------------------------------------------ 主区
st.title("🤖 智扫通机器人智能客服")
st.caption("基于 LangChain ReAct Agent + RAG 检索增强")

history_messages = load_messages(conversation_id)

# 空会话时给示例问题，降低演示门槛
if not history_messages:
    st.info("👋 你好！我是扫地机器人智能客服，可以帮你排查故障、推荐机型，也能根据你的使用数据生成报告。")
    st.markdown("**试试这些问题：**")
    samples = [
        "扫地机器人回充失败怎么办？",
        "小户型适合哪些扫地机器人？",
        "帮我生成 2025 年 6 月的使用报告",
    ]
    cols = st.columns(len(samples))
    for col, sample in zip(cols, samples):
        with col:
            if st.button(sample, use_container_width=True):
                st.session_state["pending_prompt"] = sample
                st.rerun()

# 回放历史（来自数据库，刷新后仍在）
for message in history_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        render_sources(message.get("sources"))

# 示例问题按钮点进来时，直接作为本轮输入
prompt = st.chat_input() or st.session_state.pop("pending_prompt", None)

if prompt:
    st.chat_message("user").markdown(prompt)
    add_message(conversation_id, "user", prompt)

    with st.chat_message("assistant"):
        sources = []
        answer_text = ""

        # ---------------------------------------------------------- 方案 A：实时推理过程
        # Streamlit 每次交互都会重跑脚本，实时刷新必须靠 status/empty 这类占位符承接。
        # 这里把思考与工具调用即时写进 status 容器，结束时自动折叠，不占正文空间。
        thinking_lines = []
        tool_log = []
        # 用可变容器承载来源：闭包里不能给外层变量重新赋值（nonlocal 在此作用域无效），
        # 改成往容器里写就绕开了这个限制
        result = {"sources": []}

        with st.status("🤔 正在理解你的问题...", expanded=True) as status:
            thinking_slot = st.empty()
            tool_slot = st.empty()

            # 历史从数据库读取后回传，实现真正的多轮上下文
            agent_history = [
                {"role": m["role"], "content": m["content"]}
                for m in load_messages(conversation_id)
                if m["role"] in ("user", "assistant")
            ]

            def on_event(event):
                """把非答案事件渲染到 status 容器。"""
                etype = event["type"]

                if etype == "thinking":
                    thinking_lines.append(event["content"])
                    thinking_slot.markdown("💭 " + " ".join(thinking_lines))
                    status.update(label="💭 正在推理...", state="running")

                elif etype == "tool_call":
                    label = TOOL_LABELS.get(event["name"], event["name"])
                    tool_log.append(f"🔧 **{label}** · `{event['args']}`")
                    tool_slot.markdown("\n\n".join(tool_log))
                    status.update(label=f"🔧 正在{label}...", state="running")

                elif etype == "tool_result":
                    label = TOOL_LABELS.get(event["name"], event["name"])
                    tool_log.append(f"　└─ {label} 返回结果")
                    tool_slot.markdown("\n\n".join(tool_log))

                elif etype == "sources":
                    result["sources"] = event["content"]

                elif etype == "error":
                    status.update(label="❌ 执行出错", state="error")
                    st.error(event["content"])

            def answer_stream():
                """把事件流分派给 on_event，只把 answer 交给 write_stream 渲染。"""
                for event in get_agent().execute_stream(prompt, history=agent_history):
                    if event["type"] == "answer":
                        yield event["content"]
                    else:
                        on_event(event)

            answer_text = st.write_stream(answer_stream())
            status.update(label="✅ 回答完成", state="complete", expanded=False)

        if answer_text:
            render_sources(result["sources"])

    add_message(conversation_id, "assistant", answer_text, sources=result["sources"])
    st.rerun()
