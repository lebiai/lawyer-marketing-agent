"""竞品账号分析模块 V2 — 四层风格框架 + 内容策略 + 互动表现 + 高频话题

与 style_analyzer.py 共享四层分析维度，额外增加：
- 账号级内容策略分析（发布类型/频率/长度偏好）
- 互动表现分析（数据对比/高互动内容特征）
- 高频话题分析（话题聚类/切入角度）
- 风格对比能力（多账号横向对比）
"""

import re
from datetime import datetime

# ============================================================
# 一、定位与基调维度（决定账号的"气质底色"）
# ============================================================

TONE_KEYWORDS = {
    "理性客观": ["根据", "数据显示", "研究表明", "从法律角度", "事实上", "本质上", "客观来说"],
    "温暖治愈": ["温暖", "治愈", "陪伴", "别怕", "没关系", "会好的", "一起", "抱抱"],
    "犀利直白": ["说白了", "实话告诉你", "醒醒", "别再", "就是", "直接说", "废话不多说"],
    "幽默俏皮": ["哈哈", "嘻嘻", "😂", "🤣", "笑死", "搞笑", "离谱", "笑不活了"],
    "高级克制": ["或许", "可能", "某种程度上", "不妨", "值得思考", "另一种可能"],
    "热血有力": ["必须", "一定", "绝不", "站起来", "捍卫", "战斗", "改变"],
    "文艺感性": ["时光", "岁月", "温柔", "风", "月光", "山海", "人间", "值得"],
}

STANCE_KEYWORDS = {
    "平等对话": ["我们", "一起", "来", "聊聊", "讨论", "你觉得", "你怎么看"],
    "权威指导": ["记住", "一定要", "千万", "注意", "法律规定", "根据", "建议你"],
    "朋友分享": ["我", "我的", "昨天", "最近", "发现", "分享", "安利", "推荐"],
    "官方正式": ["公告", "通知", "声明", "严格", "规范", "予以", "特此"],
    "自嘲玩梗": ["我", "本", "也是醉了", "瑟瑟发抖", "卑微", "打工人", "摸鱼"],
}

AUDIENCE_KEYWORDS = {
    "普通大众": ["每个人", "大家", "所有人", "国人", "老百姓"],
    "职场人": ["职场", "同事", "老板", "职场人", "打工人", "升职"],
    "年轻人": ["年轻人", "90后", "00后", "大学生", "刚毕业"],
    "专业人士": ["从业者", "专业人士", "同行", "业内"],
    "特定场景": ["当事人", "客户", "受害者", "家属", "房东", "租客"],
}

CONTENT_TYPE_KEYWORDS = {
    "科普干货": ["科普", "干货", "教你", "指南", "攻略", "避坑", "注意", "风险"],
    "案例评析": ["案例", "判决", "案", "审理", "法院判", "裁判", "纠纷"],
    "观点评论": ["我说", "看法", "观点", "热评", "聊聊", "你怎么看", "争议"],
    "个人故事": ["我", "经历", "故事", "那年", "当初", "分享", "亲身"],
    "热点解读": ["最新", "新规", "热搜", "关注", "重磅", "刚刚", "突发"],
    "实用工具": ["模板", "表格", "清单", "公式", "步骤", "流程", "教程"],
}

# ============================================================
# 二、语言与文字维度
# ============================================================

def _extract_sentences(text: str) -> list:
    raw = re.split(r'(?<=[。！？.!?\n])', text)
    return [s.strip() for s in raw if len(s.strip()) > 1]


def _calc_sentence_features(text: str) -> dict:
    sents = _extract_sentences(text)
    if not sents:
        return {"avg_length": 0, "distribution": "未知", "question_ratio": 0, "imperative_ratio": 0}
    lengths = [len(s) for s in sents]
    avg = sum(lengths) / len(lengths)
    short = sum(1 for l in lengths if l < 15)
    medium = sum(1 for l in lengths if 15 <= l < 35)
    long_ = sum(1 for l in lengths if l >= 35)
    total = len(sents)
    if short / total > 0.5:
        dist = "短句密集（节奏快、有力）"
    elif long_ / total > 0.3:
        dist = "长句为主（细腻、有逻辑）"
    else:
        dist = "长短句混合"
    q_count = sum(1 for s in sents if s.endswith("？") or s.endswith("?"))
    imp_words = ["吧", "请", "不要", "别", "一定", "必须", "记住", "注意", "警惕"]
    imp_count = sum(1 for s in sents if any(w in s for w in imp_words))
    return {
        "avg_length": round(avg, 1),
        "distribution": dist,
        "short_ratio": round(short / total, 2),
        "medium_ratio": round(medium / total, 2),
        "long_ratio": round(long_ / total, 2),
        "question_ratio": round(q_count / total, 2),
        "imperative_ratio": round(imp_count / total, 2),
    }


