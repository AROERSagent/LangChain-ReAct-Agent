"""
数据访问层。

把 SQL 关在这一层里，上层（app.py / agent_tools.py）只调用函数，
不直接写查询语句。将来换库、加缓存都只改这里。
"""
import json
from datetime import datetime

from sqlalchemy import func, select

from db.database import get_session
from db.models import Conversation, LlmCall, Message, UsageRecord, User
from utils.logger_handler import logger


# ---------------------------------------------------------------- 用户 / 使用记录

def get_or_create_user(session, user_code: str) -> User:
    user = session.scalar(select(User).where(User.user_code == user_code))
    if user is None:
        user = User(user_code=user_code)
        session.add(user)
        session.flush()  # 立刻拿到自增 id
    return user


def import_usage_records(rows: list[dict]) -> int:
    """
    批量导入使用记录。

    :param rows: [{"user_id": "1001", "month": "2025-01", "feature": ..., ...}, ...]
    :return: 新增的记录条数（已存在的不重复插入）

    用 (user_id, month) 做去重，重复导入同一份 CSV 不会产生脏数据。
    """
    inserted = 0

    with get_session() as session:
        for row in rows:
            user = get_or_create_user(session, str(row["user_id"]))

            exists = session.scalar(
                select(UsageRecord).where(
                    UsageRecord.user_id == user.id,
                    UsageRecord.month == row["month"],
                )
            )
            if exists:
                continue

            session.add(UsageRecord(
                user_id=user.id,
                month=row["month"],
                feature=row.get("feature", ""),
                efficiency=row.get("efficiency", ""),
                consumables=row.get("consumables", ""),
                comparison=row.get("comparison", ""),
            ))
            inserted += 1

    return inserted


def query_usage_record(user_code: str, month: str) -> dict | None:
    """
    查询某用户某月的使用记录。

    走 (user_id, month) 联合索引，等价于原来 external_data[user_id][month]，
    但不再需要把整份 CSV 读进内存。
    """
    with get_session() as session:
        stmt = (
            select(UsageRecord)
            .join(User, User.id == UsageRecord.user_id)
            .where(User.user_code == str(user_code), UsageRecord.month == month)
        )
        record = session.scalar(stmt)

        if record is None:
            return None

        return {
            "特征": record.feature,
            "效率": record.efficiency,
            "耗材": record.consumables,
            "对比": record.comparison,
        }


def query_usage_range(user_code: str, start_month: str, end_month: str) -> list[dict]:
    """
    按月份区间查询使用记录。

    CSV 方案做不到这件事（要么全读进内存再筛，要么自己解析），
    换成表之后一句 BETWEEN 就够了 —— 这也是换数据库最直接的收益。
    """
    with get_session() as session:
        stmt = (
            select(UsageRecord)
            .join(User, User.id == UsageRecord.user_id)
            .where(
                User.user_code == str(user_code),
                UsageRecord.month >= start_month,
                UsageRecord.month <= end_month,
            )
            .order_by(UsageRecord.month)
        )
        return [
            {
                "月份": r.month,
                "特征": r.feature,
                "效率": r.efficiency,
                "耗材": r.consumables,
                "对比": r.comparison,
            }
            for r in session.scalars(stmt)
        ]


def list_known_users(limit: int = 20) -> list[str]:
    """列出库里已有的用户编号，供前端或调试使用。"""
    with get_session() as session:
        stmt = select(User.user_code).order_by(User.user_code).limit(limit)
        return list(session.scalars(stmt))


def latest_record_month() -> str | None:
    """
    返回库中最新一条使用记录的月份。

    用途：数据集的月份范围往往不是当前月份（示例数据是 2025 年），
    如果模型拿「当前月份」直接去查，会查空、进而编造一份没有依据的报告。
    有了这个值，工具可以在查不到时把「可用的最新月份」告诉模型。
    """
    with get_session() as session:
        return session.scalar(select(func.max(UsageRecord.month)))


def available_months(user_code: str) -> list[str]:
    """列出某用户有记录的月份，按升序返回。"""
    with get_session() as session:
        stmt = (
            select(UsageRecord.month)
            .join(User, User.id == UsageRecord.user_id)
            .where(User.user_code == str(user_code))
            .order_by(UsageRecord.month)
        )
        return list(session.scalars(stmt))


# ---------------------------------------------------------------- 会话 / 消息

def get_or_create_conversation(session_key: str, title: str | None = None) -> int:
    """取该标识下最近的一个会话，没有就新建。返回会话 id。"""
    with get_session() as session:
        conversation = session.scalar(
            select(Conversation)
            .where(Conversation.session_key == session_key)
            .order_by(Conversation.id.desc())
        )

        if conversation is None:
            conversation = Conversation(session_key=session_key, title=title or "新对话")
            session.add(conversation)
            session.flush()

        return conversation.id


