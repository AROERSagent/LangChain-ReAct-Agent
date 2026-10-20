"""
数据库连接与会话管理。

连接串从 config/database.yml 读取，本地默认用 SQLite（零安装），
换成 MySQL 只需改一行 url，代码不用动。
"""
from contextlib import contextmanager
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from utils.config_handler import database_conf
from utils.logger_handler import logger
from utils.path_tool import get_abs_path


def _build_url() -> str:
    """
    拼出 SQLAlchemy 连接串。

    SQLite 的路径要转成绝对路径，否则会跟着 Streamlit 的工作目录漂移，
    导致换个启动方式就在别处新建一个空库。
    """
    url = database_conf["url"]

    if url.startswith("sqlite"):
        # sqlite:///relative/path.db -> 只替换路径部分
        prefix, _, path = url.partition(":///")
        if path and not path.startswith(":memory:"):
            abs_path = get_abs_path(path)
            # SQLite 不会自动创建父目录，首次运行会直接报 unable to open database file
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            # Windows 下必须把反斜杠统一成正斜杠：连接串里混用两种分隔符时
            # SQLAlchemy 解析出的路径会出错，表现为 unable to open database file
            return f"{prefix}:///{abs_path.replace(os.sep, '/')}"

    return url


DATABASE_URL = _build_url()

# SQLite 需要 check_same_thread=False：Streamlit 会在不同线程里执行脚本，
# 默认的同线程限制会直接抛错。其他数据库不受这个参数影响。
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    echo=database_conf.get("echo", False),
    future=True,
    connect_args=_connect_args,
    # 连接池预检：MySQL 空闲连接超过 wait_timeout 会被服务端断开，
    # 开启 pre_ping 可以避免拿到失效连接后报错
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db():
    """建表（幂等，已存在则跳过）。"""
    from db.models import Base

    Base.metadata.create_all(engine)
    logger.info(f"[db]数据库已就绪：{_safe_url(DATABASE_URL)}")


def _safe_url(url: str) -> str:
    """打日志时隐去密码，避免凭据写进日志文件。"""
    if "@" not in url:
        return url
    scheme, _, rest = url.partition("://")
    _, _, host = rest.rpartition("@")
    return f"{scheme}://***@{host}"


@contextmanager
def get_session():
    """
    提供一个自动提交/回滚的会话。

    用法：
        with get_session() as session:
            session.add(obj)

    正常退出提交，异常回滚并重新抛出，调用方不用自己写 try/except。
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
