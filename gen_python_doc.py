# -*- coding: utf-8 -*-
"""生成 Python 面试题库 DOCX（AI 应用开发方向）。

按真实面试频率排序：async 并发、Pydantic、生成器、GIL/多进程多线程、httpx 超时重试
放在最前面，基础语法类放在后面。难度按实习岗控制。
"""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = Path(r"D:\简历\Python-面试题库-AI应用开发.docx")

MAIN = RGBColor(0x14, 0x50, 0x7F)
ACCENT = RGBColor(0x2F, 0x7E, 0xD8)
GRAY = RGBColor(0x40, 0x40, 0x40)
CODE_BG = "F3F5F8"


def set_font(run, size=10.5, bold=False, color=None, mono=False):
    name = "Consolas" if mono else "微软雅黑"
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    if color is not None:
        run.font.color.rgb = color


def shade(cell_or_para, hex_color):
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear")
    el.set(qn("w:fill"), hex_color)
    if hasattr(cell_or_para, "_tc"):
        cell_or_para._tc.get_or_add_tcPr().append(el)
    else:
        cell_or_para._p.get_or_add_pPr().append(el)


def add_rule(doc, color="2F7ED8", size=12):
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    b = OxmlElement("w:bottom")
    b.set(qn("w:val"), "single")
    b.set(qn("w:sz"), str(size))
    b.set(qn("w:space"), "1")
    b.set(qn("w:color"), color)
    pbdr.append(b)
    pPr.append(pbdr)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    return p


