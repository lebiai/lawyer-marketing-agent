"""内容数据分析模块"""
from datetime import datetime, timedelta
from database import get_conn

def get_content_stats(days: int = 30) -> dict:
    """获取近期内容统计数据"""
    conn = get_conn("knowledge")
    since = (datetime.now() - timedelta(days=days)).isoformat()
    
    total = conn.execute("SELECT COUNT(*) as c FROM my_articles").fetchone()["c"]
    
    platform_dist = {}
    cur = conn.execute("SELECT platform, COUNT(*) as c FROM my_articles GROUP BY platform")
    for row in cur.fetchall():
        platform_dist[row["platform"]] = row["c"]
    
    with_perf = conn.execute(
        "SELECT COUNT(*) as c FROM my_articles WHERE performance IS NOT NULL"
    ).fetchone()["c"]
    
    recent = conn.execute(
        "SELECT platform, title, created_at FROM my_articles ORDER BY created_at DESC LIMIT 10"
    ).fetchall()
    
    samples = conn.execute("SELECT COUNT(*) as c FROM content_samples").fetchone()["c"]
    
    growth = conn.execute(
        "SELECT COUNT(*) as c FROM my_articles WHERE created_at >= ?", (since,)
    ).fetchone()["c"]
    
    conn2 = get_conn("profile")
    conversations = conn2.execute("SELECT COUNT(*) as c FROM conversation_logs").fetchone()["c"]
    conv_growth = conn2.execute(
        "SELECT COUNT(*) as c FROM conversation_logs WHERE created_at >= ?", (since,)
    ).fetchone()["c"]
    conn2.close()
    
    conn.close()
    
    return {
        "total_articles": total,
        "platform_distribution": platform_dist,
        "articles_with_performance_data": with_perf,
        "style_samples": samples,
        "recent_articles": [dict(r) for r in recent],
        "period_days": days,
        "growth": {
            "articles_grown": growth,
            "conversations_grown": conv_growth,
            "total_conversations": conversations
        }
    }

def analyze_performance(articles_data: list) -> dict:
    """分析文章效果数据（需用户提供）"""
    if not articles_data:
        return {"error": "请提供文章效果数据"}
    total_engagement = 0
    best = None
    for art in articles_data:
        eng = art.get("likes", 0) + art.get("favorites", 0) + art.get("comments", 0)
        if eng > total_engagement:
            total_engagement = eng
            best = art
    return {
        "total_articles_analyzed": len(articles_data),
        "total_engagement": total_engagement,
        "best_performing": best,
        "suggestion": (
            f"表现最好的内容是「{best['title']}」" if best else "暂无数据"
        )
    }
