"""
数据表定义。

分两块：
- 会话相关（Conversation / Message）：把对话历史从 Streamlit session 里搬进数据库，
  刷新不丢、多用户隔离、可做会话列表。
- 业务数据（User / UsageRecord）：把原来全量读进内存的 records.csv 落成正式表，
  支持按用户/月份索引查询，为将来做范围查询和大数据量打底。
"""
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    """用户表。原来用户信息只以字符串 ID 出现在 CSV 里，没有独立实体。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, comment="业务用户编号，如 1001")
    name: Mapped[str] = mapped_column(String(64), default="", comment="用户昵称")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    records: Mapped[list["UsageRecord"]] = relationship(back_populates="user")


class UsageRecord(Base):
    """
    用户月度使用记录。

    对应原 records.csv 的每一行：特征 / 清洁效率 / 耗材 / 对比 / 时间。
    (user_id, month) 建唯一约束 —— 同一用户同一个月只应有一条记录，
    这比原来 CSV 里靠后写覆盖先写更可靠。
    """

    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    month: Mapped[str] = mapped_column(String(7), nullable=False, comment="YYYY-MM")

    feature: Mapped[str] = mapped_column(Text, default="", comment="用户特征")
    efficiency: Mapped[str] = mapped_column(Text, default="", comment="清洁效率")
    consumables: Mapped[str] = mapped_column(Text, default="", comment="耗材状态")
    comparison: Mapped[str] = mapped_column(Text, default="", comment="横向对比")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    user: Mapped["User"] = relationship(back_populates="records")

    __table_args__ = (
        UniqueConstraint("user_id", "month", name="uq_usage_user_month"),
        # 查询几乎都是「某用户某月」或「某用户最近几个月」，
        # 联合索引让两种查询都走索引，避免全表扫描
        Index("ix_usage_user_month", "user_id", "month"),
    )


class Conversation(Base):
    """会话表。一个会话承载一串消息。"""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 多用户隔离的抓手：现在用浏览器标识占位，接上登录体系后换成真实用户 ID 即可
    session_key: Mapped[str] = mapped_column(String(64), index=True, comment="会话归属标识")
    title: Mapped[str] = mapped_column(String(128), default="新对话", comment="会话标题，取首条提问")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )


class Message(Base):
    """消息表。role 只有 user / assistant 两种。"""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="")
    # 引用来源是结构化列表，直接存 JSON 文本：来源只用于前端回放，
    # 不需要按内部字段检索，单独建表反而增加复杂度
    sources_json: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("ix_message_conversation", "conversation_id", "id"),
    )


class LlmCall(Base):
    """
    模型调用埋点，用于成本与性能分析。

    记录每次调用的 token 和耗时，可以回答「今天花了多少钱」「哪一步慢」。
    """

    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    model_name: Mapped[str] = mapped_column(String(64), default="")
    tool_name: Mapped[str] = mapped_column(String(64), default="", comment="本轮调用的工具名，非工具轮为空")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16), default="ok")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
