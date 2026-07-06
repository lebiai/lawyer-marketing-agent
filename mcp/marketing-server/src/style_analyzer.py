"""
风格分析器 V2 — 仅做文本统计，不做关键词匹配分析

数据流：
  MCP: 采集文本 → 统计客观指标（句长/词汇密度/人称/修辞频次）
  Agent: 读取统计结果 + 原文 → 分析风格定位/语气/受众
"""

import re
from snownlp import SnowNLP


def _split_sentences(text: str) -> list:
    """分句"""
    raw = re.split(r'(?<=[。！？.!?\n])', text)
    return [s.strip() for s in raw if len(s.strip()) > 1]


def analyze_style(text: str, account_name: str = None) -> dict:
    """
    提取文案的客观统计指标。
    不进行关键词匹配式的风格分析，由 Agent 完成语义分析。
    
    Returns:
        {
            "account": str,
            "text_length": int,
            "stats": {
                "sentence_stats": {...},       # 句长分布
                "vocab_density": {...},         # 词汇密度
                "person_usage": str,            # 人称使用
                "sentiment": float,             # 情感分（SnowNLP）
                "rhetoric_count": {...},        # 修辞手法出现次数
                "narrative_type": str,          # 叙事类型
                "info_focus": str,              # 信息侧重
                "platform_hints": list,         # 平台特征
                "unique_markers": dict,         # 独特标记
            },
            "keywords": list,                   # SnowNLP 关键词
            "raw_text_sample": str,             # 原文片段供 Agent 分析
        }
    """
    if not text or len(text.strip()) < 5:
        return {"error": "文案过短，无法分析"}

    text = text.strip()
    sents = _split_sentences(text)
    s = SnowNLP(text) if len(text) > 10 else None
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # ---- 句长统计 ----
    if sents:
        lengths = [len(s) for s in sents]
        avg_len = round(sum(lengths) / len(lengths), 1)
        short = round(sum(1 for l in lengths if l < 15) / len(lengths), 2)
        medium = round(sum(1 for l in lengths if 15 <= l < 35) / len(lengths), 2)
        long = round(sum(1 for l in lengths if l >= 35) / len(lengths), 2)
        q_ratio = round(sum(1 for s2 in sents if s2.endswith("？") or s2.endswith("?")) / len(lengths), 2)
        imp_words = ["吧", "请", "不要", "别", "一定", "必须", "记住", "注意", "警惕"]
        imp_ratio = round(sum(1 for s2 in sents if any(w in s2 for w in imp_words)) / len(lengths), 2)
    else:
        avg_len, short, medium, long, q_ratio, imp_ratio = 0, 0, 0, 0, 0, 0

    # ---- 词汇密度统计（客观计数） ----
    vocab_categories = {
        "口语化": ["嘛", "呗", "啦", "哟", "哈", "啥", "咋", "整"],
        "专业术语": ["依据", "条款", "之", "其", "予以", "鉴于", "故此", "民法典", "合同法"],
        "网络热词": ["破防", "yyds", "绝了", "无语", "上头", "拿捏", "emmm"],
        "古典意象": ["乾坤", "江湖", "山海", "若", "似"],
    }
    vocab_density = {}
    for cat, words in vocab_categories.items():
        count = sum(text.count(w) for w in words)
        density = round(count / max(len(text), 1) * 1000, 2)
        vocab_density[cat] = {"count": count, "density_per_1k": density}

    # ---- 人称统计 ----
    first_p = sum(text.count(p) for p in ["我", "我们", "我的"])
    second_p = sum(text.count(p) for p in ["你", "你们", "你的"])
    third_p = sum(text.count(p) for p in ["他", "她", "它", "他们", "她们"])
    persons = {"第一人称": first_p, "第二人称": second_p, "第三人称": third_p}
    dominant_person = max(persons, key=persons.get) if any(persons.values()) else "无明显偏向"

    # ---- 修辞频次统计 ----
    rhetoric_patterns = {
        "比喻": ["像", "仿佛", "如同", "宛如", "好比"],
        "设问": ["？"],
        "对比": ["但", "然而", "却", "而", "比起", "相反"],
        "排比": ["，", "\n"],
    }
    rhetoric_count = {}
    for name, patterns in rhetoric_patterns.items():
        if name == "设问":
            rhetoric_count[name] = sum(1 for s2 in sents if s2.endswith("？"))
        elif name == "排比":
            # 粗略统计相似句式重复
            rhetoric_count[name] = 0
        else:
            rhetoric_count[name] = sum(text.count(w) for w in patterns)

    # ---- SnowNLP ----
    sentiment = round(s.sentiments, 3) if s else 0.5
    keywords = s.keywords(8) if s else []

    # ---- 篇幅节奏 ----
    if len(lines) <= 1:
        pace = "一句话"
    elif len(lines) <= 3:
        pace = "短段落"
    elif len(lines) <= 6:
        pace = "分段清晰"
    else:
        pace = "长文多段"

    return {
        "account": account_name,
        "text_length": len(text),
        "paragraph_count": len(lines),
        "stats": {
            "sentence_stats": {
                "avg_length": avg_len,
                "short_ratio": short,
                "medium_ratio": medium,
                "long_ratio": long,
                "question_ratio": q_ratio,
                "imperative_ratio": imp_ratio,
                "distribution": "短句密集" if short > 0.5 else ("长句为主" if long > 0.3 else "长短句混合"),
            },
            "vocab_density": vocab_density,
            "person_usage": {"dominant": dominant_person, "counts": persons},
            "pace": pace,
            "sentiment": sentiment,
            "sentiment_label": "正面" if sentiment > 0.6 else ("负面" if sentiment < 0.4 else "中性"),
            "rhetoric_count": rhetoric_count,
        },
        "keywords": keywords,
        "raw_text_sample": text[:500],
    }


def compare_styles(samples: list) -> dict:
    """
    批量对比多个文案的统计指标。
    samples: [{"name": "账号A", "text": "..."}, ...]
    对比分析由 Agent 完成，此处仅返回各样本的统计数据。
    """
    results = []
    for s2 in samples:
        analysis = analyze_style(s2["text"], s2.get("name"))
        if "error" not in analysis:
            results.append({
                "name": s2.get("name", "未命名"),
                "stats": analysis["stats"],
                "keywords": analysis["keywords"],
            })

    return {
        "count": len(results),
        "comparison": results,
        "note": "共统计 {} 个样本的客观指标，深度对比分析由 Agent 完成".format(len(results)),
    }
