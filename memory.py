"""Step 5 长期记忆：把每次选品结果落盘到 data/results.json，新任务先查历史。

这就是架构图里"记忆管理"的长期部分——程序重启也不丢。
对比 chat.py 的短期记忆（对话历史列表）：那个活在内存里，关了就没；这个活在磁盘上。

运行：python memory.py   （查看已存的所有记忆摘要）
"""
import json
import os
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "results.json")


def load_all() -> list:
    """读取全部历史记忆。文件不存在/损坏都返回空列表（不崩程序）。"""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, encoding="utf-8") as f:  # Windows 必须显式 utf-8，否则中文乱码
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save(category_en: str, market: str, report: str):
    """任务完成后调用：追加一条记忆到磁盘。"""
    records = load_all()
    records.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "category_en": category_en,
        "market": market,
        "report": report,  # 完整报告文本
    })
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def find_similar(category_en: str) -> list:
    """找出历史里同品类的记录（子串匹配，简单够用；最多返回最近 3 条防上下文爆炸）。"""
    key = (category_en or "").lower()
    if not key:
        return []
    hits = [r for r in load_all() if key in r.get("category_en", "").lower()]
    return hits[-3:]


if __name__ == "__main__":
    records = load_all()
    if not records:
        print("data/results.json 还没有记忆（跑一次 agent.py 就会生成）")
    for r in records:
        print(f"{r['time']} | {r['category_en']} | {r['market']} | 报告 {len(r['report'])} 字")
