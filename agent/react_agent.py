"""
ReAct Agent 主逻辑。

对外提供结构化事件流，让前端能区分「模型思考 / 工具调用 / 工具结果 / 最终回答」，
而不是只拿到一串最终答案文本。
"""
from langchain.agents import create_agent
from model.factory import chat_model
from utils.config_handler import agent_conf
from utils.prompt_loader import load_system_prompts
from agent.tools.agent_tools import (last_rag_sources, rag_summarize, web_search, get_user_id,
                                     get_current_month, fetch_external_data, fetch_usage_range,
                                     fill_context_for_report)
from agent.tools.middleware import monitor_tool, log_before_model, report_prompt_switch


class ReactAgent:
    def __init__(self):
        self.agent = create_agent(
            model=chat_model,
            system_prompt=load_system_prompts(),
            tools=[rag_summarize, web_search, get_user_id,
                   get_current_month, fetch_external_data, fetch_usage_range,
                   fill_context_for_report],
            middleware=[monitor_tool, log_before_model, report_prompt_switch],
        )
        # 代码层面的硬约束，配合提示词里的调用次数建议一起兜住跑飞
        self.recursion_limit = agent_conf.get("recursion_limit", 12)
        # 本轮 RAG 命中的来源，流结束后附在末尾
        self.sources: list[dict] = []

    def execute_stream(self, query: str, history: list | None = None):
        """
        执行一次问答，产出结构化事件。

        :param query: 本轮用户输入
        :param history: 历史对话，格式 [{"role": "user"/"assistant", "content": str}, ...]。
                        传入历史后模型才能记住上下文（指代消解、追问都依赖它）。
        :return: 生成器，逐条产出事件字典：
                 {"type": "thinking",    "content": str}      模型带工具调用的思考过程
                 {"type": "tool_call",   "name": str, "args": dict}
                 {"type": "tool_result", "name": str, "content": str}
                 {"type": "answer",      "content": str}      最终回答
                 {"type": "sources",     "content": list}     本轮 RAG 命中的参考资料
                 {"type": "error",       "content": str}
        """
        messages = self._build_messages(query, history)

        self.sources = []
        seen_tool_calls: set[str] = set()

        try:
            for event in self.agent.stream(
                {"messages": messages},
                stream_mode=["messages"],
                context={"report": False},
                config={"recursion_limit": self.recursion_limit},
            ):
                yield from self._translate(event, seen_tool_calls)
        except Exception as e:
            yield {"type": "error", "content": f"执行出错：{str(e)}"}
            return

        # 来源信息统一在回答结束后附上，避免前端在答案中间插入引用块
        if self.sources:
            yield {"type": "sources", "content": list(self.sources)}

    @staticmethod
    def _build_messages(query: str, history: list | None) -> list[dict]:
        """
        拼接本轮输入。

        只保留 user / assistant 两类消息：工具调用的中间消息不需要回传给模型，
        否则历史会迅速膨胀，且模型容易被旧的工具结果带偏。
        """
        messages: list[dict] = []
        for msg in history or []:
            role = msg.get("role")
            content = msg.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": query})
        return messages

    def _translate(self, event, seen_tool_calls: set[str]):
        """
        把 LangGraph 的原始流事件翻译成前端友好事件。

        stream_mode="messages" 下每条事件是 ("messages", (消息对象, 元信息)) 二元组。
        只订阅 messages 就够了：工具入参能从带 tool_calls 的 AIMessage 上直接拿到，
        不需要再叠加 updates 模式（那样每轮工具调用会重复产出两次）。
        """
        if not isinstance(event, tuple) or len(event) != 2:
            return

        mode, payload = event

        if mode == "messages":
            yield from self._translate_message(payload, seen_tool_calls)

    def _translate_message(self, payload, seen_tool_calls: set[str]):
        """处理 messages 模式的单条消息。"""
        from langchain_core.messages import AIMessage, ToolMessage

        if not isinstance(payload, tuple) or len(payload) != 2:
            return

        message, _meta = payload

        if isinstance(message, AIMessage):
            tool_calls = getattr(message, "tool_calls", None) or []

            if tool_calls:
                # 带工具调用的 AIMessage：content 就是模型的思考过程
                if message.content:
                    text = self._as_text(message.content)
                    if text.strip():
                        yield {"type": "thinking", "content": text.strip()}

                for call in tool_calls:
                    call_id = call.get("id") or f"{call.get('name')}:{call.get('args')}"
                    if call_id in seen_tool_calls:
                        continue
                    seen_tool_calls.add(call_id)
                    yield {
                        "type": "tool_call",
                        "name": call.get("name", ""),
                        "args": call.get("args", {}),
                    }
                return

            # 不带工具调用的 AIMessage：最终回答
            content = self._as_text(message.content)
            if content.strip():
                yield {"type": "answer", "content": content.strip()}

        elif isinstance(message, ToolMessage):
            text = self._as_text(message.content).strip()

            # RAG 命中来源由工具内部记录，这里在每次调用后同步一次
            if message.name == "rag_summarize":
                self.sources = list(last_rag_sources)

            if len(text) > 500:
                text = text[:500] + "..."
            yield {"type": "tool_result", "name": message.name or "", "content": text}

    @staticmethod
    def _as_text(content) -> str:
        """
        把消息内容统一成纯文本。

        新版 LangChain 的 content 可能是字符串，也可能是 [{"type":"text","text":...}]
        这样的分块列表，两种都要兼容，否则会直接拿到 list 拼进字符串里。
        """
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                part.get("text", "") for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            )
        return str(content or "")


if __name__ == '__main__':
    agent = ReactAgent()

    for event in agent.execute_stream("给我生成我的使用报告"):
        print(event, flush=True)
