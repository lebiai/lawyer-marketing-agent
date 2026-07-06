"""
风格分析器 — 基于四层维度的自动化文案风格特征提取

参考框架：
  1. 定位与基调维度（气质底色）
  2. 语言与文字维度（风格载体）
  3. 表达与修辞维度（感染力）
  4. 传播与适配维度（场景感）
"""

import re
from snownlp import SnowNLP

# ============================================================
# 1. 定位与基调维度
# ============================================================

# 情感基调关键词库
TONE_KEYWORDS = {
    "理性客观": ["根据", "数据显示", "研究表明", "从法律角度", "事实上", "本质上", "客观来说"],
    "温暖治愈": ["温暖", "治愈", "陪伴", "别怕", "没关系", "会好的", "一起", "抱抱"],
    "犀利直白": ["说白了", "实话告诉你", "醒醒", "别再", "就是", "直接说", "废话不多说"],
    "幽默俏皮": ["哈哈", "嘻嘻", "😂", "🤣", "笑死", "搞笑", "离谱", "笑不活了"],
    "高级克制": ["或许", "可能", "某种程度上", "不妨", "值得思考", "另一种可能"],
    "热血有力": ["必须", "一定", "绝不", "站起来", "捍卫", "战斗", "改变"],
    "文艺感性": ["时光", "岁月", "温柔", "风", "月光", "山海", "人间", "值得"],
}

# 语气立场关键词库
STANCE_KEYWORDS = {
    "平等对话": ["我们", "一起", "来", "聊聊", "讨论", "你觉得", "你怎么看"],
    "权威指导": ["记住", "一定要", "千万", "注意", "法律规定", "根据", "建议你"],
    "朋友分享": ["我", "我的", "昨天", "最近", "发现", "分享", "安利", "推荐"],
    "官方正式": ["公告", "通知", "声明", "严格", "规范", "予以", "特此"],
    "自嘲玩梗": ["我", "本", "也是醉了", "瑟瑟发抖", "卑微", "打工人", "摸鱼"],
}

# 目标受众关键词
AUDIENCE_KEYWORDS = {
    "普通大众": ["每个人", "大家", "所有人", "国人", "老百姓"],
    "职场人": ["职场", "同事", "老板", "职场人", "打工人", "升职"],
    "年轻人": ["年轻人", "90后", "00后", "大学生", "刚毕业"],
    "专业人士": ["从业者", "专业人士", "同行", "业内"],
    "特定场景": ["当事人", "客户", "受害者", "家属", "房东", "租客"],
}

# 核心目的关键词
PURPOSE_KEYWORDS = {
    "传递信息": ["科普", "告诉你", "了解", "说明", "介绍", "什么是"],
    "建立信任": ["我", "多年", "经验", "专业", "案例", "当事人"],
    "引发共鸣": ["你是不是", "有没有", "同样", "经历过", "理解"],
    "制造话题": ["热议", "争议", "你怎么看", "讨论", "炸了"],
    "种草转化": ["推荐", "值得", "必买", "收藏", "关注我", "私信"],
}

# ============================================================
# 2. 语言与文字维度
# ============================================================

def _split_sentences(text: str) -> list:
    """分句"""
    raw = re.split(r'(?<=[。！？.!?\n])', text)
    return [s.strip() for s in raw if len(s.strip()) > 1]

