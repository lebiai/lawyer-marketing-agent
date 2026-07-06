"""竞品账号分析模块"""

ANALYSIS_DIMENSIONS = {
    "content_strategy": {
        "label": "内容策略",
        "questions": [
            "主要发布什么类型的内容？（科普/案例/观点/干货）",
            "更新频率如何？（日更/周更/不定时）",
            "内容长度偏好？（短图文/长文/视频）"
        ]
    },
    "style_features": {
        "label": "风格特征",
        "questions": [
            "语气风格？（严肃/幽默/亲切/犀利）",
            "排版特点？（emoji使用/分段方式/视觉风格）",
            "人设定位？（专家/朋友/吐槽/导师）"
        ]
    },
    "engagement": {
        "label": "互动表现",
        "questions": [
            "平均点赞/收藏/评论数据？",
            "哪类内容互动最高？",
            "评论区用户主要在问什么？"
        ]
    },
    "top_topics": {
        "label": "高频话题",
        "questions": [
            "最常讨论的3-5个话题是什么？",
            "这些话题的切入角度有何特点？",
            "有没有形成系列或专栏？"
        ]
    }
}

def generate_analysis_report(account_name: str, platform: str, raw_data: dict) -> str:
    lines = []
    lines.append(f"📊 竞品账号分析报告：{account_name}")
    lines.append(f"📌 平台：{platform}")
    lines.append("")
    for dim_key, dim_info in ANALYSIS_DIMENSIONS.items():
        lines.append(f"【{dim_info['label']}】")
        for q in dim_info["questions"]:
            lines.append(f"  ▸ {q}")
        lines.append("")
    return "\n".join(lines)

def extract_style_tags(report_text: str) -> list:
    tags = []
    style_keywords = {
        "专业": ["专业", "权威", "严谨"],
        "幽默": ["幽默", "搞笑", "段子"],
        "亲切": ["亲切", "朋友", "接地气"],
        "犀利": ["犀利", "尖锐", "敢说"],
        "温和": ["温和", "耐心", "温柔"]
    }
    for tag, keywords in style_keywords.items():
        if any(kw in report_text for kw in keywords):
            tags.append(tag)
    return tags
