from langchain_chroma import Chroma
from langchain_core.documents import Document
from utils.config_handler import chroma_conf

from model.factory import embed_model

from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.path_tool import get_abs_path
from utils.file_handler import pdf_loader, txt_loader, listdir_with_allowed_type, get_file_md5_hex
from utils.logger_handler import logger

import os


class VectorStoreService:
    def __init__(self):
        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"],
            embedding_function=embed_model,
            persist_directory=chroma_conf["persist_directory"],
        )

        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=chroma_conf["chunk_size"],
            chunk_overlap=chroma_conf["chunk_overlap"],
            separators=chroma_conf["separators"],
            length_function=len,
        )

    def get_retriever(self):
        """纯向量检索：直接取相似度最高的 k 条，不经过 rerank。"""
        return self.vector_store.as_retriever(search_kwargs={"k": chroma_conf["k"]})

    def retrieve(self, query: str) -> list[Document]:
        """
        两级检索：向量粗召回 -> rerank 精排。

        一级用向量召回 recall_k 条（默认 20），保证相关片段不会在第一级就被漏掉；
        二级用 rerank 模型对「query-片段」逐条打分重排，取前 k 条（默认 3）。

        粗召回之所以放宽到 20，是因为向量相似度对中文短查询区分度有限，
        真正相关的那条经常排在 5~15 名之间，只用向量取 top3 会直接丢掉。
        """
        k = chroma_conf["k"]

        if not chroma_conf.get("rerank_enabled", False):
            # 关闭 rerank 时退化为纯向量检索
            return self.vector_store.similarity_search(query, k=k)

        recall_k = max(chroma_conf.get("recall_k", k), k)
        candidates = self.vector_store.similarity_search(query, k=recall_k)

        if len(candidates) <= k:
            return candidates

        ranked = self._rerank(query, candidates, k)

        # rerank 失败时不能让整个问答挂掉，退回向量检索的结果
        if ranked is None:
            logger.warning("[rerank]重排序失败，退回向量检索结果")
            return candidates[:k]

        return ranked

    def _rerank(self, query: str, candidates: list[Document], top_n: int):
        """
        调用 DashScope rerank 接口对候选片段重新排序。

        成功返回排好序的前 top_n 条；失败返回 None，由调用方决定降级策略。
        """
        import dashscope

        try:
            resp = dashscope.TextReRank.call(
                model=chroma_conf["rerank_model_name"],
                query=query,
                documents=[doc.page_content for doc in candidates],
                top_n=top_n,
                return_documents=False,
            )
        except Exception as e:
            logger.error(f"[rerank]调用异常：{str(e)}", exc_info=True)
            return None

        if resp.status_code != 200:
            logger.error(f"[rerank]接口返回异常 status={resp.status_code} output={resp.output}")
            return None

        results = resp.output.get("results") or []
        if not results:
            return None

        # 接口只回传下标和分数，这里按下标取回原始 Document，并把分数写进元数据，
        # 方便前端展示「这个片段为什么被选中」，也方便调试检索效果。
        ranked: list[Document] = []
        for item in results:
            idx = item["index"]
            if not 0 <= idx < len(candidates):
                continue
            doc = candidates[idx]
            doc.metadata["rerank_score"] = round(float(item["relevance_score"]), 4)
            ranked.append(doc)

        return ranked

    def load_document(self):
        """
        从数据文件夹内读取数据文件，转为向量存入向量库
        要计算文件的MD5做去重
        :return: None
        """

        def check_md5_hex(md5_for_check: str):
            if not os.path.exists(get_abs_path(chroma_conf["md5_hex_store"])):
                # 创建文件
                open(get_abs_path(chroma_conf["md5_hex_store"]), "w", encoding="utf-8").close()
                return False            # md5 没处理过

            with open(get_abs_path(chroma_conf["md5_hex_store"]), "r", encoding="utf-8") as f:
                for line in f.readlines():
                    line = line.strip()
                    if line == md5_for_check:
                        return True     # md5 处理过

                return False            # md5 没处理过

        def save_md5_hex(md5_for_check: str):
            with open(get_abs_path(chroma_conf["md5_hex_store"]), "a", encoding="utf-8") as f:
                f.write(md5_for_check + "\n")

        def get_file_documents(read_path: str):
            if read_path.endswith("txt"):
                return txt_loader(read_path)

            if read_path.endswith("pdf"):
                return pdf_loader(read_path)

            return []

        allowed_files_path: list[str] = listdir_with_allowed_type(
            get_abs_path(chroma_conf["data_path"]),
            tuple(chroma_conf["allow_knowledge_file_type"]),
        )

        for path in allowed_files_path:
            # 获取文件的MD5
            md5_hex = get_file_md5_hex(path)

            if check_md5_hex(md5_hex):
                logger.info(f"[加载知识库]{path}内容已经存在知识库内，跳过")
                continue

            try:
                documents: list[Document] = get_file_documents(path)

                if not documents:
                    logger.warning(f"[加载知识库]{path}内没有有效文本内容，跳过")
                    continue

                split_document: list[Document] = self.spliter.split_documents(documents)

                if not split_document:
                    logger.warning(f"[加载知识库]{path}分片后没有有效文本内容，跳过")
                    continue

                # 将内容存入向量库
                self.vector_store.add_documents(split_document)

                # 记录这个已经处理好的文件的md5，避免下次重复加载
                save_md5_hex(md5_hex)

                logger.info(f"[加载知识库]{path} 内容加载成功")
            except Exception as e:
                # exc_info为True会记录详细的报错堆栈，如果为False仅记录报错信息本身
                logger.error(f"[加载知识库]{path}加载失败：{str(e)}", exc_info=True)
                continue


if __name__ == '__main__':
    vs = VectorStoreService()

    vs.load_document()

    retriever = vs.get_retriever()

    res = retriever.invoke("迷路")
    for r in res:
        print(r.page_content)
        print("-"*20)


