"""
多平台文案适配器 V2 — 智能结构转换

基于 copywriter.py 的 PLATFORM_RULES 方法论，
实现跨平台的内容结构重组、语气转换、格式适配。
"""

from copywriter import PLATFORM_RULES, generate_outline

def adapt_content(content: str, source_platform: str, target_platform: str) -> dict:
    """
    智能跨平台适配
    返回包含重构后的标题、正文、转换说明
    """
    target = target_platform.lower()
    if target not in PLATFORM_RULES:
        return {"error": f"不支持的目标平台：{target}"}

    rules = PLATFORM_RULES[target]
    lines = [l.strip() for l in content.split("\n") if l.strip()]
    original_title = lines[0] if lines else ""
    body_lines = lines[1:] if len(lines) > 1 else lines

    # 根据目标平台调用对应的转换函数
    if target == "xiaohongshu":
        return _to_xiaohongshu(original_title, body_lines, rules, source_platform)
    elif target == "douyin":
        return _to_douyin(original_title, body_lines, rules, source_platform)
    elif target == "wechat":
        return _to_wechat(original_title, body_lines, rules, source_platform)

    return {"error": f"不支持的平台：{target}"}


# ============================================================
# 转小红书
# ============================================================

def _to_xiaohongshu(title: str, body_lines: list, rules: dict, source: str) -> dict:
    max_title = rules["title"]["length"][1]  # 22字
    min_title = rules["title"]["length"][0]  # 15字

    # 标题
    adapted_title = _adapt_title(title, max_title, min_title)
    
    # 正文重构：按 开头(痛点/好处) → 中间(分点干货) → 结尾(互动) 结构
    restructured = _restructure_to_xiaohongshu(body_lines)
    
    # 段落格式化：每段≤3行，emoji分隔
    formatted_body = []
    for para in restructured["paragraphs"]:
        short_paras = _split_paragraph(para, max_lines=3)
        formatted_body.extend(short_paras)

    # 话题标签
    tags = _suggest_tags(restructured["keywords"], "xiaohongshu")

    return {
        "title": adapted_title,
        "title_fit": f"{len(adapted_title)}字（建议{min_title}-{max_title}字）",
        "body": "\n\n".join(formatted_body),
        "tags": tags,
        "conversion_notes": [
            f"来源：{source} → 小红书",
            "✅ 结构重构：原文 → 小红书（痛点开头 → 分点干货 → 互动结尾）",
            f"✅ 标题：从 {len(title)} 字压缩至 {len(adapted_title)} 字",
            "✅ 正文：已拆分为短段落（每段≤3行）",
        ],
        "tips": [
            "每段前加 emoji 分隔（✅ 📌 🔥 💡）",
            "结尾加互动引导：'姐妹们觉得呢？评论区聊聊～'",
            "配图 3-6 张，封面高清吸睛",
            "标签策略：1-2个大词 + 3-5个精准词 + 1-2个话题词",
        ],
    }