def _analyze_vocab(text: str) -> dict:
    categories = {
        "口语化接地气": ["嘛", "呗", "啦", "哟", "哈", "的事儿", "啥", "咋", "整"],
        "书面化精炼": ["观点", "见解", "认知", "维度", "深度", "层面", "本质"],
        "专业术语密集": ["依据", "条款", "之", "其", "予以", "鉴于", "故此", "甲方", "乙方"],
        "网络热词高频": ["破防", "yyds", "绝了", "无语", "上头", "拿捏", "emmm", "离谱"],
        "古典意象": ["乾坤", "江湖", "山海", "如诗", "若梦", "似水", "悠然", "古风", "意境"],
    }
    scores = {}
    for cat, words in categories.items():
        scores[cat] = sum(text.count(w) for w in words)
    dominant = max(scores, key=scores.get) if any(scores.values()) else "中性"
    return {"style": dominant, "scores": scores}


def _detect_person(text: str) -> str:
    first_i = text.count("我") + text.count("我们")
    second = text.count("你") + text.count("您") + text.count("你们")
    third = text.count("他") + text.count("她") + text.count("它") + text.count("他们")
    total = first_i + second + third
    if total == 0:
        return "无明显人称偏好"
    if first_i / total > 0.4:
        return "第一人称主导"
    if second / total > 0.4:
        return "第二人称主导"
    return "混合人称"


# ============================================================
# 三、表达与修辞维度
# ============================================================

def _detect_rhetoric(text: str) -> list:
    rhetoric = []
    patterns = [
        ("比喻", ["像", "如同", "仿佛", "犹如", "好比", "似"]),
        ("对比", ["比", "更", "不如", "相反", "截然不同", "vs"]),
        ("排比", lambda t: len(re.findall(r'^[^。！？\n]{3,15}[，,]\s*[^。！？\n]{3,15}[，,]\s*[^。！？\n]{3,15}[，,。！？]', t, re.M)) > 0),
        ("设问", ["你知道吗", "为什么", "怎么", "如何", "有没有想过"]),
        ("反问", ["难道", "不是吗", "怎么会", "凭什么", "何必"]),
        ("引用", ["说", "指出", "提到", "表示", "认为"]),
        ("夸张", ["千万", "万万", "绝对", "从未", "一切", "所有"]),
    ]
    for name, keywords in patterns:
        if isinstance(keywords, list) and all(isinstance(k, str) for k in keywords):
            if any(kw in text for kw in keywords):
                rhetoric.append(name)
        elif callable(keywords):
            if keywords(text):
                rhetoric.append(name)
    return rhetoric


def _analyze_narrative(text: str) -> str:
    patterns = [
        ("痛点切入→解决方案", ["你是不是", "有没有", "困扰", "烦恼", "问题", "怎么办", "解决"]),
        ("场景描绘→价值共鸣", ["在", "时候", "当", "场景", "日常", "生活"]),
        ("故事线推进", ["那天", "曾经", "有一次", "我", "经历", "故事"]),
        ("观点+论证", ["我认为", "理由", "因为", "所以", "因此", "原因"]),
        ("直接陈述", ["就是", "教你", "分享", "推荐", "介绍"]),
    ]
    scores = {name: sum(text.count(w) for w in words) for name, words in patterns}
    return max(scores, key=scores.get) if any(scores.values()) else "混合叙事"


def _detect_info_focus(text: str) -> str:
    patterns = [
        ("功能", ["功能", "特点", "流程", "步骤", "方法", "操作"]),
        ("利益", ["省", "赚", "避免", "保护", "权益", "赔偿", "拿回"]),
        ("情感", ["感受", "心情", "愤怒", "委屈", "无奈", "焦虑", "绝望"]),
        ("身份", ["身份", "角色", "法官", "律师", "当事人", "原告", "被告"]),
        ("价值观", ["公平", "正义", "平等", "权利", "自由", "尊严"]),
        ("细节体验", ["细节", "真实", "亲历", "过程", "经过", "亲身"]),
    ]
    scores = {name: sum(text.count(w) for w in words) for name, words in patterns}
    return max(scores, key=scores.get) if any(scores.values()) else "综合"


# ============================================================
# 四、传播与适配维度
# ============================================================

