"""Step 4 主循环：任务理解 -> 模型决定调工具 -> 执行 -> 结果回灌 -> 再推理 -> 最终回答。

这就是架构图中间"决策推理 ⇄ 工具调用"那个循环——Agent 与聊天机器人的分水岭。

运行：python agent.py "帮我分析便携榨汁机在美国的市场情况"
"""
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

import memory
from tools import get_specs, execute
from understand import understand

load_dotenv()
client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

SYSTEM = (
    "你是跨境电商选品分析师。工作方式：先搜索市场数据，需要深挖时把宽泛问题拆成更精准的关键词多次搜索；"
    "用户没提供成本时，先搜索该品类的常见采购/出厂成本，再用 estimate_price 计算定价建议。"
    "引用工具结果时注明来源；工具没覆盖的维度直接说'数据不足'，禁止编造。"
)


def run_agent(user_input: str, max_steps: int = 8):
    """跑一轮完整的"推理-行动"循环。

    max_steps 是保险丝：完整选品链路实测 6 轮，设 8 留余量；防止无限调工具烧钱。
    返回 (最终回答, 任务理解结果 parsed) 元组。
    """
    # 第一步：任务理解模块把模糊需求变成精确参数（失败则降级为原文直传）
    try:
        parsed = understand(user_input)
        print(f"[任务理解] 品类: {parsed.get('category_en')} | 市场: {parsed.get('market')} | 关注: {parsed.get('focus')}")
        task = (
            f"品类: {parsed.get('category_en')}（{parsed.get('category_cn', '')}）\n"
            f"市场: {parsed.get('market')}\n"
            f"用户关注: {parsed.get('focus')}\n请基于以上信息完成选品分析。"
        )
    except Exception as e:
        print(f"[任务理解] 解析失败({e})，降级为原文直传")
        parsed = {}
        task = user_input

    # 第二步：查长期记忆——同一品类分析过，就把历史结论带给模型复用
    past = memory.find_similar(parsed.get("category_en", ""))
    if past:
        print(f"[长期记忆] 命中 {len(past)} 条历史分析，注入上下文")
        brief = "\n".join(
            f"- {r['time']} 分析 {r['category_en']}（{r['market']}）：{r['report'][:300]}……"
            for r in past
        )
        task += f"\n\n历史分析参考（优先复用已有结论，只补搜缺失信息）：\n{brief}"

    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": task},
    ]

    for step in range(1, max_steps + 1):
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=get_specs(),  # <-- 每次都把"工具说明书"带给模型
        )
        msg = resp.choices[0].message

        # 情况 A：模型决定调用工具 -> 执行 -> 结果回灌 -> 继续循环
        if msg.tool_calls:
            messages.append(msg)  # 必须：把模型的"调用意图"原样存回历史
            for call in msg.tool_calls:
                print(f"  [Step {step}] 调用 {call.function.name}({call.function.arguments})")
                result = execute(call.function.name, call.function.arguments)
                print(f"  [Step {step}] 工具返回: {result[:60]}...")
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,  # 必须：和调用意图的 id 一一对应
                    "content": result,
                })
            continue

        # 情况 B：模型给出最终回答，循环结束
        print(f"\n最终回答（共 {step} 轮推理）:\n\n{msg.content}")
        memory.save(
            category_en=parsed.get("category_en") or user_input[:50],
            market=parsed.get("market") or "未指定",
            report=msg.content,
        )
        print("[长期记忆] 本次报告已存入 data/results.json")
        return msg.content, parsed

    print(f"\n[保险丝熔断] 达到 max_steps={max_steps} 上限，强制结束")


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "帮我分析便携榨汁机在美国的市场情况"
    run_agent(question)
