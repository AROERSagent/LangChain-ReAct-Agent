import os
from abc import ABC, abstractmethod
from typing import Optional

from dotenv import load_dotenv

from langchain_core.embeddings import Embeddings
from langchain_community.chat_models.tongyi import BaseChatModel
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.chat_models.tongyi import ChatTongyi
from utils.path_tool import get_abs_path
from utils.config_handler import rag_conf

# 在创建模型之前先把 .env 里的 DASHSCOPE_API_KEY 读进环境变量，
# 否则 ChatTongyi / DashScopeEmbeddings 初始化时会因为拿不到 key 而报错
load_dotenv(get_abs_path(".env"))

if not os.getenv("DASHSCOPE_API_KEY"):
    raise RuntimeError(
        "未找到 DASHSCOPE_API_KEY，请在项目根目录的 .env 文件中配置后再启动"
        "（可复制 .env.example 为 .env，填入阿里云百炼的 API Key）"
    )


class BaseModelFactory(ABC):
    @abstractmethod
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        pass


class ChatModelFactory(BaseModelFactory):
    def generator(self)->Optional[Embeddings | BaseChatModel]:
        return ChatTongyi(model=rag_conf["chat_model_name"])


class EmbeddingsFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        return DashScopeEmbeddings(model=rag_conf["embedding_model_name"])


chat_model = ChatModelFactory().generator()

embed_model = EmbeddingsFactory().generator()