PLATFORM_INDICATORS = {
    "小红书": ["姐妹们", "💄", "探店", "OOTD", "plog", "vlog", "好物", "收藏", "👇", "⬇️"],
    "抖音": ["双击", "关注我", "看下集", "下期", "口播", "上热门", "直播间"],
    "公众号": ["点击上方", "关注我们", "设为星标", "在看", "转发", "留言区", "在看"],
}


def _detect_platform(text: str) -> list:
    matched = []
    for plat, indicators in PLATFORM_INDICATORS.items():
        if any(ind in text for ind in indicators):
            matched.append(plat)
    return matched if matched else ["通用/跨平台"]


# ============================================================
# 互动表现分析
# ============================================================

ENGAGEMENT_TEMPLATES = {
    "高互动": "该内容引发了较多互动，建议分析标题和封面设计",
    "低互动": "互动较少，建议调整标题吸引力和内容开头方式",
    "评论活跃": "评论区讨论积极，说明选题触动用户表达欲",
    "收藏高": "收藏率高于平均水平，说明内容具有实用价值",
}


def _analyze_engagement(posts: list) -> dict:
    if not posts:
        return {
            "summary": "未提供互动数据",
            "avg_likes": 0, "avg_comments": 0, "avg_saves": 0, "avg_shares": 0,
            "best_performers": [],
            "suggestions": ["建议收集账号的公开互动数据后重新分析"],
        }
    likes = [p.get("likes", 0) for p in posts]
    comments = [p.get("comments", 0) for p in posts]
    saves = [p.get("saves", 0) for p in posts]
    shares = [p.get("shares", 0) for p in posts]
    avg_likes = round(sum(likes) / len(likes), 1) if likes else 0
    avg_comments = round(sum(comments) / len(comments), 1) if comments else 0
    avg_saves = round(sum(saves) / len(saves), 1) if saves else 0
    avg_shares = round(sum(shares) / len(shares), 1) if shares else 0
    scored = []
    for i, p in enumerate(posts):
        score = p.get("likes", 0) * 1 + p.get("comments", 0) * 2 + p.get("saves", 0) * 1.5
        scored.append((score, i, p.get("text", "")[:80]))
    scored.sort(reverse=True)
    best = scored[:3]
    suggestions = []
    engagement_rate = (avg_likes + avg_comments * 2 + avg_saves * 1.5) / max(len(posts), 1)
    if engagement_rate > 100:
        suggestions.append("整体互动表现优秀，内容策略值得借鉴")
    elif engagement_rate > 30:
        suggestions.append("互动表现中等，可参考其高互动内容的标题和开头")
    else:
        suggestions.append("互动偏低，建议关注其互动率最高的那类内容")
    return {
        "summary": f"平均点赞{avg_likes}/评论{avg_comments}/收藏{avg_saves}/转发{avg_shares}",
        "avg_likes": avg_likes,
        "avg_comments": avg_comments,
        "avg_saves": avg_saves,
        "avg_shares": avg_shares,
        "best_performers": [
            {"rank": i+1, "score": round(score, 1), "preview": text}
            for i, (score, _, text) in enumerate(best)
        ],
        "suggestions": suggestions,
        "raw_engagement_rate": round(engagement_rate, 1),
    }


# ============================================================
# 高频话题分析
# ============================================================

TOPIC_CATEGORIES = {
    "劳动纠纷": ["劳动仲裁", "辞退", "裁员", "N+1", "赔偿", "劳动合同", "加班", "工伤"],
    "婚姻家事": ["离婚", "抚养权", "财产分割", "彩礼", "婚前财产", "家暴", "继承"],
    "合同纠纷": ["合同", "违约", "定金", "退款", "霸王条款", "租房"],
    "交通事故": ["车祸", "赔偿", "酒驾", "交通肇事", "保险理赔"],
    "刑事犯罪": ["刑事", "拘留", "取保候审", "判刑", "缓刑", "故意伤害"],
    "知识产权": ["侵权", "商标", "专利", "著作权", "抄袭"],
    "房产纠纷": ["买房", "房产", "过户", "中介", "开发商", "逾期交房"],
    "消费维权": ["消费者", "维权", "欺诈", "退一赔三", "退款", "假货"],
    "公司商事": ["股权", "股东", "合伙", "加盟", "欠款", "公司"],
    "行政法律": ["行政复议", "行政诉讼", "行政处罚", "拆迁", "征收"],
}


