# -*- coding: utf-8 -*-
"""生成 AI 应用开发实习简历 PDF（版本 3）。

版面按原模板实测还原：A4、微软雅黑、左边距 36.85pt、正文 9.31pt、行距 13.85pt。
内容基于 RAG 与 Agent 两个真实项目源码重写，数据均可在项目 README / 配置中找到出处。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pdfkit_lite import (PDF, Font, FONT_REG, FONT_BOLD, MARGIN_X, RIGHT_EDGE,
                         TEXT_W, C_MAIN, C_ACCENT, C_BODY, C_GRAY)

OUT = Path(r"D:\简历\王建新-简历-AI应用开发实习3.pdf")
PHOTO = Path(r"D:\简历\_photo_clean.jpg")   # 原图裁掉底部水印后的版本

# 照片位置与尺寸：照搬原模板实测值（右上角，带浅灰细边框）
PHOTO_X, PHOTO_Y = 484.74067, 714.3307
PHOTO_W, PHOTO_H = 73.668239, 96.37799

BODY_SIZE = 9.31
LINE_H = 13.85


class Resume:
    def __init__(self):
        self.pdf = PDF()
        self.reg = Font(FONT_REG, "F1")
        self.bold = Font(FONT_BOLD, "F2")
        self.pdf.fonts = [self.reg, self.bold]
        self.y = 0.0

    # ---------- 版块 ----------
    def section(self, title, gap_before):
        self.y -= gap_before
        self.pdf.text(MARGIN_X, self.y, title, self.bold, 12, C_MAIN)
        rule_y = self.y - 6.0
        self.pdf.rect(MARGIN_X, rule_y, TEXT_W, 0.8, C_ACCENT)
        self.y = rule_y - 9.8

    def project_head(self, name, role, date, gap_before=13.6):
        self.y -= gap_before
        self.pdf.text(MARGIN_X, self.y, name, self.bold, 10.48, C_MAIN)
        # 日期右对齐；角色标签紧贴日期左侧
        date_w = self.reg.width(date, 10)
        self.pdf.text(MARGIN_X, self.y, role, self.bold, 9.22, C_GRAY,
                      right=RIGHT_EDGE - date_w - 12.0)
        self.pdf.text(MARGIN_X, self.y, date, self.reg, 10, C_BODY, right=RIGHT_EDGE)
        self.y -= 4.2

    # ---------- 正文段落（粗体小标题 + 正文，自动折行） ----------
    def para(self, lead, body):
        size = BODY_SIZE
        indent = size
        # 把 (字符, 是否粗体) 拆成字符流，便于统一折行
        stream = [(c, True) for c in lead] + [(c, False) for c in body]
        i = 0
        line_no = 0
        while i < len(stream):
            avail = TEXT_W if line_no == 0 else TEXT_W - indent
            x0 = MARGIN_X if line_no == 0 else MARGIN_X + indent
            # 贪心装入本行
            j = i
            w = 0.0
            while j < len(stream):
                ch, is_bold = stream[j]
                cw = self.bold.width(ch, size) if is_bold else self.reg.width(ch, size)
                if w + cw > avail:
                    break
                w += cw
                j += 1
            if j == i:                                     # 至少放一个字符，防止死循环
                j = i + 1

            if j < len(stream):
                nxt, _ = stream[j]
                # 中文断行：优先在标点/括号后断，避免把 "FastAPI" 这类词劈成 "FastAP|I"
                k = j
                while k > i + 1 and stream[k - 1][0] not in "，。、；：）」】%,;: ":
                    if stream[k - 1][0].isascii() and nxt.isascii():
                        k -= 1
                    else:
                        break
                if k > i + 1 and (j - k) <= 14:
                    j = k
                # 行首标点拉回上一行
                while j < len(stream) and stream[j][0] in "，。、；：）」】%":
                    j += 1

            self.y -= LINE_H
            self._emit(stream[i:j], x0, size)
            line_no += 1
            i = j

    def _emit(self, chars, x, size):
        # 按粗体/常规体分段绘制
        run, cur_bold = "", None
        for ch, is_bold in chars:
            if cur_bold is None or is_bold == cur_bold:
                run += ch
                cur_bold = is_bold
            else:
                self.pdf.text(x, self.y, run, self.bold if cur_bold else self.reg, size, C_BODY)
                x += (self.bold if cur_bold else self.reg).width(run, size)
                run, cur_bold = ch, is_bold
        if run:
            self.pdf.text(x, self.y, run, self.bold if cur_bold else self.reg, size, C_BODY)

    def item(self, lead, body):
        """一条项目要点。"""
        self.para(lead + "：", body)
def build():
    r = Resume()
    p = r.pdf
    reg, bold = r.reg, r.bold

    # ================= 照片 =================
    data = PHOTO.read_bytes()
    from PIL import Image as _Img
    with _Img.open(PHOTO) as im:
        px_w, px_h = im.size
    # 先描边再贴图，保证边框不被图片盖住
    p.rect(PHOTO_X, PHOTO_Y, PHOTO_W, PHOTO_H, (0.79, 0.84, 0.89))
    p.image(PHOTO_X, PHOTO_Y, PHOTO_W, PHOTO_H, data, px_w, px_h, "fzImg0")

    # ================= 抬头 =================
    r.y = 792.65
    p.text(MARGIN_X, r.y, "王建新", bold, 21.5, C_MAIN)

    r.y -= 18.27
    x = p.text(MARGIN_X + 2.6, r.y, "求职意向：", bold, 10, C_ACCENT)
    p.text(x, r.y, "AI 应用开发实习生", bold, 10, C_ACCENT)

    r.y -= 14.53
    p.text(MARGIN_X, r.y, "电话", bold, 9.4, C_ACCENT)
    p.text(MARGIN_X + 20.6, r.y, "13590909586", reg, 10, C_BODY)
    p.text(249.45, r.y, "邮箱", bold, 9.4, C_ACCENT)
    p.text(249.45 + 20.6, r.y, "3419372648@qq.com", reg, 10, C_BODY)

    r.y -= 13.78
    p.text(MARGIN_X, r.y, "年龄", bold, 9.4, C_ACCENT)
    p.text(MARGIN_X + 20.6, r.y, "21 岁", reg, 10, C_BODY)

    # ================= 教育背景 =================
    r.section("教育背景", gap_before=48.79)
    p.text(MARGIN_X, r.y, "肇庆学院", bold, 10.6, C_BODY)
    p.text(MARGIN_X, r.y, "2023.09 – 2027.06", reg, 10, C_BODY, right=RIGHT_EDGE)
    r.y -= 14.74
    p.text(MARGIN_X, r.y, "计算机科学与技术（本科）", bold, 10.6, C_BODY)
    r.y -= 13.68
    p.text(MARGIN_X, r.y, "核心课程：", bold, 9.5, C_BODY)
    p.text(MARGIN_X + bold.width("核心课程：", 9.5), r.y,
           "数据结构与算法、计算机网络、操作系统、数据库原理、Python 程序设计、人工智能",
           reg, 9.5, C_BODY)

    # ================= 项目经历 =================
    r.section("项目经历", gap_before=19.58)

    # ---- 项目一：RAG ----
    r.project_head("上市公司年报 RAG 智能问答系统", "独立开发", "2026.03 – 2026.06")
    r.para("项目简介：",
           "面向 A 股上市公司年报的检索增强问答系统，基于公开真实年报构建知识库，"
           "回答强制标注出处页码；后端 FastAPI（SSE 流式输出），前端 React + Vite。")
    r.item("混合检索与 RRF 融合",
           "向量检索与 BM25 关键词双路召回，以 rank_bm25 建词频索引、jieba 搜索模式分词，"
           "用 RRF 仅按排名融合，规避余弦距离与 BM25 分数量纲不可比带来的权重调参；"
           "BM25 零分候选直接丢弃，避免无区分度词条污染融合结果。")
    r.item("交叉编码器精排",
           "在融合结果之上用 bge-reranker-base 对候选做相关性精排，解决 RRF 无法识别"
           "「排名靠前但内容不相关」的问题；以 bge-small-zh-v1.5 本地向量化，Chroma 持久化检索。")
    r.item("评测与消融实验",
           "构建 30 题评测集并设三档检索配置，对比 Recall@k、MRR、上下文召回率与延迟，"
           "最终采用「默认混合检索、重排按需开启」的折中方案，兼顾效果与响应耗时。")
    r.item("数据质量治理",
           "定位部分年报因自定义 CID 字体编码导致的抽取乱码，横向对比 pdfplumber 与 PyMuPDF "
           "后改用后者修复；正则归一化中文字符间空白，修复被切碎的词语，保证 BM25 字面匹配可用。")
    r.item("评测口径校准",
           "发现页级命中指标因同一数据在摘要、正文、附注重复出现而存在假阴性，"
           "补充大模型判定的上下文召回率双指标报告；据此确认瓶颈在检索层而非生成层。")

    # ---- 项目二：Agent ----
    r.project_head("企业知识库智能体平台（ReAct Agent）", "独立开发", "2026.06 – 2026.09",
                   gap_before=25.0)
    r.para("项目简介：",
           "基于 LangChain create_agent 与 LangGraph 构建的 ReAct 智能体，"
           "将知识库检索、联网搜索、业务数据查询封装为工具，由模型自主决策调用链；"
           "Streamlit 构建流式对话界面，实时展示思考与工具执行过程。")
    r.item("RAG 工具化与引用溯源",
           "知识库检索封装为带来源留存的工具，回答结束统一回传引用片段；"
           "文档入库按 MD5 去重，Chroma 持久化，支持 txt / pdf 混合加载。")
    r.item("业务数据工具链",
           "用户与使用记录由 SQLite 经 SQLAlchemy 落库，提供单月与区间查询工具；"
           "查无数据时返回可用月份提示，引导模型重查而非臆造。")
    r.item("Agent 中间件设计",
           "基于 wrap_tool_call 统一监控工具调用与入参，基于 dynamic_prompt 按运行时上下文"
           "动态切换问答与报告两套 System Prompt，配置经 YAML 集中管理。")
    r.item("流式事件协议",
           "将模型原始流事件翻译为思考、工具调用、工具结果、最终回答的结构化事件，"
           "前端按类型分别渲染；合并连续 AIMessage 分片，避免答案被重复拼接。")
    r.item("稳定性控制",
           "设置递归步数上限约束工具调用深度；历史只回传 user / assistant 消息，"
           "避免工具中间结果累积导致上下文膨胀和指代偏移。")

    # ================= 专业技能 =================
    r.section("专业技能", gap_before=26.65)
    skills = [
        ("Python 工程：",
         "熟练异步编程（asyncio）与面向对象设计；熟悉 FastAPI 接口开发与 SSE 流式输出、"
         "Pydantic 校验，能完成 LLM 服务的接口设计、封装与部署。"),
        ("大模型应用开发：",
         "熟悉 OpenAI 兼容协议，能够调用大模型 API；掌握 Prompt 工程、结构化输出与流式生成。"),
        ("RAG 检索增强：",
         "掌握文档解析（PyMuPDF / pypdf）、分块策略、Embedding 向量化（bge-small-zh）与 Chroma；"
         "熟练 BM25 召回、RRF 融合与 Cross-Encoder 重排。"),
        ("Agent 智能体开发：",
         "理解 Agent 架构与状态机原理，熟悉 ReAct 循环、工具调用（Function Calling）、"
         "中间件扩展与多步任务编排。"),
        ("数据处理与工程化：",
         "熟悉 SQLite / SQLAlchemy 数据建模与查询优化、Git 版本管理；"
         "具备评测驱动开发经验（评测集搭建、消融实验、指标可复现）。"),
    ]
    for lead, body in skills:
        r.para(lead, body)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    p.save(OUT)
    print(f"saved: {OUT}  ({OUT.stat().st_size} bytes)")
    print(f"pages: {len(p.pages)}  bottom y: {r.y:.2f}")
    return r


if __name__ == "__main__":
    build()
