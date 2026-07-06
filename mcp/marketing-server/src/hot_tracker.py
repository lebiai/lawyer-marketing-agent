"""
热点追踪模块 V2 — 多维度热点分析 + 选题建议

核心流程：
  1. 多维度搜索（行业/平台/时效）
  2. 热度评分 + 平台匹配
  3. 去重 + 历史追踪
  4. 选题建议 + 内容角度
"""

from datetime import datetime, timedelta
from database import get_conn

# ============================================================
# 搜索策略配置
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

# 平台匹配度分析
PLATFORM_FIT = {
    "解读分析": {"xiaohongshu": 3, "douyin": 4, "wechat": 5},
    "案例评析": {"xiaohongshu": 5, "douyin": 5, "wechat": 4},
    "行业观察": {"xiaohongshu": 2, "douyin": 3, "wechat": 5},
    "普法科普": {"xiaohongshu": 5, "douyin": 5, "wechat": 3},
    "职业指导": {"xiaohongshu": 4, "douyin": 3, "wechat": 4},
}

# 切入角度推荐
ANGLE_TEMPLATES = {
    "解读分析": [
        "新规对比：旧规 vs 新规，变化在哪",
        "直接影响：这条新规对普通人意味着什么",
        "深度拆解：条文背后的立法意图",
    ],
    "案例评析": [
        "案情回顾：发生了什么",
        "法律分析：法院为什么这么判",
        "警示意义：我们能学到什么",
    ],
    "行业观察": [
        "趋势解读：行业正在发生什么变化",
        "数据说话：用数据说明趋势",
        "未来预测：接下来会怎么发展",
    ],
    "普法科普": [
        "避坑指南：常见错误和正确做法",
        "自检清单：你中了几条",
        "必知必会：每个人都该知道的法律常识",
    ],
    "职业指导": [
        "实用建议：给新人的X条建议",
        "经验分享：过来人怎么说",
        "路径规划：怎么从入门到精通",
    ],
}