def _analyze_sentence_features(text: str) -> dict:
    """句式特征分析"""
    sents = _split_sentences(text)
    if not sents:
        return {"avg_length": 0, "distribution": "未知", "question_ratio": 0, "imperative_ratio": 0}
    
    lengths = [len(s) for s in sents]
    avg = sum(lengths) / len(lengths)
    
    # 长短句分布
    short = sum(1 for l in lengths if l < 15)
    medium = sum(1 for l in lengths if 15 <= l < 35)
    long = sum(1 for l in lengths if l >= 35)
    total = len(sents)
    
    if short / total > 0.5:
        dist = "短句密集（节奏快、有力）"
    elif long / total > 0.3:
        dist = "长句为主（细腻、有逻辑）"
    else:
        dist = "长短句混合"
    
    # 疑问句比例
    q_count = sum(1 for s in sents if s.endswith("？") or s.endswith("?"))
    # 祈使句比例
    imp_words = ["吧", "请", "不要", "别", "一定", "必须", "记住", "注意", "警惕"]
    imp_count = sum(1 for s in sents if any(w in s for w in imp_words))
    
    return {
        "avg_length": round(avg, 1),
        "distribution": dist,
        "short_ratio": round(short / total, 2),
        "medium_ratio": round(medium / total, 2),
        "long_ratio": round(long / total, 2),
        "question_ratio": round(q_count / total, 2),
        "imperative_ratio": round(imp_count / total, 2),
    }

def _analyze_vocabulary(text: str) -> dict:
    """用词风格分析"""
    sents = _split_sentences(text)
    total_words = len(text)
    
    # 各层级词汇密度
    categories = {
        "口语化接地气": ["嘛", "呗", "啦", "哟", "哈", "的事儿", "啥", "咋", "整"],
        "专业术语密集": ["依据", "条款", "之", "其", "予以", "鉴于", "故此"],
        "网络热词": ["破防", "yyds", "绝了", "无语", "上头", "拿捏", "emmm"],
        "古典意象": ["乾坤", "江湖", "山海", "如", "若", "似", "然"],
    }
    
    cat_scores = {}
    for cat, words in categories.items():
        count = sum(1 for w in words if w in text)
        cat_scores[cat] = count
    
    # 判断用词层级
    dominant = max(cat_scores, key=cat_scores.get) if any(cat_scores.values()) else "中性自然"
    
    return {
        "style": dominant if cat_scores.get(dominant, 0) > 0 else "中性自然",
        "scores": cat_scores,
        "total_chars": total_words,
    }

def _analyze_person(text: str) -> str:
    """人称使用分析"""
    first_person = len(re.findall(r'(?<![^\s，。])我(?![^\s，。])', text))
    first_plural = text.count("我们")
    second_person = text.count("你") + text.count("您")
    third_person = text.count("它") + text.count("他") + text.count("她") + text.count("品牌") + text.count("该")
    
    if first_plural > first_person and first_plural > second_person:
        return "第一人称复数（我们）"
    elif first_person > second_person:
        return "第一人称（我）"
    elif second_person > first_person:
        return "第二人称（你/您）"
    elif third_person > first_person:
        return "第三人称"
    return "混合使用"

# ============================================================
# 3. 表达与修辞维度
# ============================================================

# 修辞手法关键词
RHETORIC_KEYWORDS = {
    "比喻": ["像", "如同", "仿佛", "好比", "宛如", "似", "犹如"],
    "对比": ["比", "相比", "相反", "却", "而", "但是", "不过", "另一方面"],
    "排比": None,  # 需要结构检测
    "设问": ["你知道吗", "为什么", "是什么", "怎么办", "如何"],
    "引用": ["说", "说过", "有句", "古话", "俗话说", "正如"],
    "数字具象化": None,  # 数字检测
    "反问": ["难道", "不是吗", "怎么会", "凭什么"],
    "夸张": ["惊了", "所有人", "没有一个", "从来", "永远"],
}

def _detect_rhetoric(text: str) -> list:
    """检测修辞手法"""
    detected = []
    
    # 关键词匹配
    for technique, keywords in RHETORIC_KEYWORDS.items():
        if keywords is None:
            continue
        if any(kw in text for kw in keywords):
            detected.append(technique)
    
    # 数字检测
    numbers = re.findall(r'\d+', text)
    if len(numbers) >= 2:
        detected.append("数字具象化")
    
    # 排比检测（连续相同结构）
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) >= 3:
        # 检查连续行是否以相同词开头
        starts = [l[:2] for l in lines]
        for i in range(len(starts) - 2):
            if starts[i] == starts[i+1] == starts[i+2]:
                detected.append("排比")
                break
    
    return list(set(detected))

