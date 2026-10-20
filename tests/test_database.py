"""
数据层自测。

不依赖 pytest，直接 python -m tests.test_database 运行。
覆盖：建表、导入去重、单条/区间查询、会话读写、清空。
"""
import os
import sys

# 测试用独立数据库文件，避免污染开发数据
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_test_react_agent.db")


def _setup_test_db():
    """把连接串指向测试库，再重建表。"""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    import utils.config_handler as ch
    ch.database_conf["url"] = f"sqlite:///{TEST_DB}"

    # db.database 在导入时就建好了 engine，这里重新加载模块让它读到新配置
    for mod in [m for m in list(sys.modules) if m.startswith("db.")]:
        del sys.modules[mod]

    from db.database import init_db
    init_db()


def test_import_and_query():
    from db.repository import import_usage_records, query_usage_range, query_usage_record

    rows = [
        {"user_id": "1001", "month": "2025-01", "feature": "65㎡", "efficiency": "85%",
         "consumables": "主刷60天", "comparison": "优于同类"},
        {"user_id": "1001", "month": "2025-02", "feature": "65㎡", "efficiency": "86%",
         "consumables": "主刷55天", "comparison": "优于同类"},
        {"user_id": "1002", "month": "2025-01", "feature": "70㎡", "efficiency": "88%",
         "consumables": "边刷中度", "comparison": "低于同类"},
    ]

    assert import_usage_records(rows) == 3, "首次导入应写入 3 条"

    # 幂等：同一份数据再导一次不应产生重复
    assert import_usage_records(rows) == 0, "重复导入不应新增记录"

    # 单条查询
    rec = query_usage_record("1001", "2025-01")
    assert rec is not None, "应能查到 1001 在 2025-01 的记录"
    assert rec["特征"] == "65㎡", f"特征字段错误：{rec['特征']}"

    # 未命中返回 None，而不是抛异常
    assert query_usage_record("9999", "2025-01") is None, "不存在的用户应返回 None"
    assert query_usage_record("1001", "1999-01") is None, "不存在的月份应返回 None"

    # 区间查询，且必须按月份升序
    rng = query_usage_range("1001", "2025-01", "2025-02")
    assert len(rng) == 2, f"区间查询应返回 2 条，实际 {len(rng)}"
    assert [r["月份"] for r in rng] == ["2025-01", "2025-02"], "区间结果应按月份升序"

    # 区间边界不能串到别的用户
    rng2 = query_usage_range("1002", "2025-01", "2025-12")
    assert len(rng2) == 1, "用户 1002 只应有一条记录"

    print("  ✓ 导入去重 / 单条查询 / 未命中 / 区间查询")


def test_conversation():
    from db.repository import (add_message, clear_conversation, get_or_create_conversation,
                               load_messages)

    cid = get_or_create_conversation("test-session")
    assert isinstance(cid, int) and cid > 0, "应返回有效的会话 id"

    # 同一 session_key 再取应复用同一会话
    assert get_or_create_conversation("test-session") == cid, "同一标识应复用会话"

    # 不同标识应隔离，这是多用户不串话的基础
    other = get_or_create_conversation("other-session")
    assert other != cid, "不同标识应得到不同会话"

    uid = add_message(cid, "user", "扫地机器人回充失败怎么办？")
    add_message(cid, "assistant", "先检查回充传感器", sources=[{"index": 1, "file": "故障排除.txt"}])

    msgs = load_messages(cid)
    assert len(msgs) == 2, f"应读出 2 条消息，实际 {len(msgs)}"
    assert msgs[0]["role"] == "user" and msgs[1]["role"] == "assistant", "消息顺序错误"
    assert msgs[1]["sources"][0]["file"] == "故障排除.txt", "来源 JSON 未正确往返"

    # 会话标题应取首条提问
    from db.database import get_session
    from db.models import Conversation
    with get_session() as s:
        conv = s.get(Conversation, cid)
        assert conv.title.startswith("扫地机器人"), f"标题应取自首条提问，实际：{conv.title}"

    # 清空只删消息，保留会话
    assert clear_conversation(cid) == 2, "应删除 2 条消息"
    assert load_messages(cid) == [], "清空后应无消息"
    assert get_or_create_conversation("test-session") == cid, "清空后会话本身应保留"

    # 通过 id 校验：空会话的 id 必须仍是原值
    assert uid > 0, "add_message 应返回消息 id"

    print("  ✓ 会话隔离 / 消息读写 / 来源往返 / 标题生成 / 清空")


def test_llm_call_logging():
    from db.repository import record_llm_call, usage_summary

    before = usage_summary()
    record_llm_call(None, "qwen-max", input_tokens=100, output_tokens=20, latency_ms=1500.0)
    record_llm_call(None, "qwen-max", input_tokens=200, output_tokens=40, latency_ms=2500.0)

    after = usage_summary()
    assert after["calls"] == before["calls"] + 2, "应记录 2 次调用"
    assert after["input_tokens"] == before["input_tokens"] + 300, "输入 token 累加错误"
    assert after["output_tokens"] == before["output_tokens"] + 60, "输出 token 累加错误"

    print(f"  ✓ 埋点写入 / 用量汇总（共 {after['calls']} 次调用）")


def main():
    print("开始数据层自测...")
    _setup_test_db()

    test_import_and_query()
    test_conversation()
    test_llm_call_logging()

    print("\n全部通过 ✓")


if __name__ == "__main__":
    try:
        main()
    finally:
        # 清理测试库，不留垃圾文件
        for suffix in ("", "-journal", "-wal", "-shm"):
            p = TEST_DB + suffix
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