def _extract_topics(texts: list) -> dict:
    combined = " ".join(texts)
    topic_scores = {}
    for cat, keywords in TOPIC_CATEGORIES.items():
        score = sum(combined.count(kw) for kw in keywords)
        if score > 0:
            topic_scores[cat] = score
    sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)
    angle_templates = {
        "劳动纠纷": ["避坑指南", "维权步骤", "赔偿计算"],
        "婚姻家事": ["法律科普", "案例解析", "自我保护"],
        "合同纠纷": ["常见陷阱", "维权方法", "条款解读"],
        "交通事故": ["处理流程", "赔偿标准", "注意事项"],
        "刑事犯罪": ["法律规定", "案例警示", "权利保护"],
    }
    topics_with_angles = []
    for name, count in sorted_topics:
        angles = angle_templates.get(name, ["法律科普", "案例分析"])
        topics_with_angles.append({
            "topic": name,
            "frequency": count,
            "suggested_angles": [f"{name}的{angle}" for angle in angles],
        })
    return {
        "total_topics": len(topics_with_angles),
        "topics": topics_with_angles,
        "dominant_area": sorted_topics[0][0] if sorted_topics else "未识别",
    }


# ============================================================
# 内容策略分析
# ============================================================

def _analyze_content_type(text: str) -> str:
    scores = {t: sum(text.count(w) for w in ws) for t, ws in CONTENT_TYPE_KEYWORDS.items()}
    return max(scores, key=scores.get) if any(scores.values()) else "综合"


def _analyze_content_strategy(posts: list) -> dict:
    if not posts:
        return {"types_distribution": {}, "main_type": "未知", "posting_frequency": "未知", "length_preference": {"avg_chars": 0, "preference": "未知"}}
    type_counts = {}
    for p in posts:
        text = p.get("text", "")
        ct = _analyze_content_type(text)
        type_counts[ct] = type_counts.get(ct, 0) + 1
    total = len(posts)
    types_dist = {k: f"{round(v/total*100)}%" for k, v in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)}
    lengths = [len(p.get("text", "")) for p in posts]
    avg_len = round(sum(lengths) / len(lengths)) if lengths else 0
    if avg_len < 200:
        pref = "短内容（小红书式图文）"
    elif avg_len < 800:
        pref = "中篇内容（短视频口播）"
    else:
        pref = "长内容（公众号深度文）"
    return {
        "types_distribution": types_dist,
        "main_type": max(type_counts, key=type_counts.get) if type_counts else "未知",
        "posting_frequency": "需结合时间数据判断",
        "length_preference": {"avg_chars": avg_len, "preference": pref},
    }


# ============================================================
# 对外接口
# ============================================================

def generate_analysis_report(account_name: str, platform: str, raw_data: dict) -> str:
    """旧接口兼容 — 内部调用新版 analyze_account"""
    posts = raw_data.get("posts", [])
    result = analyze_account(account_name, platform, posts)
    return result["report"]


def extract_style_tags(report_text: str) -> list:
    """旧接口兼容 — 从报告中提取风格标签"""
    # 实际标签已由 analyze_account 生成
    tags = []
    style_keywords = {
        "专业": ["专业", "权威", "严谨"],
        "幽默": ["幽默", "搞笑", "段子"],
        "亲切": ["亲切", "朋友", "接地气"],
        "犀利": ["犀利", "尖锐", "敢说"],
        "温和": ["温和", "耐心", "温柔"],
    }
    for tag, keywords in style_keywords.items():
        if any(kw in report_text for kw in keywords):
            tags.append(tag)
    return tags


