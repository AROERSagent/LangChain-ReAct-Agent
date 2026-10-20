import os

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser

from rag.vector_store import VectorStoreService
from utils.prompt_loader import load_rag_prompts
from langchain_core.prompts import PromptTemplate
from model.factory import chat_model


class RagSummarizeService:
    def __init__(self):
        self.vector_store = VectorStoreService()
        self.prompt_text = load_rag_prompts()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model = chat_model
        self.chain = self._init_chain()

    def _init_chain(self):
        return self.prompt_template | self.model | StrOutputParser()

    def retriever_docs(self, query: str) -> list[Document]:
        """两级检索取参考资料（向量粗召回 + rerank 精排）。"""
        return self.vector_store.retrieve(query)

    @staticmethod
    def format_sources(docs: list[Document]) -> list[dict]:
        """
        把命中的片段整理成前端可展示的来源列表。

        只取文件名（不含路径）和片段预览，避免把本机目录结构暴露到界面上。
        """
        sources = []
        for i, doc in enumerate(docs, start=1):
            path = doc.metadata.get("source", "")
            preview = doc.page_content.strip().replace("\n", " ")
            sources.append({
                "index": i,
                "file": os.path.basename(path) if path else "未知来源",
                "preview": preview[:120] + ("..." if len(preview) > 120 else ""),
                "rerank_score": doc.metadata.get("rerank_score"),
            })
        return sources

    def rag_summarize(self, query: str) -> str:
        return self.rag_summarize_with_sources(query)[0]

    def rag_summarize_with_sources(self, query: str) -> tuple[str, list[Document]]:
        """
        返回 (回答, 命中的参考资料)。

        保留原始 Document 是为了让上层能把来源回传给前端做溯源展示；
        工具函数 rag_summarize 只取第一个元素返回给模型，行为不变。
        """
        context_docs = self.retriever_docs(query)

        context = ""
        counter = 0
        for doc in context_docs:
            counter += 1
            context += f"【参考资料{counter}】: 参考资料：{doc.page_content} | 参考元数据：{doc.metadata}\n"

        answer = self.chain.invoke(
            {
                "input": query,
                "context": context,
            }
        )

        return answer, context_docs


if __name__ == '__main__':
    rag = RagSummarizeService()

    print(rag.rag_summarize("小户型适合哪些扫地机器人"))