def _restructure_to_xiaohongshu(body_lines: list) -> dict:
    """将原文按小红书结构重组"""
    all_text = "\n".join(body_lines)
    lines = [l for l in body_lines if l]
    
    n = len(lines)
    if n >= 4:
        # 原文较长 → 自然按三段拆
        split1 = max(1, n // 3)
        split2 = max(2, n * 2 // 3)
        hook = _extract_hook(lines[:split1])
        main = lines[split1:split2]
        ending = _build_xiaohongshu_ending(lines[split2:])
    elif n >= 2:
        hook = _extract_hook(lines[:1])
        main = lines[1:]
        ending = "姐妹们觉得有用的话，点赞收藏起来吧～ 💕"
    else:
        hook = _extract_hook(lines)
        main = []
        ending = "大家还有什么问题，评论区见～ 💬"

    # 提取关键词
    import re
    keywords = re.findall(r'[\u4e00-\u9fff]{2,}', all_text)
    # 取出现次数最多的前5个
    from collections import Counter
    keyword_scores = Counter(keywords)
    top_keywords = [k for k, v in keyword_scores.most_common(10) if len(k) >= 2][:5]

    return {
        "paragraphs": [hook] + main + [ending],
        "keywords": top_keywords,
    }


# ============================================================
# 转抖音口播
# ============================================================

def _to_douyin(title: str, body_lines: list, rules: dict, source: str) -> dict:
    max_title = rules["title"]["length"][1]
    all_text = "\n".join(body_lines)

    # 标题 = 3秒钩子
    hook_title = _extract_hook_text(title or all_text, max_len=max_title)

    # 按 钩子→展开→亮点→引导 四段重组
    segments = _restructure_to_douyin(all_text)

    return {
        "title": hook_title,
        "title_fit": f"{len(hook_title)}字（建议≤{max_title}字）",
        "script": "\n\n".join([f"【{s['label']}】\n{s['text']}" for s in segments]),
        "timing": [s["timing"] for s in segments],
        "total_duration": sum(s["duration"] for s in segments),
        "conversion_notes": [
            f"来源：{source} → 抖音口播",
            "✅ 结构重构：黄金60秒（钩子→展开→亮点→引导）",
            "✅ 标题变为开场钩子",
            "✅ 每段≤15字，口语化处理",
        ],
        "tips": [
            "语速适中，关键词重复2次",
            "关键句加字幕放大",
            "新手建议先拍15-30秒版本",
        ],
    }


def _restructure_to_douyin(text: str) -> list:
    """按黄金60秒结构重组"""
    sents = [s.strip() for s in text.replace("\n", "。").split("。") if len(s.strip()) > 3]
    n = len(sents)

    if n >= 4:
        hook = _shorten_sentence(sents[0], max_chars=15)
        expand = [_shorten_sentence(s, 15) for s in sents[1:n//2]]
        highlight = [_shorten_sentence(s, 15) for s in sents[n//2:-1]]
        call_action = _build_douyin_ending(sents[-1])
    elif n >= 2:
        hook = _shorten_sentence(sents[0], 15)
        expand = [_shorten_sentence(s, 15) for s in sents[1:-1]]
        highlight = []
        call_action = _build_douyin_ending(sents[-1])
    else:
        hook = _shorten_sentence(sents[0], 15)
        expand = []
        highlight = []
        call_action = "关注我，学法律不吃亏 🔔"

    return [
        {"label": "🔥 0-3秒 钩子", "text": hook, "timing": "0-3秒", "duration": 3},
        {"label": "💡 3-30秒 展开", "text": "\n".join(expand) if expand else "继续往下说…", "timing": "3-30秒", "duration": 15},
        {"label": "⚡ 30-50秒 亮点", "text": "\n".join(highlight) if highlight else "给大家总结一下重点…", "timing": "30-50秒", "duration": 10},
        {"label": "👋 50-60秒 引导", "text": call_action, "timing": "50-60秒", "duration": 5},
    ]


# ============================================================
# 转公众号
# ============================================================

def _to_wechat(title: str, body_lines: list, rules: dict, source: str) -> dict:
    max_title = rules["title"]["length"][1]
    min_title = rules["title"]["length"][0]
    all_text = "\n".join(body_lines)

    adapted_title = _adapt_wechat_title(title, all_text, max_title, min_title)

    # 按导读→分层论述→金句→互动 结构重组
    restructured = _restructure_to_wechat(all_text)

    return {
        "title": adapted_title,
        "title_fit": f"{len(adapted_title)}字（建议{min_title}-{max_title}字）",
        "body": restructured["body"],
        "word_count": len(restructured["body"]),
        "conversion_notes": [
            f"来源：{source} → 公众号",
            "✅ 结构重构：导语 → 分层论述 → 总结 → 互动",
            f"✅ 标题从 {len(title)} 字扩展至 {len(adapted_title)} 字",
            "✅ 正文已分段，适合深度阅读",
        ],
        "tips": [
            "行间距设为 1.5-1.75",
            "配图 3-5 张，每500字左右插一张",
            "重点语句**加粗**处理",
            "推送时间建议：早7:30 / 午12:00 / 晚20:00",
            "结尾引导「在看」和「转发」",
        ],
    }


def _restructure_to_wechat(text: str) -> dict:
    """按公众号长文结构重组"""
    sents = [s.strip() for s in text.replace("\n", "。").split("。") if len(s.strip()) > 5]
    n = len(sents)

    if n <= 3:
        # 太短就按原文分段
        body = text
    else:
        parts = []
        # 导语
        parts.append(f"📌 **导语**\n\n{sents[0]}。")
        # 分层（每2-3句一段）
        chunk_size = max(2, n // 3)
        for i in range(1, n - 1, chunk_size):
            chunk = sents[i:i + chunk_size]
            if chunk:
                parts.append("\n\n".join([f"{s}。" for s in chunk if s]))
        # 金句
        last = sents[-1]
        parts.append(f"---\n\n💡 **总结**\n\n{last}。\n\n---\n\n*觉得有用的话，点个「在看」让更多人看到 👀*")
        body = "\n\n".join(parts)

    return {"body": body}


# ============================================================
# 工具函数
# ============================================================

def _adapt_title(original: str, max_len: int, min_len: int = 8) -> str:
    """将原标题适配为平台标题格式"""
    if len(original) <= max_len and len(original) >= min_len:
        return original
    if len(original) > max_len:
        # 留一个字符给省略号
        return original[:max_len - 1] + "…"
    return original


def _adapt_wechat_title(original: str, full_text: str, max_len: int, min_len: int) -> str:
    """公众号标题可以比原文更长，需要扩展"""
    if len(original) >= min_len:
        return original[:max_len]
    # 太短时从正文取关键词补充
    import re
    words = re.findall(r'[\u4e00-\u9000]{2,}', full_text)
    from collections import Counter
    top = [w for w, _ in Counter(words).most_common(3) if w not in original]
    if top:
        return f"{original}｜{''.join(top)}"
    return original


def _extract_hook(lines: list) -> str:
    """从行中提取钩子"""
    if not lines:
        return "你知道吗？"
    first = lines[0]
    hook_words = ["警惕", "注意", "千万别", "重磅", "紧急", "你知道吗", "惊了"]
    if any(w in first for w in hook_words):
        return first
    return f"姐妹们注意了！{first}"


def _extract_hook_text(text: str, max_len: int = 30) -> str:
    """提取3秒钩子文本"""
    hook = text[:50].split("。")[0] if "。" in text[:50] else text[:50]
    if len(hook) > max_len:
        hook = hook[:max_len] + "…"
    return hook


def _shorten_sentence(s: str, max_chars: int = 15) -> str:
    """缩短句子到指定字数"""
    if len(s) <= max_chars:
        return s
    # 尝试在标点处截断
    import re
    for sep in ["，", ",", "、", "；", ";"]:
        parts = s.split(sep)
        if len(parts[0]) <= max_chars:
            return parts[0]
    return s[:max_chars] + "…"


def _split_paragraph(text: str, max_lines: int = 3) -> list:
    """将一段拆成多段，每段不超过max_lines行"""
    sents = [s.strip() for s in text.replace("\n", "").split("。") if s.strip()]
    result = []
    for i in range(0, len(sents), max_lines):
        chunk = "。".join(sents[i:i + max_lines]) + "。"
        if chunk.strip("。"):
            result.append(chunk.strip())
    return result if result else [text]


def _build_xiaohongshu_ending(lines: list) -> str:
    """生成小红书风格的结尾"""
    if not lines:
        return "大家还有什么问题，评论区见～ 💬"
    last = lines[-1]
    if "关注" in last or "收藏" in last:
        return last
    return f"{last}\n\n大家觉得有用的话收藏起来吧～ 💕"


def _build_douyin_ending(text: str) -> str:
    """生成抖音风格的引导结尾"""
    if any(w in text for w in ["关注", "点赞", "收藏"]):
        return text
    return f"{text}\n\n👇 觉得有用吗？\n❤️ 点赞支持一下\n🔔 关注我，学法律不吃亏"


def _suggest_tags(keywords: list, platform: str) -> list:
    """根据关键词和平台生成标签建议（只取2-6字的关键词）"""
    tags = []
    if platform == "xiaohongshu":
        tags = ["#法律科普", "#律师日常"]
        for kw in keywords[:5]:
            if 2 <= len(kw) <= 6:
                tags.append(f"#{kw}")
        if len(tags) < 4:
            tags.append("#涨知识")
    return list(dict.fromkeys(tags))[:8]  # 去重+限制8个