def _analyze_narrative(text: str) -> str:
    """检测叙事逻辑"""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    
    # 检查特征
    has_story = any(w in text for w in ["我", "客户", "朋友", "同事", "昨天", "去年"])
    has_problem = any(w in text for w in ["问题", "困难", "麻烦", "痛点", "陷阱"])
    has_solution = any(w in text for w in ["方法", "建议", "可以", "应该", "怎么办"])
    has_opinion = any(w in text for w in ["认为", "觉得", "观点", "看法"])
    has_hook = any(w in text[:50] for w in ["警惕", "千万别", "紧急", "重磅", "注意"])
    
    if has_hook and has_problem and has_solution:
        return "痛点切入 → 解决方案"
    if has_story:
        return "故事线推进"
    if has_opinion:
        return "观点 + 论证"
    if len(lines) <= 3:
        return "直接陈述"
    return "场景描绘 → 价值共鸣"

def _analyze_info_focus(text: str) -> str:
    """分析信息侧重"""
    if any(w in text for w in ["功能", "用法", "步骤", "流程", "怎么"]):
        return "功能/方法"
    if any(w in text for w in ["利益", "好处", "省", "赚", "赔", "亏"]):
        return "利益/结果"
    if any(w in text for w in ["感动", "温暖", "心酸", "心疼", "共鸣"]):
        return "情感共鸣"
    if any(w in text for w in ["身份", "资格", "资深", "十年", "从业"]):
        return "身份/权威"
    return "信息传递"

# ============================================================
# 4. 传播与适配维度
# ============================================================

def _detect_platform(text: str) -> list:
    """检测适配平台"""
    platforms = []
    length = len(text)
    
    if length < 50:
        platforms.append("朋友圈/标题")
    if length < 200:
        platforms.append("短视频口播")
    if 100 < length < 500:
        platforms.append("小红书图文")
    if length > 300:
        platforms.append("公众号长文")
    if any(w in text for w in ["点击", "购买", "链接", "下方"]):
        platforms.append("电商/转化")
    
    return platforms if platforms else ["通用"]

def _detect_unique_markers(text: str) -> dict:
    """检测独特标识（固定句式、口头禅等）"""
    markers = {}
    
    # 固定开头
    openers = ["我是", "你好", "大家好", "今天", "最近", "朋友们"]
    for o in openers:
        if text.startswith(o):
            markers["固定开头"] = o
            break
    
    # 固定结尾
    if any(text.strip().endswith(e) for e in ["关注我", "收藏", "转发", "点赞"]):
        markers["固定结尾"] = text.strip()[-10:] if len(text) > 10 else text.strip()
    
    # 口头禅
    filler_words = ["其实", "说实话", "讲真", "懂的都懂", "你懂的", "怎么说呢"]
    found_fillers = [w for w in filler_words if w in text]
    if found_fillers:
        markers["口头禅"] = found_fillers
    
    return markers

# ============================================================
# 主入口
# ============================================================

