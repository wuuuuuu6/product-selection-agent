"""Step 2 任务理解：把用户一句话解析成结构化 JSON。

这是 Agent 的"耳朵"——后面所有模块只认结构化数据，不认自然语言。

运行：python understand.py "帮我分析便携榨汁机在美国亚马逊的机会"
      python understand.py "帮我看看无线鼠标在东南亚有没有机会"（可换任意问法抽测）
"""
import json
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

# 规则放 system（稳定不变的内容），用户输入放 user（每次变化的内容）
SYSTEM_RULES = """你是选品 Agent 的任务理解模块。把用户输入解析成 JSON，格式如下：
{
  "category_cn": "品类中文名",
  "category_en": "品类英文关键词（跨境电商平台最常用的搜索词）",
  "market": "目标市场，如 美国亚马逊 / 东南亚Shopee / 独立站",
  "focus": ["用户关注的点1", "点2"],
  "lang": "用户使用的语言，zh 或 en"
}

规则：
1. 只输出 JSON 本身，不要解释、不要 markdown 代码块标记。
2. 用户没提的字段用合理默认值：market 默认"美国亚马逊"；focus 默认["市场热度", "竞争格局", "定价"]。
3. category_en 必须是海外买家实际会搜的词，不要直译。"""


def understand(user_input: str) -> dict:
    """自然语言 -> 结构化 JSON。失败自动重试一次。"""
    for attempt in (1, 2):
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_RULES},
                {"role": "user", "content": user_input},
            ],
            response_format={"type": "json_object"},  # JSON 模式：从源头强制合法 JSON
            temperature=0,  # 理解任务要确定性，不要发挥
        )
        try:
            return json.loads(resp.choices[0].message.content)
        except json.JSONDecodeError:
            if attempt == 2:
                raise  # 重试还失败就抛出，让上层看到真实问题


if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) or "帮我分析便携榨汁机在美国亚马逊的机会"
    result = understand(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))
