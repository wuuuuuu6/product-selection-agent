"""Step 6 报告输出：把 Agent 的最终回答落成正式的 Markdown 报告文件。

Agent 从此有了"交付物"——不只是终端里滚过的一段话，
而是一份可存档、可发人、可放进简历演示的文件。

运行：python report.py "帮我分析桌面加湿器"
产出：data/reports/report_<品类>_<时间戳>.md
"""
import os
import sys
from datetime import datetime

from agent import run_agent

REPORT_DIR = os.path.join(os.path.dirname(__file__), "data", "reports")

FOOTER = (
    "\n---\n"
    "*本报告由 AI Agent 自动生成（无框架实现；任务理解: DeepSeek JSON 模式 / 工具调用: "
    "Tavily 实时搜索 + 规则定价 / 长期记忆: results.json）。关键数字均已标注来源，"
    "但 AI 生成内容可能存在偏差，使用前请人工抽核核心数据。*\n"
)


def write_report(parsed: dict, answer: str) -> str:
    """加报告头（元信息）和 footer，写入 data/reports/，返回文件路径。"""
    os.makedirs(REPORT_DIR, exist_ok=True)
    category_en = parsed.get("category_en") or "report"
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    path = os.path.join(REPORT_DIR, f"report_{category_en.replace(' ', '_')[:30]}_{stamp}.md")

    header = (
        f"# 选品分析报告 · {parsed.get('category_cn') or category_en}\n\n"
        f"- **品类关键词**: {category_en}\n"
        f"- **目标市场**: {parsed.get('market') or '未指定'}\n"
        f"- **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"- **生成方式**: AI Agent · 无框架实现（DeepSeek + Tavily 实时检索）\n\n---\n\n"
    )
    with open(path, "w", encoding="utf-8") as f:  # Windows 必须显式 utf-8
        f.write(header + answer + FOOTER)
    return path


if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) or "帮我分析桌面加湿器"
    answer, parsed = run_agent(text)
    if not answer:
        print("\nAgent 未产出最终回答（可能触发保险丝熔断），请重试或简化任务")
        sys.exit(1)
    path = write_report(parsed, answer)
    print(f"\n[报告] 已生成: {path}")
