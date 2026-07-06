"""内容排期模块"""
from datetime import datetime, timedelta

WEEKLY_TEMPLATES = {
    "balanced": {
        "name": "均衡型（每周3篇）",
        "schedule": [
            {"day": "周一", "platform": "公众号", "content_type": "深度长文/案例解读"},
            {"day": "周三", "platform": "抖音", "content_type": "口播科普/热点点评"},
            {"day": "周五", "platform": "小红书", "content_type": "图文干货/避坑指南"}
        ]
    },
    "intensive": {
        "name": "高频型（每周5篇）",
        "schedule": [
            {"day": "周一", "platform": "公众号", "content_type": "深度长文"},
            {"day": "周二", "platform": "小红书", "content_type": "知识卡片"},
            {"day": "周三", "platform": "抖音", "content_type": "口播"},
            {"day": "周四", "platform": "小红书", "content_type": "案例分享"},
            {"day": "周五", "platform": "抖音", "content_type": "热点点评"}
        ]
    },
    "focused": {
        "name": "聚焦型（每周2篇）",
        "schedule": [
            {"day": "周三", "platform": "抖音", "content_type": "口播科普"},
            {"day": "周六", "platform": "公众号", "content_type": "深度分析"}
        ]
    }
}

DAY_MAP = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6}

def generate_calendar(template_name: str = "balanced", start_date: str = None) -> dict:
    template = WEEKLY_TEMPLATES.get(template_name, WEEKLY_TEMPLATES["balanced"])
    if not start_date:
        start_date = datetime.now().strftime("%Y-%m-%d")
    start = datetime.strptime(start_date, "%Y-%m-%d")
    
    weeks = []
    for w in range(4):
        week = []
        for item in template["schedule"]:
            target = DAY_MAP[item["day"]]
            date = start + timedelta(days=w * 7 + target)
            week.append({
                "date": date.strftime("%Y-%m-%d"),
                "day": item["day"],
                "platform": item["platform"],
                "content_type": item["content_type"],
                "status": "待创作"
            })
        weeks.append({"week": w + 1, "items": week})
    
    return {
        "template": template["name"],
        "start_date": start_date,
        "weeks": weeks,
        "total_items": len(template["schedule"]) * 4
    }

def get_templates() -> dict:
    return {k: {"name": v["name"], "count": len(v["schedule"])} 
            for k, v in WEEKLY_TEMPLATES.items()}