def analyze_account(account_name: str, platform: str, posts: list = None) -> dict:
    """
    完整的竞品账号分析 V2
    posts: [{"text": "...", "likes": 0, "comments": 0, "saves": 0, "shares": 0}, ...]
    """
    posts = posts or []
    texts = [p.get("text", "") for p in posts if p.get("text")]
    combined = "\n".join(texts) if texts else ""

    # ---- 维度1: 定位与基调 ----
    if combined:
        tone_scores = {t: sum(1 for w in words if w in combined) for t, words in TONE_KEYWORDS.items()}
        dominant_tone = max(tone_scores, key=tone_scores.get) if any(tone_scores.values()) else "中性"
        stance_scores = {t: sum(1 for w in words if w in combined) for t, words in STANCE_KEYWORDS.items()}
        dominant_stance = max(stance_scores, key=stance_scores.get) if any(stance_scores.values()) else "中性叙述"
        audience_scores = {t: sum(1 for w in words if w in combined) for t, words in AUDIENCE_KEYWORDS.items()}
        dominant_audience = max(audience_scores, key=audience_scores.get) if any(audience_scores.values()) else "泛人群"
    else:
        dominant_tone = dominant_stance = dominant_audience = "需提供文案样本"

    positioning = {"目标受众": dominant_audience, "情感基调": dominant_tone, "语气立场": dominant_stance}

    # ---- 维度2: 语言与文字 ----
    if combined:
        sent_feat = _calc_sentence_features(combined)
        vocab = _analyze_vocab(combined)
        person = _detect_person(combined)
        lines_count = len([l for l in combined.split('\n') if l.strip()])
        pace = "短段落（节奏快）" if lines_count <= 3 else ("分段清晰" if lines_count <= 6 else "长文多段")
    else:
        sent_feat = {"avg_length": 0, "distribution": "需提供样本", "question_ratio": 0, "imperative_ratio": 0}
        vocab = {"style": "需提供样本", "scores": {}}
        person = "需提供样本"
        pace = "需提供样本"

    language = {
        "句式特征": f"平均{sent_feat['avg_length']}字/句，{sent_feat['distribution']}",
        "用词风格": vocab['style'],
        "篇幅节奏": pace,
        "人称使用": person,
    }

    # ---- 维度3: 表达与修辞 ----
    if combined:
        rhetoric = _detect_rhetoric(combined)
        narrative = _analyze_narrative(combined)
        focus = _detect_info_focus(combined)
    else:
        rhetoric = ["需提供样本"]
        narrative = "需提供样本"
        focus = "需提供样本"

    expression = {"修辞手法": rhetoric, "叙事逻辑": narrative, "信息侧重": focus}

    # ---- 维度4: 传播与适配 ----
    matched_platforms = _detect_platform(combined) if combined else ["需提供样本"]
    style_tag = f"{dominant_tone} · {vocab['style'][:8]} · {narrative[:6]}"
    distribution = {"适配平台": matched_platforms, "风格标签": style_tag}

    # ---- 内容策略 ----
    content_strat = _analyze_content_strategy(posts)
    # ---- 互动表现 ----
    engagement = _analyze_engagement(posts)
    # ---- 高频话题 ----
    topics = _extract_topics(texts)

    return {
        "account_name": account_name,
        "platform": platform,
        "analyzed_at": datetime.now().isoformat(),
        "sample_count": len(posts),
        "四层风格分析": {
            "定位与基调": positioning,
            "语言与文字": language,
            "表达与修辞": expression,
            "传播与适配": distribution,
        },
        "内容策略": content_strat,
        "互动表现": engagement,
        "高频话题": topics,
        "report": _format_report(account_name, platform, positioning, language, expression, distribution, content_strat, engagement, topics),
        "suggested_tags": [t.strip() for t in style_tag.split("·")],
    }


def _format_report(name, platform, positioning, language, expression, distribution, content_strat, engagement, topics) -> str:
    lines = []
    lines.append(f"╔══ 竞品账号分析报告：{name}")
    lines.append(f"║ 📌 平台：{platform}")
    lines.append(f"║ 📊 样本：{engagement.get('avg_likes','N/A')} 赞/篇 平均\n")
    lines.append("【📌 定位与基调】")
    for k, v in positioning.items():
        lines.append(f"  ▸ {k}：{v}")
    lines.append("")
    lines.append("【✏️ 语言与文字】")
    for k, v in language.items():
        lines.append(f"  ▸ {k}：{v}")
    lines.append("")
    lines.append("【🎨 表达与修辞】")
    for k, v in expression.items():
        vs = ", ".join(v) if isinstance(v, list) else v
        lines.append(f"  ▸ {k}：{vs}")
    lines.append("")
    lines.append("【📱 传播与适配】")
    for k, v in distribution.items():
        vs = ", ".join(v) if isinstance(v, list) else v
        lines.append(f"  ▸ {k}：{vs}")
    lines.append("")
    lines.append("【📋 内容策略】")
    lines.append(f"  ▸ 主要类型：{content_strat.get('main_type', 'N/A')}")
    lines.append(f"  ▸ 篇幅偏好：{content_strat.get('length_preference', {}).get('preference', 'N/A')}")
    lines.append(f"  ▸ 发布频率：{content_strat.get('posting_frequency', 'N/A')}")
    lines.append("")
    lines.append("【💬 互动表现】")
    lines.append(f"  ▸ {engagement.get('summary', 'N/A')}")
    for s in engagement.get("suggestions", []):
        lines.append(f"  ▸ 💡 {s}")
    lines.append("")
    lines.append("【🔥 高频话题】")
    for t in topics.get("topics", []):
        angles = ", ".join(t.get("suggested_angles", [])[:2])
        lines.append(f"  ▸ {t['topic']}（频次：{t['frequency']}）→ {angles}")
    lines.append("")
    lines.append(f'🏷️ 详见上方【📱 传播与适配】风格标签')
    return "\n".join(lines)