def list_conversations(session_key: str, limit: int = 50) -> list[dict]:
    """
    列出该标识下的全部会话，最近更新的排前面。

    带消息条数：侧边栏要显示每个会话有多少轮对话，
    用一次聚合查询取回，避免在循环里逐个查（N+1）。
    """
    with get_session() as session:
        stmt = (
            select(Conversation, func.count(Message.id))
            .outerjoin(Message, Message.conversation_id == Conversation.id)
            .where(Conversation.session_key == session_key)
            .group_by(Conversation.id)
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
            .limit(limit)
        )

        return [
            {
                "id": conv.id,
                "title": conv.title or "新对话",
                "message_count": count,
                "updated_at": conv.updated_at,
            }
            for conv, count in session.execute(stmt).all()
        ]


def create_conversation(session_key: str, title: str = "新对话") -> int:
    """新建一个空会话并返回 id（用于「新建对话」按钮）。"""
    with get_session() as session:
        conversation = Conversation(session_key=session_key, title=title)
        session.add(conversation)
        session.flush()
        return conversation.id


def delete_conversation(conversation_id: int) -> bool:
    """删除会话及其全部消息。返回是否删掉了东西。"""
    with get_session() as session:
        conversation = session.get(Conversation, conversation_id)
        if conversation is None:
            return False

        # messages 关系配了 cascade="all, delete-orphan"，删会话会连带删消息
        session.delete(conversation)
        return True


def conversation_exists(conversation_id: int) -> bool:
    """校验会话是否还存在（切换会话后可能已被删除）。"""
    with get_session() as session:
        return session.get(Conversation, conversation_id) is not None


def add_message(conversation_id: int, role: str, content: str, sources: list | None = None) -> int:
    """追加一条消息。返回消息 id。"""
    with get_session() as session:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content or "",
            sources_json=json.dumps(sources or [], ensure_ascii=False),
        )
        session.add(message)

        # 首条用户提问作为会话标题，方便以后做会话列表
        conversation = session.get(Conversation, conversation_id)
        if conversation is not None:
            if role == "user" and conversation.title == "新对话":
                conversation.title = (content or "")[:50]
            conversation.updated_at = datetime.now()

        session.flush()
        return message.id


def load_messages(conversation_id: int) -> list[dict]:
    """按顺序读出会话的全部消息，sources 反序列化回列表。"""
    with get_session() as session:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id)
        )
        result = []
        for m in session.scalars(stmt):
            try:
                sources = json.loads(m.sources_json) if m.sources_json else []
            except (ValueError, TypeError):
                logger.warning(f"[db]消息 {m.id} 的来源字段解析失败，按空处理")
                sources = []
            result.append({"role": m.role, "content": m.content, "sources": sources})
        return result


def clear_conversation(conversation_id: int) -> int:
    """清空某会话的全部消息，返回删除条数。会话本身保留。"""
    with get_session() as session:
        messages = list(session.scalars(
            select(Message).where(Message.conversation_id == conversation_id)
        ))
        for m in messages:
            session.delete(m)
        return len(messages)


# ---------------------------------------------------------------- 埋点

def record_llm_call(conversation_id, model_name: str, input_tokens: int = 0,
                    output_tokens: int = 0, latency_ms: float = 0.0,
                    tool_name: str = "", status: str = "ok") -> None:
    """
    记录一次模型调用。

    ponytail: 写库失败只记日志不抛出 —— 埋点是观测手段，不该因为它挂掉整个问答。
    """
    try:
        with get_session() as session:
            session.add(LlmCall(
                conversation_id=conversation_id,
                model_name=model_name or "",
                tool_name=tool_name or "",
                input_tokens=input_tokens or 0,
                output_tokens=output_tokens or 0,
                latency_ms=latency_ms or 0.0,
                status=status,
            ))
    except Exception as e:
        logger.warning(f"[db]埋点写入失败：{str(e)}")


def usage_summary() -> dict:
    """汇总 token 用量与调用次数，供成本看板使用。"""
    with get_session() as session:
        total_calls = session.scalar(select(func.count(LlmCall.id))) or 0
        total_in = session.scalar(select(func.coalesce(func.sum(LlmCall.input_tokens), 0))) or 0
        total_out = session.scalar(select(func.coalesce(func.sum(LlmCall.output_tokens), 0))) or 0
        avg_latency = session.scalar(select(func.coalesce(func.avg(LlmCall.latency_ms), 0.0))) or 0.0

        return {
            "calls": total_calls,
            "input_tokens": int(total_in),
            "output_tokens": int(total_out),
            "avg_latency_ms": round(float(avg_latency), 1),
        }