def analyze_style(text: str, account_name: str = None) -> dict:
    """
    完整风格分析入口
    返回四层维度的结构化分析结果
    """
    if not text or len(text.strip()) < 5:
        return {"error": "文案过短，无法分析"}
    
    text = text.strip()
    s = SnowNLP(text) if len(text) > 10 else None
    
    # ---- 1. 定位与基调 ----
    tone_scores = {t: sum(1 for w in words if w in text) for t, words in TONE_KEYWORDS.items()}
    dominant_tone = max(tone_scores, key=tone_scores.get) if any(tone_scores.values()) else "中性"
    
    stance_scores = {t: sum(1 for w in words if w in text) for t, words in STANCE_KEYWORDS.items()}
    dominant_stance = max(stance_scores, key=stance_scores.get) if any(stance_scores.values()) else "中性叙述"
    
    audience_scores = {t: sum(1 for w in words if w in text) for t, words in AUDIENCE_KEYWORDS.items()}
    dominant_audience = max(audience_scores, key=audience_scores.get) if any(audience_scores.values()) else "泛人群"
    
    purpose_scores = {t: sum(1 for w in words if w in text) for t, words in PURPOSE_KEYWORDS.items()}
    dominant_purpose = max(purpose_scores, key=purpose_scores.get) if any(purpose_scores.values()) else "通用"
    
    sentiment = s.sentiments if s else 0.5
    
    dimension_1 = {
        "目标受众": dominant_audience,
        "核心目的": dominant_purpose,
        "情感基调": dominant_tone,
        "语气立场": dominant_stance,
        "情感倾向": "正面" if sentiment > 0.6 else ("负面" if sentiment < 0.4 else "中性"),
        "情感分": round(sentiment, 3),
        "_细节": {
            "情感基调得分": tone_scores,
            "语气立场得分": stance_scores,
            "受众匹配": audience_scores,
            "目的匹配": purpose_scores,
        }
    }
    
    # ---- 2. 语言与文字 ----
    sent_features = _analyze_sentence_features(text)
    vocab = _analyze_vocabulary(text)
    person = _analyze_person(text)
    
    # 篇幅节奏
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if len(lines) <= 1:
        pace = "一句话文案"
    elif len(lines) <= 3:
        pace = "短段落（节奏快）"
    elif len(lines) <= 6:
        pace = "分段清晰"
    else:
        pace = "长文多段"
    
    dimension_2 = {
        "句式特征": {
            "平均句长": f"{sent_features['avg_length']}字",
            "分布": sent_features['distribution'],
            "疑问句比例": sent_features['question_ratio'],
            "祈使句比例": sent_features['imperative_ratio'],
        },
        "用词风格": vocab['style'],
        "篇幅节奏": pace,
        "人称使用": person,
        "_细节": {
            "句长分布": f"短句{sent_features['short_ratio']:.0%}, 中句{sent_features['medium_ratio']:.0%}, 长句{sent_features['long_ratio']:.0%}",
            "用词得分": vocab['scores'],
        }
    }
    
    # ---- 3. 表达与修辞 ----
    rhetoric = _detect_rhetoric(text)
    narrative = _analyze_narrative(text)
    focus = _analyze_info_focus(text)
    markers = _detect_unique_markers(text)
    
    dimension_3 = {
        "修辞手法": rhetoric if rhetoric else ["无明显修辞"],
        "叙事逻辑": narrative,
        "信息侧重": focus,
        "独特符号": markers if markers else "无明显独有标记",
    }
    
    # ---- 4. 传播与适配 ----
    platforms = _detect_platform(text)
    
    # 综合风格标签
    style_tags = f"{dominant_tone} + {narrative[:6]} + {person[:4]}"
    
    dimension_4 = {
        "适配平台": platforms,
        "风格标签": style_tags,
    }
    
    # ---- 汇总 ----
    return {
        "account": account_name,
        "text_length": len(text),
        "summary": f"{dominant_tone} · {narrative} · {vocab['style'][:6]}",
        "dimensions": {
            "定位与基调": dimension_1,
            "语言与文字": dimension_2,
            "表达与修辞": dimension_3,
            "传播与适配": dimension_4,
        },
        "structured_features": {
            "tone": dominant_tone,
            "stance": dominant_stance,
            "audience": dominant_audience,
            "sentence_dist": sent_features['distribution'],
            "vocab_style": vocab['style'],
            "person": person,
            "narrative": narrative,
        },
        "keywords": s.keywords(8) if s else [],
    }


def compare_styles(samples: list) -> dict:
    """
    批量对比多个文案或账号的风格
    samples: [{"name": "账号A", "text": "..."}, ...]
    """
    results = []
    for s in samples:
        analysis = analyze_style(s["text"], s.get("name"))
        if "error" not in analysis:
            results.append({
                "name": s.get("name", "未命名"),
                "summary": analysis["summary"],
                "features": analysis["structured_features"],
            })
    
    return {
        "count": len(results),
        "comparison": results,
        "insight": "共分析 {} 个样本".format(len(results)),
    }
