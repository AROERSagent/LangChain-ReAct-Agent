"""
一次性数据迁移：把 data/external/records.csv 导入数据库。

用法：
    python -m db.import_records

可以重复执行：按 (用户, 月份) 去重，已存在的记录不会重复插入。
"""
import csv
import os
import sys

from db.database import init_db
from db.repository import import_usage_records, list_known_users
from utils.config_handler import agent_conf
from utils.path_tool import get_abs_path


def parse_csv(path: str) -> list[dict]:
    """
    解析 records.csv。

    文件按 UTF-8 读取（原 CSV 是中文表头）。
    注意字段里可能有字面量 \\n 转义，保持原样存入数据库，
    展示时由前端或模型自行处理。
    """
    rows: list[dict] = []

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            # 表头是中文，这里映射成英文字段名，与模型层对齐
            rows.append({
                "user_id": (raw.get("用户ID") or "").strip(),
                "feature": (raw.get("特征") or "").strip(),
                "efficiency": (raw.get("清洁效率") or "").strip(),
                "consumables": (raw.get("耗材") or "").strip(),
                "comparison": (raw.get("对比") or "").strip(),
                "month": (raw.get("时间") or "").strip(),
            })

    # 过滤掉缺关键字段的脏行
    return [r for r in rows if r["user_id"] and r["month"]]


def main() -> int:
    csv_path = get_abs_path(agent_conf["external_data_path"])

    if not os.path.exists(csv_path):
        print(f"[导入失败]找不到文件：{csv_path}")
        return 1

    init_db()

    rows = parse_csv(csv_path)
    print(f"[导入]解析到 {len(rows)} 条记录：{csv_path}")

    inserted = import_usage_records(rows)
    print(f"[导入]新增 {inserted} 条，跳过 {len(rows) - inserted} 条（已存在）")
    print(f"[导入]当前库中用户：{list_known_users()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
