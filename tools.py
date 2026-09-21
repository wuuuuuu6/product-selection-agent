"""Step 3 工具调用：工具注册表 + 统一执行器 + 真实搜索工具（Tavily）。

这是 Agent 的"手"。分工很明确：
- 模型只负责"决定调哪个工具、传什么参数"（它不执行任何东西）
- 真正执行在你的 Python 代码里
- 执行结果回灌给模型继续推理
"""
import json
import os

import httpx


# ---------- 工具实现 ----------

def search_market(keyword: str, market: str = "美国亚马逊") -> str:
    """[真实搜索] 用 Tavily 检索市场数据，返回带来源链接的网页摘要。"""
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key or api_key.startswith("在这里"):
        return "[提示] .env 里还没填 TAVILY_API_KEY，无法联网搜索"

    query = f"{keyword} {market} market trends sales pricing reviews"
    try:
        r = httpx.post(
            "https://api.tavily.com/search",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"query": query, "max_results": 5, "search_depth": "basic"},
            timeout=30,
        )
        r.raise_for_status()
        results = r.json().get("results", [])
    except Exception as e:
        return f"[错误] 搜索失败: {e}"

    if not results:
        return f"[搜索] '{keyword}' 未检索到有效结果"

    lines = [
        f"{i}. {item.get('title', '')}\n   来源: {item.get('url', '')}\n   {item.get('content', '')[:400]}"
        for i, item in enumerate(results, 1)
    ]
    return "\n\n".join(lines)


def estimate_price(cost: float, market: str = "美国亚马逊") -> str:
    """根据采购成本估算建议零售价区间（确定性规则计算，不让模型拍脑袋）。"""
    if cost <= 0:
        return "[错误] 成本必须大于 0"
    low, high = cost * 2.5, cost * 4
    return (
        f"采购成本 ${cost:.2f} 的建议零售价区间：${low:.2f} - ${high:.2f}\n"
        f"- 靠近 ${low:.0f}：走量策略，广告空间小，适合白牌起量\n"
        f"- 靠近 ${high:.0f}：需要差异化支撑（材质/功能/品牌故事）\n"
        f"倍率 2.5-4 的依据：覆盖头程物流、FBA 配送费(约$3-6/件)、亚马逊佣金15%、退货损耗与广告费(ACOS)"
    )


# ---------- 注册表：给模型看的"说明书" + 给代码用的"函数本体" ----------

TOOLS = {
    "search_market": {
        "fn": search_market,
        "spec": {
            "type": "function",
            "function": {
                "name": "search_market",
                "description": "联网搜索某品类在目标市场的真实数据（市场趋势、销量、价位、用户评价等），返回带来源链接的网页摘要。分析任何品类前必须先调用它。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string", "description": "品类英文搜索词，如 portable blender"},
                        "market": {"type": "string", "description": "目标市场，默认美国亚马逊"},
                    },
                    "required": ["keyword"],
                },
            },
        },
    },
    "estimate_price": {
        "fn": estimate_price,
        "spec": {
            "type": "function",
            "function": {
                "name": "estimate_price",
                "description": "根据采购成本(美元)用跨境电商经验倍率计算建议零售价区间。给出定价建议前必须调用；成本未知时先用搜索工具查明该品类常见采购/出厂成本，再把数值传进来。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cost": {"type": "number", "description": "单件采购成本（美元），应从搜索结果中提取并注明出处"},
                        "market": {"type": "string", "description": "目标市场，默认美国亚马逊"},
                    },
                    "required": ["cost"],
                },
            },
        },
    },
}


def get_specs():
    """给模型看的工具说明书列表（每次请求都带上）。"""
    return [t["spec"] for t in TOOLS.values()]


def execute(name: str, args_json: str) -> str:
    """统一执行器：解析参数 -> 调用函数 -> 永远返回字符串（模型只认文本）。

    注意：工具报错不抛异常崩程序，而是把错误文本回灌给模型，让它自己调整。
    """
    if name not in TOOLS:
        return f"[错误] 工具 {name} 不存在。可用工具：{list(TOOLS)}"
    try:
        args = json.loads(args_json or "{}")
        return str(TOOLS[name]["fn"](**args))
    except Exception as e:
        return f"[错误] 工具执行失败: {e}"
