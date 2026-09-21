"""Step 1 对话内核：多轮对话 + 短期记忆（messages 列表）+ 历史裁剪。

运行：python chat.py    退出：输入 q
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

MAX_HISTORY = 20  # 短期记忆容量：超过就裁掉最旧的对话


def build_messages(history):
    """每次请求实际发送的内容 = 人设(system) + 最近的历史。

    system 每次单独加回来，所以裁剪永远不会弄丢人设。
    """
    system = {
        "role": "system",
        "content": "你是一位资深跨境电商选品分析师，回答简洁、先给结论，不确定的信息要明确标注。",
    }
    return [system] + history[-MAX_HISTORY:]


def chat(history, user_input):
    """把用户输入追加进记忆 -> 请求模型 -> 把回复也存进记忆。"""
    history.append({"role": "user", "content": user_input})
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=build_messages(history),
    )
    reply = resp.choices[0].message.content
    history.append({"role": "assistant", "content": reply})
    return reply, resp.usage.total_tokens


if __name__ == "__main__":
    history = []  # <-- 短期记忆的全部真相：就是一个列表
    print("选品分析师已上线（输入 q 退出）")
    while True:
        user_input = input("\n你: ").strip()
        if user_input.lower() in ("q", "quit", "exit"):
            print("再见。")
            break
        if not user_input:
            continue
        reply, tokens = chat(history, user_input)
        print(f"分析师: {reply}   [本次 {tokens} tokens]")
