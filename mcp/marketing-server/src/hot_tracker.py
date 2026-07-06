"""
热点追踪模块 V2 — 搜索策略 + 热度存储

数据流：
  MCP: 提供搜索策略 → 执行搜索 → 去重评分 → 存储结果
  Agent: 读取热点数据 → 分析趋势 → 生成选题建议
"""

from datetime import datetime, timedelta
from database import get_conn

# ============================================================
# 搜索策略配置（仅提供搜索关键词模板）
# ============================================================

SEARCH_STRATEGIES = {
    "lawyer": {
        "name": "律师行业",
        "dimensions": {
            "政策法规": {
                "keywords": ["法律法规 新出台", "司法新规 2025", "最高法 最新通知", "立法动态 法律 新规"],
                "weight": 3,
                "content_type": "解读分析",
            },
            "热点案件": {
                "keywords": ["热点案件 法律 判决", "重大案件 开庭 审理", "明星打官司 法律", "网红 法律纠纷"],
                "weight": 4,
                "content_type": "案例评析",
            },
            "行业趋势": {
                "keywords": ["律师行业 趋势 2025", "律师事务所 数字化", "法律科技 AI 律师", "青年律师 发展"],
                "weight": 2,
                "content_type": "行业观察",
            },
            "民生普法": {
                "keywords": ["劳动仲裁 维权 热搜", "婚姻财产 离婚 热门", "租房 合同纠纷 维权", "消费者 权益 保护 案例"],
                "weight": 3,
                "content_type": "普法科普",
            },
            "求职就业": {
                "keywords": ["法考 通过率 2025", "律师 招聘 求职", "法学生 就业 方向", "律师助理 实习"],
                "weight": 1,
                "content_type": "职业指导",
            },
        },
    }
}


def get_search_strategy(industry: str = "lawyer") -> dict:
    """获取指定行业的完整搜索策略"""
    strategy = SEARCH_STRATEGIES.get(industry, SEARCH_STRATEGIES["lawyer"])
    dimensions = []
    for dim_name, dim_config in strategy["dimensions"].items():
        dimensions.append({
            "name": dim_name,
            "keywords": dim_config["keywords"],
            "weight": dim_config["weight"],
            "content_type": dim_config["content_type"],
        })
    return {
        "industry": strategy["name"],
        "dimensions": dimensions,
        "total_queries": sum(len(d["keywords"]) for d in dimensions),
        "instruction": "请使用 agent-reach 对每个维度的关键词逐一搜索，汇总结果后调用 analyze_hot_topics 分析",
    }


def analyze_hot_topics(raw_topics: list, industry: str = "lawyer") -> dict:
    """
    对原始搜索结果进行去重、评分、存储。
    不进行关键词匹配式的内容分析，深度分析由 Agent 完成。
    
    raw_topics: [{title, description, source, url, heat_score?}, ...]
    
    Returns:
        {"top": [...], "total": int, "fresh_count": int, "note": str}
    """
    strategy = SEARCH_STRATEGIES.get(industry, SEARCH_STRATEGIES["lawyer"])

    # 1. 去重 + 基础评分（标题长度+来源权重）
    seen_titles = set()
    scored = []
    for topic in raw_topics:
        title = (topic.get("title") or "").strip()
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)

        # 基础分：标题长度（长标题通常信息更丰富）
        base = min(len(title) / 20, 5)
        # 来源加分
        source_bonus = 1 if topic.get("source") else 0
        # 外部热度分（如果提供）
        external = float(topic.get("heat_score", 0)) if topic.get("heat_score") else 0

        total_score = base + source_bonus + external
        topic["total_score"] = round(total_score, 2)
        scored.append(topic)

    # 2. 按总分排序取前 10
    scored.sort(key=lambda x: x["total_score"], reverse=True)
    top = scored[:15]  # 多取一些供 Agent 筛选

    # 3. 历史去重
    existing = _get_existing_topics()
    fresh = [t for t in top if t["title"] not in existing]
    
    # 4. 存储到 DB
    conn = get_conn("knowledge")
    for topic in fresh[:10]:
        conn.execute(
            "INSERT INTO hot_topics (platform, topic, description, heat_score, trend, related_keywords) VALUES (?, ?, ?, ?, ?, ?)",
            (
                topic.get("platform") or topic.get("source", "unknown"),
                topic["title"],
                topic.get("description", "")[:500],
                topic.get("total_score", 0),
                "new",
                "[]",
            )
        )
    conn.commit()
    conn.close()

    return {
        "top": top[:10],
        "total_raw": len(raw_topics),
        "after_dedup": len(scored),
        "fresh_count": len(fresh),
        "note": f"共采集 {len(raw_topics)} 条，去重后 {len(scored)} 条，新增 {len(fresh)} 条。深度趋势分析由 Agent 完成。",
    }


def _get_existing_topics(days: int = 7) -> set:
    """获取近期已存储的热点标题，用于去重"""
    conn = get_conn("knowledge")
    since = (datetime.now() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT topic FROM hot_topics WHERE captured_at >= ?",
        (since,)
    ).fetchall()
    conn.close()
    return {r["topic"] for r in rows}


