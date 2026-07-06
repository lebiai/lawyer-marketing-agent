"""热点追踪模块 — 定义搜索策略和热点分析逻辑"""

HOT_TOPIC_SEARCHES = {
    "lawyer": {
        "keywords": [
            "律师 热点 新闻",
            "法律 新规 最新",
            "律师行业 趋势",
            "律师事务所 营销",
            "法律科普 热门"
        ],
        "industry_terms": [
            "民法典", "诉讼法", "合同纠纷", "劳动争议",
            "知识产权", "婚姻法", "继承法", "侵权责任"
        ]
    }
}

def get_search_queries(industry: str = "lawyer") -> list:
    config = HOT_TOPIC_SEARCHES.get(industry, HOT_TOPIC_SEARCHES["lawyer"])
    return config["keywords"]

def filter_by_industry(topics: list, industry: str = "lawyer") -> list:
    config = HOT_TOPIC_SEARCHES.get(industry, HOT_TOPIC_SEARCHES["lawyer"])
    terms = config["industry_terms"]
    filtered = []
    for topic in topics:
        title = (topic.get("title", "") + topic.get("description", "")).lower()
        if any(term.lower() in title for term in terms):
            filtered.append(topic)
    return filtered