# ============================================================
# 核心功能
# ============================================================

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
    对原始搜索结果进行热度分析、平台匹配、选题建议
    raw_topics: [{title, description, source, url, heat_score?}, ...]
    """
    strategy = SEARCH_STRATEGIES.get(industry, SEARCH_STRATEGIES["lawyer"])
    
    # 1. 去重 + 评分
    scored = _score_and_dedup(raw_topics, strategy)
    
    # 2. 按热度排序取前10
    scored.sort(key=lambda x: x["total_score"], reverse=True)
    top = scored[:10]
    
    # 3. 历史去重（检查hot_topics表）
    existing = _get_existing_topics()
    fresh = [t for t in top if t["title"] not in existing]
    
    # 4. 为每个热点生成平台匹配和选题建议
    results = []
    for topic in fresh:
        content_type = topic.get("content_type", "普法科普")
        platforms = PLATFORM_FIT.get(content_type, {})
        
        # 找出最适合的平台
        best_platforms = sorted(platforms.items(), key=lambda x: x[1], reverse=True)
        recommended = [p[0] for p in best_platforms if p[1] >= 4]
        
        # 选题角度
        angles = ANGLE_TEMPLATES.get(content_type, [])
        
        results.append({
            "title": topic["title"],
            "description": topic.get("description", ""),
            "source": topic.get("source", "未知"),
            "content_type": content_type,
            "heat_level": topic["heat_level"],
            "total_score": topic["total_score"],
            "recommended_platforms": recommended,
            "content_angles": angles[:3],
            "is_new": topic["title"] not in existing,
        })
    
    # 5. 汇总统计
    stats = {
        "total_raw": len(raw_topics),
        "after_dedup": len(scored),
        "fresh_topics": len(fresh),
        "existing_topics": len(top) - len(fresh),
        "dimension_breakdown": {},
    }
    for t in results:
        ct = t["content_type"]
        stats["dimension_breakdown"][ct] = stats["dimension_breakdown"].get(ct, 0) + 1
    
    return {
        "industry": strategy["name"],
        "analyzed_at": datetime.now().isoformat(),
        "hot_topics": results,
        "statistics": stats,
    }


def _score_and_dedup(raw_topics: list, strategy: dict) -> list:
    """去重 + 热度评分"""
    seen = set()
    scored = []
    
    # 收集所有行业术语
    all_terms = []
    for dim_config in strategy["dimensions"].values():
        all_terms.extend(dim_config["keywords"])
    
    for topic in raw_topics:
        title = topic.get("title", "").strip()
        if not title or title in seen:
            continue
        seen.add(title)
        
        desc = topic.get("description", "")
        full_text = (title + " " + desc).lower()
        
        # 基础热度（默认中）
        heat = topic.get("heat_score", 50)
        
        # 行业相关度加分
        relevance = sum(1 for term in all_terms if any(w in full_text for w in term.split()))
        relevance_bonus = min(relevance * 5, 30)
        
        # 多维度热度加分
        dims = topic.get("source", "")
        source_bonus = 10 if "小红书" in dims or "热搜" in dims else 0
        
        total = heat + relevance_bonus + source_bonus
        
        # 热度等级
        if total >= 80:
            level = "🔥🔥🔥 高"
        elif total >= 50:
            level = "🔥🔥 中"
        else:
            level = "🔥 低"
        
        # 判断内容类型
        content_type = _classify_content(full_text, strategy)
        
        scored.append({
            "title": title,
            "description": desc,
            "source": topic.get("source", "未知"),
            "heat_score": heat,
            "relevance_bonus": relevance_bonus,
            "total_score": total,
            "heat_level": level,
            "content_type": content_type,
        })
    
    return scored


def _classify_content(text: str, strategy: dict) -> str:
    """根据文本判断内容类型"""
    type_keywords = {
        "解读分析": ["新规", "出台", "实施", "修改", "条例", "修正", "发布"],
        "热点案件": ["案", "开庭", "判决", "审理", "上诉", "起诉", "打官司"],
        "行业观察": ["趋势", "发展", "增长", "数字化", "转型", "市场"],
        "普法科普": ["注意", "警惕", "维权", "权益", "保护", "避坑", "指南"],
        "职业指导": ["法考", "招聘", "求职", "工资", "实习", "就业"],
    }
    scores = {}
    for ct, keywords in type_keywords.items():
        scores[ct] = sum(1 for kw in keywords if kw in text)
    if any(scores.values()):
        return max(scores, key=scores.get)
    return "普法科普"


def _get_existing_topics(days: int = 7) -> set:
    """获取近期已追踪过的热点（去重用）"""
    conn = get_conn("knowledge")
    since = (datetime.now() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT topic FROM hot_topics WHERE captured_at >= ?", (since,)
    ).fetchall()
    conn.close()
    return {row["topic"] for row in rows}


def get_content_suggestions(hot_topic: dict) -> dict:
    """
    针对单个热点，生成完整的创作建议
    包括：选题角度、平台建议、标题方向、最佳发布时间
    """
    content_type = hot_topic.get("content_type", "普法科普")
    title = hot_topic.get("title", "")
    
    # 选题角度
    angles = ANGLE_TEMPLATES.get(content_type, ["深度分析"])
    
    # 平台匹配
    platform_scores = PLATFORM_FIT.get(content_type, {})
    ranked = sorted(platform_scores.items(), key=lambda x: x[1], reverse=True)
    
    # 标题方向
    title_suggestions = []
    for angle in angles[:3]:
        title_suggestions.append(f"「{title}」｜{angle}")
    
    return {
        "topic": title,
        "content_type": content_type,
        "suggestions": {
            "angles": angles,
            "best_platforms": [p[0] for p in ranked if p[1] >= 3],
            "title_directions": title_suggestions,
            "timing": "热点发布后 24 小时内跟进效果最佳",
        },
    }


def get_historical_trends(days: int = 30) -> dict:
    """查看历史热点趋势"""
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