def h1(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(2)
    set_font(p.add_run(text), 15, True, MAIN)
    add_rule(doc)


def h2(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(9)
    p.paragraph_format.space_after = Pt(3)
    set_font(p.add_run(text), 11.5, True, ACCENT)


def body(doc, text, size=10.5, indent=0.0, color=GRAY, space_after=2):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.18
    if indent:
        p.paragraph_format.left_indent = Cm(indent)
    set_font(p.add_run(text), size, False, color)
    return p


def code(doc, lines):
    """代码块：等宽字体 + 浅灰底。"""
    for i, line in enumerate(lines):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(3 if i == 0 else 0)
        p.paragraph_format.space_after = Pt(3 if i == len(lines) - 1 else 0)
        p.paragraph_format.left_indent = Cm(0.55)
        p.paragraph_format.line_spacing = 1.05
        shade(p, CODE_BG)
        set_font(p.add_run(line if line else " "), 9, False, RGBColor(0x1A, 0x1A, 0x1A), mono=True)


def qa(doc, idx, question, answer, tag=None, code_lines=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(7)
    p.paragraph_format.space_after = Pt(1)
    set_font(p.add_run(f"{idx}. "), 10.5, True, MAIN)
    set_font(p.add_run(question), 10.5, True, RGBColor(0x1A, 0x1A, 0x1A))
    if tag:
        set_font(p.add_run(f"  [{tag}]"), 9, False, ACCENT)

    for line in answer:
        bp = doc.add_paragraph()
        bp.paragraph_format.space_before = Pt(0)
        bp.paragraph_format.space_after = Pt(1)
        bp.paragraph_format.line_spacing = 1.2
        bp.paragraph_format.left_indent = Cm(0.55)
        if line.startswith("- "):
            set_font(bp.add_run("• "), 10, False, ACCENT)
            set_font(bp.add_run(line[2:]), 10, False, GRAY)
        else:
            set_font(bp.add_run(line), 10, False, GRAY)

    if code_lines:
        code(doc, code_lines)


def build():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.left_margin = Cm(2.2)
    sec.right_margin = Cm(2.2)
    sec.top_margin = Cm(2.0)
    sec.bottom_margin = Cm(2.0)

    style = doc.styles["Normal"]
    style.font.name = "微软雅黑"
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    style.font.size = Pt(10.5)

    # ---------------- 封面 ----------------
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    set_font(p.add_run("Python 面试题库 · AI 应用开发方向"), 21, True, MAIN)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(8)
    set_font(p.add_run("按真实面试频率排序 ｜ 共 96 题 ｜ 难度：实习岗"), 10.5, False, ACCENT)

    body(doc,
         "说明：题目按「AI 应用开发岗实际问到的频率」排序，不是按课本顺序。"
         "async 并发、Pydantic 校验、生成器、GIL 与并发选型、httpx 超时重试这五块是重点，"
         "放最前面且给了可运行的代码；后面的基础语法题是为了防止「简单题答崩」——"
         "很多面试是先用简单题淘汰，再问深入题。")

    h2(doc, "怎么用这份题库")
    rows = [
        ("优先级", "第一、二章必须能写出代码；第三、四章能讲清原理；第六、七章扫一遍即可。"),
        ("答题方法", "先给一句话结论，再说为什么，最后给代码或报错场景。Python 题目面试官想看代码。"),
        ("动手验证", "代码块都是可以直接跑的，建议在本地跑一遍，尤其 async 和超时重试那几段。"),
    ]
    table = doc.add_table(rows=len(rows), cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (k, v) in enumerate(rows):
        c0, c1 = table.rows[i].cells
        c0.width = Cm(3.2)
        c1.width = Cm(13.2)
        shade(c0, "EAF2FB")
        set_font(c0.paragraphs[0].add_run(k), 9.5, True, MAIN)
        set_font(c1.paragraphs[0].add_run(v), 9.5, False, GRAY)

    doc.add_paragraph()

    # ================= 一、async/await 并发 =================
    h1(doc, "一、async / await 异步并发（AI 应用最高频）")
    body(doc, "调大模型 API 是典型的 I/O 等待，这章基本必问，而且一定会让你写代码。")

    qa(doc, 1, "什么是协程？async def 和普通 def 有什么区别？",
       ["协程是「可以暂停、之后继续执行」的函数，暂停点是 await。普通函数一旦调用就跑到底，中途不受控。",
        "调用 async def 的函数并不会执行函数体，只是返回一个协程对象；必须 await 它、"
        "或者塞进事件循环（asyncio.run / create_task / gather）才会真正跑。",
        "关键区别：普通函数是「调用即执行」，协程是「调用只是创建，await 才执行」。"], "必考")

    qa(doc, 2, "await 到底做了什么？为什么它不阻塞其他任务？",
       ["await 一个协程（或 Future）时，当前任务把控制权交还给事件循环，事件循环去跑别的就绪任务；"
        "等这件事的 I/O 完成，再回来继续。",
        "所以「不阻塞」的本质是：不是并行执行，而是「等待期间把 CPU 让给别人」。",
        "追问：如果你在协程里调用了阻塞函数（比如 time.sleep 或同步 requests），"
        "事件循环就被卡住，所有请求一起变慢——这是最常见的错误。"], "必考")

    qa(doc, 3, "怎么并发调用 10 个 LLM 接口？写出代码。",
       ["不能写成 10 个连续 await，那样是一个接一个串行，总耗时是 10 倍。",
        "正确做法是用 asyncio.gather 并发（或无上限并发），" "生产环境一定要加 Semaphore 限制并发数，防止被限流或打爆连接。",
        "", "要点：gather 返回顺序和传入顺序一致；return_exceptions=True 可以避免一个失败拖垮全部。"],
       "必考·手写", code_lines=[
           "import asyncio",
           "from typing import Any",
           "",
           "async def call_llm(prompt: str, sem: asyncio.Semaphore) -> Any:",
           "    async with sem:                       # 限制同时最多 N 个在跑",
           "        await asyncio.sleep(0.5)          # 假装是在调大模型 API",
           "        return f\"answer for {prompt}\"",
           "",
           "async def main(prompts: list[str]) -> list[Any]:",
           "    sem = asyncio.Semaphore(5)            # 生产环境必加",
           "    tasks = [call_llm(p, sem) for p in prompts]",
           "    return await asyncio.gather(*tasks, return_exceptions=True)",
           "",
           "if __name__ == \"__main__\":",
           "    print(asyncio.run(main([f\"q{i}\" for i in range(10)])))",
       ])

    qa(doc, 4, "asyncio.gather 和 create_task 有什么区别？",
       ["create_task 是「把协程注册进事件循环立即开始跑」，不等待结果；返回一个 Task。",
        "gather 是「等这一批任务全部完成」，本质上内部也是先 create_task 再统一 await。",
        "所以常见写法是先 create_task 起任务、再去干别的、最后 gather 收结果。",
        "注意：如果只是 create_task 却不保存引用，任务可能被垃圾回收掉，"
        "官方建议把引用存进一个集合里。"], "常考")

    qa(doc, 5, "asyncio.gather 和 asyncio.wait 有什么区别？",
       ["gather 直接返回结果列表，更常用；wait 返回 (done, pending) 两个集合，"
        "可以控制 FIRST_COMPLETED（谁先完成就先处理）。",
        "wait 在新版里要求传入 Task 而不是协程。",
        "需要「任一完成就继续」的场景（比如多模型选最快的那个）用 wait。"], "进阶")

    qa(doc, 6, "一个协程抛异常了会怎样？gather 怎么控制？",
       ["默认情况下 gather 里任一任务抛异常会立刻向上抛出，其他任务并不会被取消，继续在后台跑。",
        "传 return_exceptions=True 后，异常会作为结果值返回，不会中断其他任务。",
        "如果确实要「一个失败全取消」，就用 asyncio.TaskGroup（Python 3.11+），"
        "它会自动取消兄弟任务并抛出 ExceptionGroup。"], "常考")

    qa(doc, 7, "怎么给协程加超时？",
       ["用 asyncio.wait_for(coro, timeout=10)，超时会抛 asyncio.TimeoutError。",
        "Python 3.11+ 还可以用 asyncio.timeout() 上下文管理器，更简洁。",
        "注意 wait_for 超时时会 cancel 内部协程，如果你的清理逻辑写在 finally 里要小心 CancelledError。"],
       "常考", code_lines=[
           "async def main():",
           "    try:",
           "        res = await asyncio.wait_for(call_llm(\"hi\", sem), timeout=10)",
           "    except asyncio.TimeoutError:",
           "        res = \"降级回答\"                  # 超时兜底",
       ])

    qa(doc, 8, "同步的耗时函数（比如 requests、本地向量化）能在 async 里直接调吗？",
       ["不能直接调，会阻塞整个事件循环，所有并发请求都被拖慢。",
        "两种解法：一是换成异步库（requests → httpx.AsyncClient）；"
        "二是如果库本身没有异步版本，用 asyncio.to_thread 丢到线程池执行。",
        "CPU 密集的（向量化计算）应该用 run_in_executor 配 ProcessPoolExecutor，绕开 GIL。"],
       "必考", code_lines=[
           "import asyncio",
           "",
           "def blocking_io(): ...           # 同步库，没法改",
           "",
           "async def main():",
           "    result = await asyncio.to_thread(blocking_io)   # 丢线程池",
       ])

    qa(doc, 9, "FastAPI 里 async def 和普通 def 的接口有什么区别？",
       ["FastAPI 对 async def 路由在主事件循环里直接执行；",
        "对普通 def 路由会自动丢到线程池（anyio）里跑，所以同步阻塞代码写在 def 里反而不容易卡死。",
        "结论：路由里全是异步调用就写 async def；如果有同步阻塞调用，要么改异步，要么写成 def。"], "加分项")

    qa(doc, 10, "什么是事件循环？一个线程能有几个？",
       ["事件循环是异步的调度核心：不断检查有没有就绪的任务、到期定时器、完成的 I/O，然后推进它们。",
        "一个线程同时只能跑一个事件循环。asyncio.run() 会自动创建、运行、最后关闭。",
        "Jupyter 里 asyncio.run 报错「event loop is already running」就是因为已经有循环在跑。"], "基础")

    qa(doc, 11, "asyncio 适合 CPU 密集任务吗？",
       ["不适合。协程的价值在于「等待时能切换」，CPU 密集任务根本没有等待，切来切去反而是额外开销。",
        "而且一个线程里协程是串行的，不会用上多核。",
        "CPU 密集要么用多进程，要么用专门的库（numpy 内部释放 GIL、或者用 C 扩展）。"], "必考")

    # ================= 二、Pydantic =================
    h1(doc, "二、Pydantic 数据校验（FastAPI 标配）")

    qa(doc, 12, "Pydantic 是干什么的？为什么 FastAPI 离不开它？",
       ["基于类型注解做数据校验和解析：你声明字段类型，它负责把输入转成正确类型、"
        "校验不通过就抛出结构化的错误。",
        "FastAPI 用它做请求体校验、响应序列化，并自动生成 OpenAPI 文档。",
        "核心价值：把「校验」从手写一堆 if 变成声明式，且错误信息统一。"], "必考")

    qa(doc, 13, "BaseModel 和 dataclass 有什么区别？",
       ["dataclass 只帮你生成 __init__、__repr__，不做类型校验——传错类型它也照收。",
        "BaseModel 会做运行时校验、类型转换（\"123\" → 123）、支持嵌套模型、"
        "有 .dict() / .model_dump() 和 JSON Schema 导出。",
        "简单内部数据用 dataclass 更轻；对外接口、配置、LLM 结构化输出用 Pydantic。"], "常考")

    qa(doc, 14, "字段校验怎么写？约束、默认值、可选字段。",
       ["用 Field 给约束：长度、范围、正则等。",
        "注意区分 Optional 和默认值：Optional[X] 只是允许 None，不等于有默认值，必须显式给 = None。",
        "X | None 是 Python 3.10 的写法，等价于 Optional[X]。"], "常考",
       code_lines=[
           "from typing import Optional",
           "from pydantic import BaseModel, Field, field_validator",
           "",
           "class ChatRequest(BaseModel):",
           "    question: str = Field(..., min_length=1, max_length=500)",
           "    top_k: int | None = Field(default=None, ge=1, le=20)",
           "    tags: list[str] = Field(default_factory=list)   # 可变默认值必须用 factory",
       ])

    qa(doc, 15, "什么是自定义校验器？validator 和 field_validator 的区别？",
       ["Pydantic v1 用 @validator，v2 改用 @field_validator（并且要写 @classmethod）。",
        "校验器在类型转换之后执行，适合做业务规则：比如「结束时间必须晚于开始时间」。",
        "模型级的跨字段校验用 @model_validator(mode=\"after\")。"], "必考",
       code_lines=[
           "from pydantic import BaseModel, field_validator",
           "",
           "class User(BaseModel):",
           "    email: str",
           "",
           "    @field_validator(\"email\")",
           "    @classmethod",
           "    def check_email(cls, v: str) -> str:",
           "        if \"@\" not in v:",
           "            raise ValueError(\"邮箱格式不对\")",
           "        return v",
       ])

    qa(doc, 16, "Pydantic v1 和 v2 有哪些主要变化？",
       ["最明显的是重命名：.dict() → .model_dump()、.json() → .model_dump_json()、"
        "parse_obj → model_validate、Config 类 → model_config。",
        "校验器从 validator/root_validator 改成 field_validator/model_validator。",
        "v2 的核心用 Rust 重写，校验速度快了很多。",
        "面试小技巧：说清你项目用的是哪个版本，能体现你真的用过。"], "常考")

    qa(doc, 17, "model_dump() 和 model_dump_json() 有什么区别？",
       ["model_dump() 返回 dict，里面的嵌套模型已经递归转成 dict，但 datetime 等还是 Python 对象。",
        "model_dump_json() 直接返回 JSON 字符串，所有类型都按 JSON 规则序列化。",
        "如果要把结果塞进数据库 JSON 字段或返回响应，用后者更省事。"], "细节")

    qa(doc, 18, "遇到额外字段怎么办？（比如前端多传了字段）",
       ["默认是 ignore：多余的字段直接丢掉，不报错。",
        "严格模式可以设 model_config = ConfigDict(extra=\"forbid\")，多传就报错——"
        "对外接口建议这样，能及早发现调用方的问题。",
        "还有 extra=\"allow\"，全部保留。"], "追问")

    qa(doc, 19, "怎么校验嵌套结构和列表？",
       ["直接用类型注解声明：字段类型写成 list[Item] 或嵌套的 BaseModel，Pydantic 会递归校验。",
        "优点是错误信息会带出具体是哪个下标、哪个字段出错，前端能精准定位。"], "基础",
       code_lines=[
           "class Source(BaseModel):",
           "    company: str",
           "    page: int | None = None",
           "",
           "class ChatResponse(BaseModel):",
           "    answer: str",
           "    sources: list[Source] = []",
       ])

    qa(doc, 20, "Pydantic 怎么和 LLM 的结构化输出结合？",
       ["把 Pydantic 模型当成 schema 传给模型（或让模型按这个 JSON 结构输出），拿到结果后用 "
        "Model.model_validate(json.loads(text)) 解析。",
        "解析失败就捕获 ValidationError，把错误信息喂回给模型让它重试——这是最实用的兜底。",
        "好处是：格式约束有代码保证，不是靠提示词碰运气。"], "AI 结合",
       code_lines=[
           "try:",
           "    data = Score.model_validate_json(raw_text)",
           "except ValidationError as e:",
           "    # 把 e 拼进下一轮提示词，让模型修正格式后重试",
           "    ...",
       ])

    qa(doc, 21, "Pydantic 校验和 FastAPI 返回 422 的关系？",
       ["请求体校验失败时，FastAPI 自动返回 HTTP 422，响应里带上每个字段的错误位置和原因。",
        "不需要你写 try/except，这是 FastAPI + Pydantic 最省事的地方。",
        "如果想让错误格式符合公司规范，可以自定义 exception handler 覆盖默认输出。"], "常考")

    # ================= 三、生成器与迭代器 =================
    h1(doc, "三、生成器与迭代器")

    qa(doc, 22, "可迭代对象、迭代器、生成器，三者的区别？",
       ["可迭代对象（Iterable）：能用于 for 的东西，实现了 __iter__。list、dict、str 都是。",
        "迭代器（Iterator）：实现了 __iter__ 和 __next__，有状态，只能往前走一次。",
        "生成器（Generator）：用 yield 或生成器表达式写出来的迭代器，是一种简洁的实现方式。",
        "关系是：可迭代对象 → iter() → 迭代器；生成器是迭代器的一种。"], "必考")

    qa(doc, 23, "为什么迭代器只能遍历一次？",
       ["因为迭代器内部维护了「当前位置」这个状态，next 一次就往前走一格，走到最后抛 StopIteration。",
        "之后它的位置就停在末尾了，再遍历拿不到东西。想要重新遍历就重新调用 iter() 生成新的迭代器（如果源可迭代）。",
        "典型坑：把 generator 传给两个函数，第二个函数什么都拿不到。"], "常考")

    qa(doc, 24, "yield 和 return 有什么区别？",
       ["return 结束函数、返回一个值，函数就没了；",
        "yield 是「抛出一个值并暂停」，函数现场（局部变量、执行位置）都被保存，下次 next 时从这里继续。",
        "所以生成器函数可以被多次推进，这是它和普通函数最根本的区别。"], "必考")

    qa(doc, 25, "为什么流式输出要用生成器？写出一个流式接口。",
       ["生成器是惰性的，来一个吐一个，不用把所有内容都攒在内存里。",
        "大模型流式输出正好是「模型吐一个 token、我们转发一个」，天然匹配。",
        "而且生成器可以和异步结合成 async generator（async for），FastAPI 的 SSE 就是这么做的。"],
       "必考·AI 场景", code_lines=[
           "# 同步输出流",
           "def stream_answer(prompt: str):",
           "    for chunk in call_llm_stream(prompt):",
           "        yield chunk",
           "",
           "# 异步输出流（FastAPI SSE 常用）",
           "async def stream_answer_async(prompt: str):",
           "    async for chunk in call_llm_stream_async(prompt):",
           "        yield chunk",
       ])

    qa(doc, 26, "什么是生成器表达式？和列表推导式有什么区别？",
       ["写法是 (x*2 for x in range(10))，圆括号；列表推导式是方括号。",
        "列表推导式会立刻算出所有元素放进内存；生成器表达式只返回生成器，用到才算。",
        "数据量大或者只是要遍历一次时，用生成器表达式省内存。"], "基础")

    qa(doc, 27, "yield from 是干什么的？",
       ["把子生成器的 yield 委托出去，避免写 for 循环手动转发。",
        "递归遍历树结构、或者把一个生成器接在另一个里面时特别有用。",
        "它还会把异常和返回值一起透传，比手写 for 更完整。"], "进阶")

    qa(doc, 28, "send() 和 yield 能双向通信吗？",
       ["可以。yield 可以接收 send 传进来的值：value = yield x。第一次必须先 next() 或 send(None) 启动。",
        "用途是协程的雏形——asyncio 底层的协程就是基于生成器这套机制演进来的。",
        "实习岗能讲清「yield 既能发出也能接收」就够了，不用深挖。"], "进阶")

    qa(doc, 29, "生成器的常见坑有哪些？",
       ["- 只能遍历一次，重复用会拿到空；",
        "- 生成器里抛异常，会让生成器结束，后续取不到值；",
        "- 生成器被提前关闭（close）时，没走到 finally 的清理逻辑要留心；",
        "- 生成器函数里如果有 return 值，那个值是 StopIteration.value，正常 for 拿不到。"], "加分项")

    # ================= 四、GIL 与并发选型 =================
    h1(doc, "四、GIL 与多进程 / 多线程 / 协程的选择")

    qa(doc, 30, "什么是 GIL？",
       ["GIL（全局解释器锁）是 CPython 的一把锁：同一时刻只允许一个线程执行 Python 字节码。",
        "所以多线程不能把纯 Python 计算跑得更快，它在同一进程内是「并发但不并行」。",
        "它是 CPython 的实现细节，不是 Python 语言规范；Jython、PyPy 行为不同。"], "必考")

    qa(doc, 31, "有了 GIL，为什么多线程还能加速？",
       ["因为 GIL 在遇到 I/O 阻塞时会主动释放：网络请求、文件读写、sleep 期间别的线程可以跑。",
        "所以 I/O 密集型任务用多线程是有效的。",
        "另外 numpy 这类 C 扩展在计算时会手动释放 GIL，所以某些数值计算多线程也有收益。"], "必考")

    qa(doc, 32, "CPU 密集和 I/O 密集，分别该用什么并发模型？",
       ["CPU 密集（大量计算、图像处理、本地向量化）→ 多进程（ProcessPoolExecutor），绕开 GIL。",
        "I/O 密集且大量（成百上千个网络请求）→ 协程（asyncio），开销最小。",
        "I/O 密集但并发不高、或者必须在同步代码里用 → 多线程（ThreadPoolExecutor）。",
        "一句话总结：CPU 密集多进程，高并发 I/O 用协程，同步代码兼容用线程。"], "必考")

    qa(doc, 33, "多进程有什么代价？",
       ["进程间内存不共享，数据要序列化传输（pickle），开销比线程大；",
        "启动慢，Windows 上还有 spawn 方式的额外开销，函数必须可被 pickle；",
        "共享状态要用 Queue、Manager 这类机制，开发复杂度高。",
        "所以不是越多越好，进程数一般等于 CPU 核数。"], "常考")

    qa(doc, 34, "写一个「I/O 用线程池、CPU 用进程池」的例子。",
       ["线程池和进程池的接口几乎一样，都是 submit / map，区别只在 Executor 类型。",
        "在 asyncio 里可以用 loop.run_in_executor 把两者接进事件循环。"], "常考",
       code_lines=[
           "from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor",
           "",
           "# I/O 密集：调外部接口",
           "with ThreadPoolExecutor(max_workers=20) as pool:",
           "    results = list(pool.map(fetch_url, urls))",
           "",
           "# CPU 密集：纯计算，绕开 GIL",
           "with ProcessPoolExecutor() as pool:",
           "    results = list(pool.map(heavy_compute, items))",
       ])

    qa(doc, 35, "线程安全是什么？list 的 append 安全吗？",
       ["线程安全指多个线程同时操作同一份数据不会出错。",
        "CPython 里 list.append 因为受 GIL 保护，单次操作是原子的，但这只保证「不崩溃」，"
        "不保证「逻辑正确」——比如 check-then-act（先判断再修改）就不是原子的。",
        "正确做法是用 Lock，或者改用 queue.Queue（内部已加锁）。"], "常考")

    qa(doc, 36, "什么是死锁？怎么避免？",
       ["两个线程各持一把锁，又都在等对方释放，谁都走不下去。",
        "避免方法：固定加锁顺序、用超时加锁（acquire(timeout=...)）、减少持锁时间、尽量不用嵌套锁。",
        "Python 3.11 之前还有 GIL 死锁的极端情况，一般面试不追问到这一层。"], "基础")

    qa(doc, 37, "全局变量在多线程里怎么改才安全？",
       ["用 threading.Lock 包住临界区。",
        "更简单的做法是用 queue.Queue 传数据，避免共享状态。",
        "用 concurrent.futures 的 Future 收集结果，而不是让线程往共享 list 里 append（虽然 append 本身原子，但顺序不确定）。"], "常考")

    qa(doc, 38, "Python 3.13 的 free-threaded 模式是什么？（可以只提一句）",
       ["官方在做的「去除 GIL」实验版本（PEP 703），可以真正多线程并行。",
        "目前是实验特性，生态兼容性还在推进。",
        "面试时提一句「了解这个方向，但生产还没大规模用」就够，答不出反而扣分。"], "加分项")

    # ================= 五、requests / httpx 超时重试 =================
    h1(doc, "五、requests / httpx 超时与重试")

    qa(doc, 39, "requests 的超时参数为什么一定要显式传？",
       ["requests 默认没有超时，连接不上时会一直挂着，线程就被永久占住。",
        "这是线上事故的常见来源：某次网络抖动之后，线程池慢慢被占满，服务像死了一样。",
        "所以规范要求每次请求都必须传 timeout。"], "必考")

    qa(doc, 40, "connect 超时和 read 超时有什么区别？",
       ["connect 是「建立 TCP 连接」的时间，反映网络是否可达；",
        "read 是「连接建立后等数据返回」的时间，反映服务端处理速度。",
        "写 timeout=(3, 60) 表示连接 3 秒、读取 60 秒。",
        "大模型接口延迟高，read 要设大；但连接超时应该短，快速失败。"], "必考")

    qa(doc, 41, "重试应该怎么做？为什么不能无脑重试？",
       ["无脑重试会放大故障：服务已经过载了，你还翻倍打过去。",
        "正确做法：",
        "- 只对幂等操作重试（GET 可以，POST 可能重复下单）；",
        "- 用指数退避 + 随机抖动，避免所有客户端同一时刻重试（惊群）；",
        "- 限制最大次数和总时长，超过就降级。",
        "用 urllib3 的 Retry 能省事，但要配置 allowed_methods 和 status_forcelist。"], "必考",
       code_lines=[
           "import requests",
           "from requests.adapters import HTTPAdapter",
           "from urllib3.util.retry import Retry",
           "",
           "session = requests.Session()",
           "retry = Retry(",
           "    total=3,",
           "    backoff_factor=0.5,                       # 0.5s, 1s, 2s 递增",
           "    status_forcelist=[429, 500, 502, 503, 504],",
           "    allowed_methods=[\"GET\", \"POST\"],        # 谨慎：POST 不一定幂等",
           "    raise_on_status=False,",
           ")",
           "session.mount(\"https://\", HTTPAdapter(max_retries=retry))",
           "resp = session.get(url, timeout=(3, 30))",
       ])

    qa(doc, 42, "为什么调 LLM 接口更喜欢 httpx 而不是 requests？",
       ["httpx 原生支持 async，可以在协程里并发调用，不阻塞事件循环。",
        "requests 只有同步版本，在 FastAPI 的 async 路由里用会卡住整个服务。",
        "httpx 的接口和 requests 非常像，迁移成本低。",
        "第三方 SDK（openai、langchain）底层现在大多也是 httpx。"], "必考")

    qa(doc, 43, "用 httpx.AsyncClient 写一个带超时和重试的调用。",
       ["AsyncClient 要复用（建连接池），不要每次请求都新建一个。",
        "推荐用 httpx.Timeout 分别设置连接、读、写、连接池的超时。",
        "重试可以手动写，也可以用库（如 tenacity 或 httpx-retry）。"], "必考·手写",
       code_lines=[
           "import asyncio",
           "import httpx",
           "",
           "async def call_llm(client: httpx.AsyncClient, prompt: str) -> str:",
           "    timeout = httpx.Timeout(connect=3.0, read=60.0, write=10.0, pool=5.0)",
           "    for attempt in range(3):",
           "        try:",
           "            r = await client.post(",
           "                \"/chat/completions\",",
           "                json={\"messages\": [{\"role\": \"user\", \"content\": prompt}]},",
           "                timeout=timeout,",
           "            )",
           "            r.raise_for_status()",
           "            return r.json()[\"choices\"][0][\"message\"][\"content\"]",
           "        except (httpx.TimeoutException, httpx.HTTPStatusError) as e:",
           "            if attempt == 2:",
           "                raise",
           "            await asyncio.sleep(0.5 * 2 ** attempt)   # 指数退避",
       ])

    qa(doc, 44, "为什么一定要复用 Client / Session？",
       ["每个 Client 都有自己的连接池，新建一次的代价包括 TCP 握手、TLS 握手，很贵。",
        "复用之后连接可以 keep-alive，请求延迟能降一大截。",
        "用 with httpx.AsyncClient() as client: 或者放在应用生命周期里单例持有。",
        "注意：Client 不能跨事件循环共用，多进程时要各自创建。"], "常考")

    qa(doc, 45, "调大模型接口时，还有哪些稳定性设计？",
       ["- 超时分级：连接超时短、读超时长；",
        "- 重试只针对 5xx 和 429（限流），4xx 参数错误重试没用；",
        "- 遇到 429 优先读服务端返回的 Retry-After；",
        "- 熔断降级：连续失败就切备用模型或返回兜底话术；",
        "- 限流：本地 Semaphore + 全局令牌桶，控制 QPS；",
        "- 记录每次调用的耗时、token 数、失败原因，方便排查。"], "加分项")

    qa(doc, 46, "怎么处理流式响应（SSE）？",
       ["用 stream 上下文管理器读取，边读边处理，不要等全部返回。",
        "流式场景下「超时」的语义要改：应该用「空闲超时」（多久没收到新数据）而不是总时长。",
        "断流要能恢复重试，或者至少保证前端能感知到异常结束。"], "进阶",
       code_lines=[
           "async with client.stream(\"POST\", url, json=payload, timeout=timeout) as r:",
           "    async for line in r.aiter_lines():",
           "        if line.startswith(\"data: \"):",
           "            chunk = line[6:]",
           "            if chunk == \"[DONE]\":",
           "                break",
           "            yield chunk",
       ])

    # ================= 六、基础语法（防止栽在简单题上） =================
    h1(doc, "六、基础语法（简单题更要答准）")
    body(doc, "面试常先用这类题筛人。答不快、答不准比答不出更掉分。")

    qa(doc, 47, "元组和列表有什么区别？",
       ["可变性：list 可增删改，tuple 创建后不能改。",
        "语法：[] 和 ()，单元素元组要写 (1,) 否则就是括号里的数字。",
        "用途：列表放同类可变数据；元组常表示「结构固定的记录」（如坐标、返回值），"
        "也可以当字典的 key，因为可哈希。",
        "性能上元组更省内存、创建更快。"], "必考")

    qa(doc, 48, "元组真的完全不可变吗？",
       ["元组本身的「引用」不可变，但如果里面存了可变对象（比如一个列表），那个列表的内容是可以改的。",
        "所以严格说是「浅不可变」。",
        "另外 += 对元组是新对象，所以 a += (1,) 之后 id(a) 变了。"], "加分项")

    qa(doc, 49, "深拷贝和浅拷贝的区别？",
       ["浅拷贝只复制最外层容器，里面的元素还是同一个引用（copy.copy 或 list[:]）；",
        "深拷贝递归复制所有层级（copy.deepcopy）。",
        "经典坑：[[0]*3]*3 建出来的列表，三行是同一个对象，改一个全变。"], "必考",
       code_lines=[
           "a = [[0] * 3] * 3",
           "a[0][0] = 1",
           "print(a)        # [[1, 0, 0], [1, 0, 0], [1, 0, 0]]  三行都变了",
           "",
           "b = [[0] * 3 for _ in range(3)]   # 正确写法",
       ])

    qa(doc, 50, "is 和 == 的区别？",
       ["== 比较值是否相等（调用 __eq__），is 比较是不是同一个对象（比较 id）。",
        "小整数（-5~256）和部分短字符串会被驻留，所以 a is b 有时为 True，但这是实现细节，不能依赖。",
        "判断 None 一定用 is None，不用 == None。"], "必考")

    qa(doc, 51, "可变对象能当字典的 key 吗？",
       ["不能。dict 的 key 必须可哈希，而 list、dict、set 都是可变的、不可哈希。",
        "tuple 可以当 key，前提是里面所有元素也都可哈希。"], "基础")

    qa(doc, 52, "字符串为什么不可变？",
       ["不可变才能安全地当字典 key、才能被安全共享（多个变量指向同一个字符串）。",
        "也便于解释器做驻留优化。",
        "所以大量拼接字符串要用 join 或列表收集，而不是在循环里 +=。"], "基础")

    qa(doc, 53, "*args 和 **kwargs 是什么？",
       ["*args 收集多余的位置参数成元组，**kwargs 收集多余的关键字参数成字典。",
        "函数定义里出现是「收集」，函数调用里出现是「解包」。",
        "参数顺序固定：位置参数 → 默认参数 → *args → 仅关键字参数 → **kwargs。"], "必考")

    qa(doc, 54, "什么是装饰器？写一个带参数的装饰器。",
       ["装饰器本质是「接收函数、返回函数」的高阶函数，用来在不改原函数代码的前提下加功能（日志、计时、重试）。",
        "带参数的装饰器要多一层：最外层接收参数，返回真正的装饰器。",
        "记得用 functools.wraps 保留原函数的名字和文档。"], "必考",
       code_lines=[
           "import functools, time",
           "",
           "def timer(prefix: str):",
           "    def deco(func):",
           "        @functools.wraps(func)",
           "        def wrapper(*args, **kwargs):",
           "            start = time.perf_counter()",
           "            try:",
           "                return func(*args, **kwargs)",
           "            finally:",
           "                print(f\"{prefix} {func.__name__} 耗时 {time.perf_counter()-start:.3f}s\")",
           "        return wrapper",
           "    return deco",
       ])

    qa(doc, 55, "闭包是什么？会踩什么坑？",
       ["闭包是「内部函数引用了外部函数的变量」，外层函数返回后这些变量依然被保留。",
        "经典坑是在循环里创建闭包，所有闭包共享同一个变量，最后都取到循环结束时的值。",
        "解决：用默认参数把值绑进去，或者用 functools.partial。"], "常考",
       code_lines=[
           "funcs = [lambda: i for i in range(3)]",
           "print([f() for f in funcs])          # [2, 2, 2] 不是 [0, 1, 2]",
           "funcs = [lambda i=i: i for i in range(3)]",
           "print([f() for f in funcs])          # [0, 1, 2]",
       ])

    qa(doc, 56, "Python 的变量作用域规则？",
       ["LEGB：Local（局部）→ Enclosing（闭包外层）→ Global（全局）→ Built-in（内置）。",
        "函数内部给变量赋值会创建局部变量；要改全局变量得用 global，要改外层函数变量用 nonlocal。",
        "只读全局变量不用声明，只有赋值才需要。"], "常考")

    qa(doc, 57, "默认参数为什么不能用可变对象？",
       ["默认参数只在函数定义时求值一次，所以可变默认参数会在多次调用之间共享。",
        "正确做法是默认设 None，函数内部再判断创建。"], "必考",
       code_lines=[
           "def bad(item, bucket=[]):      # 错：每次调用共用同一个 list",
           "    bucket.append(item)",
           "    return bucket",
           "",
           "def good(item, bucket=None):",
           "    bucket = [] if bucket is None else bucket",
           "    bucket.append(item)",
           "    return bucket",
       ])

    qa(doc, 58, "list、dict、set、tuple 的查找复杂度？",
       ["list 查找是 O(n)（从头扫到尾），按下标访问是 O(1)。",
        "dict 和 set 基于哈希表，平均 O(1)。",
        "tuple 按下标 O(1)，查找元素 O(n)。",
        "所以在循环里做 in 判断，要把 list 换成 set。"], "基础")

    qa(doc, 59, "浅复制一个列表有哪几种写法？",
       ["lst[:]、lst.copy()、list(lst)，还有 copy.copy(lst)。",
        "这几种都是浅拷贝，嵌套的可变对象仍共享。"], "基础")

    qa(doc, 60, "sorted 和 list.sort() 的区别？key 怎么用？",
       ["sorted 返回新列表、不改原对象，能用于任何可迭代对象；sort 是原地排序，返回 None。",
        "key 接收一个函数，按它的返回值排序；reverse 控制降序。",
        "多关键字排序可以返回元组，比如 key=lambda x: (x.age, -x.score)。"], "必考")

    qa(doc, 61, "lambda 能写多行吗？什么场景用？",
       ["只能写单个表达式，不能有语句块。",
        "适合作为排序 key、简单的过滤条件。逻辑复杂就该定义普通函数，可读性更重要。",
        "常见坑：在循环里创建 lambda 时的延迟绑定（见闭包那题）。"], "基础")

    qa(doc, 62, "map、filter、reduce 分别是什么？现在还用吗？",
       ["map 对每个元素应用函数，filter 按条件筛选，reduce 做累积归约。",
        "现在更推荐用列表推导式或生成器表达式，可读性更好，也更快。",
        "reduce 在 Python 3 里要 from functools import reduce。"], "基础")

    qa(doc, 63, "什么是上下文管理器？with 做了什么？",
       ["实现了 __enter__ 和 __exit__ 的对象，with 进入时调前者、退出时调后者（即使抛异常）。",
        "用来保证资源释放：文件、数据库连接、锁。",
        "自己写可以用 contextlib.contextmanager 装饰一个生成器，更简洁。"], "必考")

    qa(doc, 64, "try / except / else / finally 的执行顺序？",
       ["没有异常：try 全部执行 → else → finally。",
        "有异常且被捕获：try 中断 → except → finally。",
        "有异常没被捕获：try 中断 → finally → 异常继续往上抛。",
        "finally 一定执行，常用来释放资源。"], "基础")

    qa(doc, 65, "exceptions 应该怎么捕获？为什么不要裸 except？",
       ["要捕获具体异常类型，比如 except ValueError。",
        "裸 except: 会连 KeyboardInterrupt、SystemExit 一起吞掉，还会掩盖真正的 bug。",
        "需要兜底时写 except Exception（不含系统退出类），并把异常栈记进日志。"], "常考")

    qa(doc, 66, "Python 里怎么做类型提示？有什么用？",
       ["用注解：def f(x: int) -> str。运行时 Python 并不强制检查，但 IDE、mypy 能查出来。",
        "在 AI 应用里最大的价值是配合 Pydantic 做校验、也方便团队协作。",
        "用 from __future__ import annotations 或引号可以解决前向引用问题。"], "常考")

    qa(doc, 67, "OrderedDict 还有必要用吗？",
       ["Python 3.7+ 的普通 dict 已经保证插入顺序，一般不需要 OrderedDict。",
        "OrderedDict 还多两个能力：move_to_end、以及判断顺序是否相同（普通 dict 的 == 不看顺序）。",
        "需要 LRU 缓存时用 collections.OrderedDict 还是经典写法。"], "进阶")

    qa(doc, 68, "collections 里常用哪些工具？",
       ["defaultdict：访问不存在的 key 时自动创建默认值，适合做分组统计。",
        "Counter：计数，还能直接取 most_common。",
        "deque：双端队列，两端操作 O(1)，可以做滑动窗口。"], "常考")

    qa(doc, 69, "怎么优雅地合并两个字典？",
       ["Python 3.9+ 用 a | b，3.5+ 用 {**a, **b}。后者更容易兼容。",
        "update 是原地修改，会改变 a。"], "基础")

    qa(doc, 70, "== 比较自定义对象时行为是什么？",
       ["默认比较的是对象身份（等同 is），要定制就重写 __eq__。",
        "重写 __eq__ 时通常也要重写 __hash__，否则对象会变成不可哈希（放进 set 就报错）。"], "常考")

    qa(doc, 71, "__init__ 和 __new__ 的区别？",
       ["__new__ 负责「创建对象」，返回实例；__init__ 负责「初始化这个实例」。",
        "__new__ 是类方法（第一参数是 cls），__init__ 是实例方法。",
        "只在极少场景需要自定义 __new__，比如单例模式。"], "进阶")

    qa(doc, 72, "Python 的垃圾回收机制？",
       ["主要靠引用计数：引用数为 0 立即回收。",
        "引用计数解决不了循环引用，所以还有分代的循环垃圾收集器（gc 模块），按存活时间分三代。",
        "可以手动 gc.collect() 触发，但不建议频繁调用。"], "常考")

    qa(doc, 73, "什么是内存泄漏？Python 里什么情况会出现？",
       ["对象该被回收却没被回收，内存持续上涨。",
        "常见原因：全局列表/字典只增不减（比如缓存没设上限）、闭包持有大对象、"
        "循环引用里有 __del__、或者注册了回调却从不注销。",
        "排查用 tracemalloc 或 objgraph 看对象增长。"], "常考")

    qa(doc, 74, "什么是鸭子类型？",
       ["「看起来像鸭子、叫起来像鸭子就是鸭子」——不关心对象是什么类型，只关心它有没有对应的方法。",
        "Python 的 for 循环不要求你是 list，只要求你可迭代。",
        "这是 Python 偏向「协议」而非「继承」的设计哲学。"], "基础")

    qa(doc, 75, "面向对象的三大特性在 Python 里怎么体现？",
       ["封装：用下划线约定私有（_x、__x 名字改写），本质靠约定不是强制。",
        "继承：class A(B)，支持多继承。",
        "多态：靠鸭子类型和 __getattr__ 等协议实现，不依赖接口声明。"], "基础")

    # ================= 七、AI 应用工程实践 =================
    h1(doc, "七、AI 应用工程实践（Python 综合题）")

    qa(doc, 76, "怎么把上面几块串起来：设计一个「批量问 LLM 并做结构化解析」的服务？",
       ["流程：Pydantic 定义输入输出 → asyncio.Semaphore 限并发 → httpx.AsyncClient 带超时重试 → "
        "拿到文本用 model_validate_json 解析 → 失败重试 → 汇总结果。",
        "这题是综合题，能把这几个技术点串起来讲，比单点答对更有说服力。",
        "可以顺带说清楚：为什么要限并发、为什么复用一个 Client、失败怎么降级。"], "综合")

    qa(doc, 77, "并发调 100 个接口，怎么避免把对方打挂？",
       ["用 Semaphore 限制同时在飞的请求数，剩下的排队。",
        "再加令牌桶控制 QPS，防止短时间尖峰。",
        "设置合理超时和最大重试次数，失败不要无限重试。",
        "本地也要限制连接池大小（httpx 的 limits 参数），否则同一条路全堵在连接上。"], "常考")

    qa(doc, 78, "怎么给整个应用加统一的日志和耗时统计？",
       ["用装饰器包装关键函数，记录开始/结束时间、参数摘要、异常信息。",
        "异步函数要用 async def 的装饰器，并且 await 原函数。",
        "更好的是用上下文变量（contextvars）把 request_id 串起来，日志里自动带上。"], "进阶")

    qa(doc, 79, "contextvars 是什么？为什么异步里不能用 threading.local？",
       ["threading.local 是按线程隔离的，但协程都在同一个线程里，会互相串数据。",
        "contextvars 是按「上下文」隔离的，每个任务有自己的副本，asyncio 原生支持。",
        "典型用途：给每个请求加 trace_id，贯穿所有日志。"], "加分项")

    qa(doc, 80, "怎么写一个限流器？",
       ["简单版用 Semaphore（限制并发数）；",
        "限速版用令牌桶：固定速率往桶里放令牌，取到才能执行；",
        "分布式场景要用 Redis 做全局计数，用 Lua 保证原子性。"], "加分项")

    qa(doc, 81, "FastAPI 的依赖注入怎么用？",
       ["用 Depends 声明依赖，FastAPI 会帮你创建并传进来，还能做嵌套依赖。",
        "常见用法：数据库会话、当前用户（鉴权）、配置对象。",
        "异步依赖用 async def，FastAPI 会正确 await。"], "常考",
       code_lines=[
           "from fastapi import Depends, FastAPI",
           "",
           "async def get_db():",
           "    async with SessionLocal() as s:",
           "        yield s          # yield 依赖：请求结束后自动关闭",
           "",
           "@app.get(\"/items\")",
           "async def list_items(db=Depends(get_db)): ...",
       ])

    qa(doc, 82, "为什么要用 .venv 虚拟环境？",
       ["隔离项目依赖，避免不同项目版本冲突。",
        "配合 requirements.txt 或 pyproject.toml 锁定版本，保证可复现。",
        "生产环境用 uv、poetry 或 pip-tools 锁定精确版本更稳。"], "基础")

    qa(doc, 83, "pip、conda、uv、poetry 怎么选？",
       ["pip + venv 最标准通用；",
        "conda 适合带原生依赖（比如 CUDA、torch）的环境，依赖解析能力强；",
        "uv 是新一代超快安装器，兼容 pip 生态；",
        "poetry 侧重依赖管理和打包，锁文件严谨。",
        "实习阶段能讲清 lock 文件的意义就够了。"], "基础")

    qa(doc, 84, "怎么用 pytest 测异步代码？",
       ["用 pytest-asyncio 插件，给测试函数加 @pytest.mark.asyncio 就能直接 await。",
        "也可以自己用 asyncio.run 包一层，但插件更规范。",
        "要注意测试之间的事件循环隔离，避免状态残留。"], "常考")

    qa(doc, 85, "单元测试里怎么 mock 外部 API？",
       ["用 unittest.mock.patch 替换调用点，或者在 pytest 里用 monkeypatch。",
        "关键原则：patch 的是「被测试模块里引用的那个名字」，不是定义处。",
        "异步函数要被 mock 成 AsyncMock，否则 await 一个普通 Mock 会报错。"], "常考")

    qa(doc, 86, "进程被 kill 时，怎么保证数据不丢？",
       ["关键数据及时落库，不要只放在内存里。",
        "需要长任务时用队列 + 状态标记，重启后能续跑。",
        "文件写入用「写临时文件 + 原子重命名」，避免写到一半崩溃产生坏文件。"], "进阶")

    qa(doc, 87, "怎么处理大文件 / 大响应，避免内存爆掉？",
       ["流式读取，不要一次性 read()。",
        "写文件用 shutil.copyfileobj，或者按 chunk 循环读写。",
        "处理 CSV / JSON 大文件优先用流式解析（ijson、pandas 的 chunksize）。"], "常考")

    qa(doc, 88, "Python 程序跑得慢，你会怎么排查？",
       ["先用 cProfile 或 py-spy 找热点函数，不要凭感觉优化。",
        "确认是 CPU 慢还是 I/O 慢分别处理。",
        "常见优化：换数据结构（list → set/dict）、避免重复计算（加缓存）、"
        "把循环换成向量化、或者把热点用 C 扩展 / 多进程。"], "加分项")

    qa(doc, 89, "什么是单例模式？Python 里怎么实现？",
       ["保证一个类只有一个实例。",
        "实现方式：模块级变量（最简单，Python 模块本身就是单例）、__new__ 控制、装饰器、元类。",
        "实际项目里常用「模块级全局对象」或者 lru_cache 缓存初始化函数。"], "常考")

    qa(doc, 90, "为什么项目里连接池、模型对象都只用一份？",
       ["模型加载很慢、占内存，连接池建立也要握手，反复创建代价大。",
        "常见做法是用 functools.lru_cache 装饰初始化函数，让它只执行一次。",
        "注意：缓存的对象如果会失效（比如向量库集合被重建），就不能缓存，否则会拿到旧对象——"
        "这是个真实的坑。"], "结合你项目")

    qa(doc, 91, "Python 里怎么做重试？写出一个通用重试装饰器。",
       ["用装饰器包装，捕获指定异常后 sleep 再试，次数用完抛最后一个异常。",
        "支持同步用；异步版本要包成 async def 并 await sleep。",
        "生产上直接用 tenacity 库，别自己造轮子。"], "常考",
       code_lines=[
           "import time, functools",
           "",
           "def retry(times=3, delay=0.5, exceptions=(Exception,)):",
           "    def deco(func):",
           "        @functools.wraps(func)",
           "        def wrapper(*a, **kw):",
           "            for i in range(times):",
           "                try:",
           "                    return func(*a, **kw)",
           "                except exceptions:",
           "                    if i == times - 1:",
           "                        raise",
           "                    time.sleep(delay * 2 ** i)",
           "        return wrapper",
           "    return deco",
       ])

    qa(doc, 92, "什么是 requirements.txt 和 pyproject.toml 的区别？",
       ["requirements.txt 是扁平依赖列表，简单直接，适合部署。",
        "pyproject.toml 是现代标准，能声明项目元数据、依赖、构建工具配置、工具配置（pytest、ruff）。",
        "实际项目常用 pyproject 管理依赖，再导出 requirements 给部署环境。"], "基础")

    qa(doc, 93, "Python 代码风格你遵守什么规范？",
       ["PEP 8：命名、缩进、行宽。",
        "工具链一般是 ruff 或 flake8 做检查、black 格式化、isort 管导入顺序。",
        "团队里统一就行，比具体用哪个重要。"], "基础")

    qa(doc, 94, "讲讲你项目里最难的一个 Python 问题。",
       ["准备一个真实的：比如「重建向量库后后端报错必须重启」，"
        "根因是 lru_cache 缓存了已被删除的集合对象。",
        "按「现象 → 定位 → 原因 → 修复 → 验证」的顺序讲，体现排查能力。",
        "这种题没有标准答案，面试官看的是你有没有真的动手。"], "必问")

    qa(doc, 95, "如果让你优化一个慢的 RAG 接口，你会从哪下手？",
       ["先量：分别测检索耗时、生成耗时、网络耗时，找出真正的瓶颈。",
        "检索慢：加缓存、减少 top-k、换更轻的向量模型；",
        "生成慢：换小模型 / 开流式输出 / 压缩上下文 token；",
        "并发：把串行调用改异步，并加连接池复用。"], "加分项")

    qa(doc, 96, "最后：AI 应用开发岗的 Python 面试，重点是哪几个？",
       ["按重要性排序：async 并发（必考、常手写）、Pydantic 校验、生成器与流式输出、"
        "GIL 与并发选型、超时重试与稳定性。",
        "基础语法题是门槛，答崩会直接出局，但一般不会深挖。",
        "建议准备一个「能跑通的最小 demo」，面试时能说出来具体怎么写的，比背概念强得多。"], "总结")

    # ================= 速查表 =================
    doc.add_page_break()
    h1(doc, "八、临场速查表")

    gloss = [
        ("async def", "定义协程函数，调用返回协程对象，await 才真正执行。"),
        ("await", "把控制权交还事件循环，等待期间可以去跑别的任务。"),
        ("asyncio.gather", "并发跑多个协程并等全部完成，返回顺序与传入一致。"),
        ("create_task", "把协程注册进事件循环立即开始，不等待结果。"),
        ("Semaphore", "限制同时执行的任务数，是最常用的限流手段。"),
        ("wait_for", "给协程加超时，超时抛 TimeoutError 并取消任务。"),
        ("to_thread", "把同步阻塞函数丢进线程池，避免卡住事件循环。"),
        ("Pydantic", "基于类型注解做校验和转换，FastAPI 的标配。"),
        ("Field", "给字段加约束和默认值，可变默认值用 default_factory。"),
        ("field_validator", "Pydantic v2 的自定义字段校验器，要加 @classmethod。"),
        ("model_dump", "v2 里替代 dict()，把模型转成字典。"),
        ("validator 分层", "类型转���在前，校验器在后，适合加业务规则。"),
        ("Iterable", "可迭代对象，实现了 __iter__，如 list/dict/str。"),
        ("Iterator", "迭代器，实现 __iter__ 和 __next__，有状态、只能走一次。"),
        ("Generator", "用 yield 写出的迭代器，惰性求值、省内存。"),
        ("yield", "抛出一个值并暂停，保留函数现场，下次继续。"),
        ("yield from", "把子生成器委托出去，递归场景很好用。"),
        ("GIL", "CPython 的全局解释器锁，同一时刻只有一个线程跑字节码。"),
        ("多进程", "绕开 GIL 做真正并行，适合 CPU 密集，代价是序列化和启动开销。"),
        ("多线程", "适合 I/O 密集，GIL 在 I/O 等待时释放。"),
        ("协程", "适合海量并发 I/O，开销最小，但不能解决 CPU 密集。"),
        ("ThreadPoolExecutor", "线程池，提交任务返回 Future。"),
        ("ProcessPoolExecutor", "进程池，接口与线程池一致，绕开 GIL。"),
        ("requests timeout", "必须显式传，格式 (connect, read)，否则可能永久阻塞。"),
        ("指数退避", "重试间隔按 2 的幂递增，加随机抖动避免惊群。"),
        ("幂等", "同一请求执行多次结果相同，只有幂等操作才适合自动重试。"),
        ("httpx.AsyncClient", "异步 HTTP 客户端，支持连接池复用，AI 应用首选。"),
        ("连接池复用", "避免重复 TCP/TLS 握手，显著降低延迟。"),
        ("元组 vs 列表", "元组不可变、可哈希、更省内存；列表可变、适合动态增删。"),
        ("is vs ==", "is 比身份（id），== 比值；判断 None 用 is。"),
        ("浅拷贝", "只复制外层容器，内部元素仍共享引用。"),
        ("可变默认参数", "只在定义时求值一次，会跨调用共享，必须用 None 兜底。"),
        ("闭包延迟绑定", "循环里创建闭包共享同一个变量，用默认参数固定值。"),
        ("装饰器", "接收函数返回函数，可叠加；带参数的要多包一层。"),
        ("contextvars", "按上下文隔离变量，异步里替代 threading.local。"),
    ]
    tbl = doc.add_table(rows=len(gloss) + 1, cols=2)
    tbl.style = "Table Grid"
    hdr = tbl.rows[0].cells
    for c, t in zip(hdr, ("名词", "一句话解释")):
        shade(c, "14507F")
        set_font(c.paragraphs[0].add_run(t), 9.5, True, RGBColor(0xFF, 0xFF, 0xFF))
    hdr[0].width = Cm(3.8)
    hdr[1].width = Cm(12.6)
    for i, (k, v) in enumerate(gloss, start=1):
        c0, c1 = tbl.rows[i].cells
        c0.width = Cm(3.8)
        c1.width = Cm(12.6)
        shade(c0, "EAF2FB")
        set_font(c0.paragraphs[0].add_run(k), 9, True, MAIN)
        set_font(c1.paragraphs[0].add_run(v), 9, False, GRAY)

    doc.add_paragraph()
    body(doc, "提醒：AI 应用岗的 Python 面试，代码能力比八股重要。"
              "上面每一段代码都建议亲手跑一遍，面试时被要求写代码才不会卡壳。",
         size=10, color=RGBColor(0xB8, 0x2A, 0x2A))

    doc.save(OUT)
    print("saved:", OUT)
    print("paragraphs:", len(doc.paragraphs), "tables:", len(doc.tables))


if __name__ == "__main__":
    build()