def get_content_suggestions(hot_topic: dict) -> dict:
    """
    基于热点内容生成基础选题建议。
    仅提供数据层面建议（平台、时效性），具体内容角度由 Agent 分析。
    """
    title = hot_topic.get("title", "")
    description = hot_topic.get("description", "")
    content_type = hot_topic.get("content_type", "普法科普")

    # 平台匹配（纯数据：给出各平台的基础匹配度）
    platform_scores = {
        "xiaohongshu": 3,
        "douyin": 3,
        "wechat": 3,
    }

    return {
        "hot_topic": title,
        "content_type": content_type,
        "platform_scores": platform_scores,
        "suggested_platforms": sorted(platform_scores, key=platform_scores.get, reverse=True)[:2],
        "note": "具体内容角度和切入点由 Agent 基于热点原文和受众分析生成",
        "raw": {"title": title, "desc": description[:200]},
    }


def get_historical_trends(days: int = 30) -> dict:
    """查看历史热点追踪记录"""
    conn = get_conn("knowledge")
    since = (datetime.now() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT topic, description, platform, captured_at FROM hot_topics WHERE captured_at >= ? ORDER BY captured_at DESC",
        (since,)
    ).fetchall()
    conn.close()

    return {
        "period_days": days,
        "total": len(rows),
        "topics": [dict(r) for r in rows],
        "trend_insight": f"近 {days} 天共追踪到 {len(rows)} 个热点" if rows else "暂无历史数据",
    }


# ============================================================
# 搜索工具检测与降级
# ============================================================

SEARCH_TOOL_OPTIONS = {
    "agent-reach": {
        "name": "Agent Reach",
        "platforms": ["小红书", "微博", "知乎", "B站", "Twitter", "百度", "全网"],
        "check_command": "which agent-reach || echo \'not found\'",
        "capability": "多平台社交搜索",
        "usage": "agent-reach: 搜索「{query}」{platform}",
    },
    "anysearch": {
        "name": "AnySearch",
        "platforms": ["全网"],
        "check_command": "which anysearch || echo \'not found\'",
        "capability": "通用网页搜索",
        "usage": "使用 anysearch 搜索「{query}」",
    },
    "web_search": {
        "name": "Web Search",
        "platforms": ["全网"],
        "check_command": None,
        "capability": "通用网页搜索（Codex 内置）",
        "usage": "使用 web_search 搜索「{query}」",
    },
}

def check_search_tools() -> dict:
    """检测当前环境可用的搜索工具"""
    import shutil

    available = []
    unavailable = []

    if shutil.which("agent-reach"):
        available.append({
            "tool": "agent-reach",
            "name": "Agent Reach",
            "platforms": ["小红书", "微博", "知乎", "B站"],
            "priority": 1,
        })
    else:
        unavailable.append({"tool": "agent-reach", "reason": "未安装", "install_guide": "参考：https://github.com/Panniantong/Agent-Reach"})

    if shutil.which("anysearch"):
        available.append({
            "tool": "anysearch",
            "name": "AnySearch",
            "platforms": ["全网"],
            "priority": 2,
        })
    else:
        unavailable.append({"tool": "anysearch", "reason": "未安装"})

    available.append({
        "tool": "web_search",
        "name": "Web Search (Codex 内置)",
        "platforms": ["全网"],
        "priority": 3,
    })

    return {
        "available": sorted(available, key=lambda x: x["priority"]),
        "unavailable": unavailable,
        "best_tool": available[0] if available else {"tool": "web_search", "name": "Web Search"},
        "recommendation": (
            "推荐安装 agent-reach 以获得多平台社交搜索能力"
            if any(u["tool"] == "agent-reach" for u in unavailable)
            else "当前搜索工具齐全"
        ),
        "fallback_plan": _generate_fallback(available),
    }


def _generate_fallback(available: list) -> list:
    """根据可用工具生成搜索执行计划"""
    plan = []
    tool_names = [a["tool"] for a in available]

    if "agent-reach" in tool_names:
        plan.append("主方案：使用 agent-reach 进行多平台搜索")
    elif "anysearch" in tool_names:
        plan.append("替代方案：使用 anysearch 进行通用网页搜索")
    else:
        plan.append("兜底方案：使用 web_search（Codex 内置）进行搜索")

    plan.append("搜索完成后，调用 analyze_hot_topics 分析结果")
    return plan


def get_search_instruction(industry: str = "lawyer") -> dict:
    """获取完整的搜索执行指令（含工具检测）"""
    tools = check_search_tools()
    strategy = get_search_strategy(industry)
    best = tools["best_tool"]

    return {
        "industry": strategy["industry"],
        "tool": best,
        "dimensions": strategy["dimensions"],
        "fallback": tools["fallback_plan"],
        "workflow": [
            f"1. 检查到可用工具：{best['name']}",
            "2. 按5个维度逐一搜索（每个维度4个关键词）",
            "3. 汇总所有搜索结果",
            "4. 调用 analyze_topics 分析",
            "5. 输出热点榜单 + 选题建议",
            "6. 调用 store_knowledge 存储",
        ],
    }
