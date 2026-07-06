"""评论助手模块 V2 — 中文关键词匹配"""

REPLY_TEMPLATES = {
    "thanks": {
        "label": "感谢互动",
        "templates": [
            "谢谢支持！有法律问题随时问我 🙌",
            "感谢关注，后续会分享更多法律干货 📚",
            "谢谢！觉得有用的话可以转发给需要的朋友 🤝"
        ]
    },
    "question": {
        "label": "回答法律问题",
        "templates": [
            "这个问题比较常见，简单来说：{answer}。建议具体案情咨询专业律师。",
            "根据法律规定，{answer}。建议收集好相关证据。",
            "好的，我简单解释一下：{answer}。如果情况复杂建议当面咨询。"
        ]
    },
    "disagree": {
        "label": "处理不同意见",
        "templates": [
            "理解你的观点，这个问题在实践中确实有不同看法，我的分析是基于{reason}。",
            "谢谢补充！这也是一个角度，在实践中需要根据具体情况判断。",
            "好的，你说得有道理。法律问题往往不是非黑即白的。"
        ]
    },
    "promote": {
        "label": "引导关注",
        "templates": [
            "觉得有用的话点个❤️，让更多人看到！",
            "关注我，每天学点法律知识 🔔",
            "还有什么法律问题想了解的？评论区告诉我 💬"
        ]
    }
}


def suggest_reply(comment: str, category: str = None) -> dict:
    """根据评论内容和可选分类推荐回复话术"""
    if not category:
        if any(w in comment for w in ["谢谢", "感谢", "赞", "棒", "有用", "好"]):
            category = "thanks"
        elif "?" in comment or "？" in comment or "吗" in comment or "怎么" in comment or "如何" in comment or "什么" in comment:
            category = "question"
        elif any(w in comment for w in ["不对", "不同意", "错了", "不是", "不对"]):
            category = "disagree"
        else:
            category = "thanks"

    templates = REPLY_TEMPLATES.get(category, REPLY_TEMPLATES["thanks"])
    return {
        "category": templates["label"],
        "original_comment": comment,
        "suggestions": templates["templates"],
        "tip": "建议根据具体情况微调后回复，保持人设一致性"
    }


def analyze_sentiment(comments: list) -> dict:
    """批量分析评论情感倾向"""
    total = len(comments)
    if total == 0:
        return {"total": 0, "error": "无评论数据"}

    positive = sum(1 for c in comments if any(w in c for w in ["谢谢", "赞", "好", "棒", "有用", "感谢", "收藏"]))
    questioning = sum(1 for c in comments if "?" in c or "？" in c or "吗" in c or "怎么" in c or "如何" in c)
    negative = sum(1 for c in comments if any(w in c for w in ["不对", "错了", "差", "不好", "没用", "坑"]))
    other = total - positive - questioning - negative

    return {
        "total": total,
        "sentiment": {
            "正面": positive,
            "提问": questioning,
            "负面": negative,
            "其他": other
        },
        "positive_rate": round(positive / total * 100, 1) if total > 0 else 0,
        "suggestion": "评论区总体积极，建议重点回复提问类评论" if questioning > 0 else "评论区互动良好"
    }
