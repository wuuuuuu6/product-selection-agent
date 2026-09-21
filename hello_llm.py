"""Step 0 连通性验证：让你的 Agent 第一次开口说话。

运行：python hello_llm.py
预期：终端打印 DeepSeek 的回复 + 本次消耗的 token 数。
"""
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # 读取同目录下的 .env 文件

api_key = os.environ.get("DEEPSEEK_API_KEY", "")
if not api_key or "粘贴" in api_key:
    raise SystemExit(
        "\n[还没填 Key] 打开 .env 文件，把 DEEPSEEK_API_KEY= 后面\n"
        "替换成你在 platform.deepseek.com 创建的 sk- 开头密钥，再运行一次。\n"
    )

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",  # DeepSeek 兼容 OpenAI 协议，只需改这一行
)

resp = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是一个简洁的助手，回答不超过两句话。"},
        {"role": "user", "content": "用一句话介绍你自己，并报出你的模型名。"},
    ],
)

print(resp.choices[0].message.content)
print(f"\n[连通成功] 本次消耗 {resp.usage.total_tokens} tokens")
