"""
LLM 驱动的深度分析模块。
替代原有的关键词匹配分析，提供真正的智能分析。

工作方式：
  1. 检查环境变量 LLM_API_KEY 或 OPENAI_API_KEY
  2. 有 Key → LLM 深度分析（1-2次调用）
  3. 无 Key → 回退到规则引擎

环境变量：
  LLM_API_KEY         OpenAI/兼容 API Key
  LLM_BASE_URL        OpenAI/兼容 API 地址（可选）
  LLM_MODEL          模型名（可选，默认 gpt-4o-mini）
"""

import json
import os
import re
import urllib.request
import urllib.error
from typing import Optional
from datetime import datetime

# ============================================================
# 配置
# ============================================================

_API_KEY = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
_BASE_URL = os.environ.get("LLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")

_LLM_AVAILABLE = bool(_API_KEY)


def is_llm_available() -> bool:
    """检查 LLM 是否可用"""
    return _LLM_AVAILABLE


# ============================================================
# LLM API 调用
# ============================================================

def _call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.3, max_tokens: int = 4096) -> Optional[str]:
    """调用 OpenAI 兼容 API，返回响应文本"""
    if not _LLM_AVAILABLE:
        return None

    payload = json.dumps({
        "model": _MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode("utf-8")

    url = f"{_BASE_URL.rstrip('/')}/chat/completions"
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "lawyer-marketing-agent/1.0",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"]
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, KeyError, OSError) as e:
        print(f"  ⚠️ LLM 调用失败: {e}")
        return None


def _extract_json(text: str) -> Optional[dict]:
    """从 LLM 响应中提取 JSON"""
    if not text:
        return None
    # 尝试直接解析
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"```(?:json)?\s*", "", text).strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 尝试从文本中提取 JSON 块
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return None


# ============================================================
# 风格分析 — LLM 驱动
# ============================================================

def analyze_account_style(profile: dict, notes: list, stats: dict, tag_freq: list[tuple]) -> dict:
    """
    LLM 驱动的四层风格分析。
    
    Args:
        profile: 博主资料 {nickname, desc, fans, ...}
        notes: 笔记/视频列表（取 top 15 用于分析）
        stats: 统计 {total, avg_likes, ...}
        tag_freq: [(tag, count), ...]
    
    Returns:
        风格分析 dict
    """
    if not _LLM_AVAILABLE or not notes:
        return {}

    # 取 top 15 笔记
    sample_notes = sorted(notes, key=lambda n: n.get("likes", 0), reverse=True)[:15]

    # 构建样本文本
    samples = []
    for i, n in enumerate(sample_notes):
        title = n.get("title", "")[:60]
        desc = (n.get("desc", "") or "")[:200]
        likes = n.get("likes", 0)
        comments = n.get("comments_count", 0)
        collects = n.get("collects", 0)
        tags_list = n.get("tags", [])[:5]
        samples.append(
            f"[内容{i+1}]\n"
            f"标题: {title}\n"
            f"正文: {desc}\n"
            f"互动: {likes}赞 / {comments}评 / {collects}藏\n"
            f"标签: {', '.join(tags_list)}\n"
        )

    samples_text = "\n".join(samples)

    # Top tags
    top_tags = [f"#{t[0]}" for t in tag_freq[:10]]

    user_profile = f"昵称: {profile.get('nickname', '?')}\n简介: {profile.get('desc', '?')}\n粉丝: {profile.get('fans', '?')}"

    system_prompt = """你是一个社交媒体内容分析师。你的任务是分析博主的风格特征，输出结构化 JSON。

分析维度：
1. 情感基调（1-2个词）：理性客观 / 温暖治愈 / 犀利直白 / 幽默俏皮 / 高级克制 / 热血有力 / 文艺感性 / 共情倾诉 / 其他
2. 语气立场（1个词）：平等对话 / 权威指导 / 朋友分享 / 官方正式 / 自嘲玩梗
3. 目标受众（1个）：描述最可能的受众群体，如"职场人群"、"婚恋需求人群"、"泛娱乐用户"
4. 语言特征：标题风格、句式特点（短句/长句、问句/陈述等）、人称使用
5. 内容类别：按主题给内容分类（不是按态度），分析各类占比
6. 认知层核心观点：提炼博主反复表达的核心观点/价值观
7. 标题模式：归纳标题的常见模式
8. 风格标签：3-5个概括性标签

只输出 JSON，格式：
{
  "tone": "情感基调",
  "stance": "语气立场", 
  "audience": "目标受众",
  "language_features": "语言特征描述",
  "content_categories": [{"name": "类别名", "pct": 占比数字, "example": "示例"}],
  "core_opinions": ["观点1", "观点2", ...],
  "title_patterns": ["模式1", "模式2", ...],
  "style_tags": ["标签1", "标签2", ...]
}"""

    user_prompt = f"""请分析以下博主的风格特征。

【博主资料】
{user_profile}

【常用标签】
{', '.join(top_tags)}

【统计数据】
共 {stats.get('total', 0)} 篇样本
均赞 {stats.get('avg_likes', 0)} | 均评 {stats.get('avg_comments', 0)} | 均藏 {stats.get('avg_collects', 0)}

【内容样本（Top 15）】
{samples_text}

请输出 JSON 格式的分析结果。"""

    response = _call_llm(system_prompt, user_prompt)
    result = _extract_json(response)
    if result:
        print(f"  ✅ LLM 风格分析完成")
    else:
        print(f"  ⚠️ LLM 风格分析无结果")
    return result or {}


# ============================================================
# 评论洞察 — LLM 驱动
# ============================================================

def analyze_comments_insight(notes: list) -> dict:
    """
    LLM 驱动的评论洞察分析。
    
    Args:
        notes: 带评论的笔记列表
    
    Returns:
        {
            "sentiment": {"positive": N, "neutral": N, "negative": N},
            "pain_points": [{...}],
            "user_needs": [{...}],
            "top_comments": [{...}],
            "interaction_summary": "...",
        }
    """
    if not _LLM_AVAILABLE:
        return {}

    # 收集评论样本（取 top 5 笔记的评论）
    top_notes = sorted(notes, key=lambda n: n.get("likes", 0), reverse=True)[:5]
    all_comments = []
    for n in top_notes:
        comment_list = n.get("comment_list", [])
        for c in comment_list[:10]:  # 每篇取前 10
            content = c.get("content", "").strip()
            likes = c.get("likes", c.get("likeCount", 0))
            if content:
                all_comments.append({"content": content, "likes": likes})

    if not all_comments:
        return {}

    # 排序取高赞评论
    all_comments.sort(key=lambda x: x.get("likes", 0), reverse=True)
    top_15_comments = all_comments[:15]

    # 构建评论样本（去重）
    seen = set()
    comment_samples = []
    for c in top_15_comments:
        text = c["content"][:150]
        if text not in seen:
            seen.add(text)
            comment_samples.append(f"[赞{c['likes']}] {text}")
    
    comment_text = "\n".join(comment_samples)

    system_prompt = """你是一个社交媒体评论分析师。分析评论区的用户声音，输出结构化 JSON。

分析要求：
1. 情绪分布：统计正面/中性/负面评论比例
2. 真实痛点：归纳评论区暴露的具体问题、焦虑、困扰（3-5条，每条一句话）
3. 真实需求：归纳用户实际想要什么、在找什么（3-5条，每条一句话）
4. 高价值评论：提取最有信息量/代表性的 3 条评论
5. 互动特征：作者回复情况、评论区整体氛围

只输出 JSON，格式：
{
  "sentiment": {"positive": 正面占比数字, "neutral": 中性占比数字, "negative": 负面占比数字},
  "sentiment_label": "整体情绪倾向",
  "pain_points": [{"point": "痛点描述", "evidence": "依据的评论例证"}],
  "user_needs": [{"need": "需求描述", "evidence": "依据的评论例证"}],
  "top_comments": [{"content": "评论内容", "likes": 赞数, "value": "这条评论的价值说明"}],
  "interaction_summary": "互动特征简要描述"
}"""

    user_prompt = f"""请分析以下评论数据：

共有 {len(all_comments)} 条评论样本，以下是高赞评论：

{comment_text}

请输出 JSON 格式的分析结果。"""

    response = _call_llm(system_prompt, user_prompt)
    result = _extract_json(response)
    if result:
        print(f"  ✅ LLM 评论洞察完成")
    else:
        print(f"  ⚠️ LLM 评论洞察无结果")
    return result or {}


# ============================================================
# 综合一轮分析
# ============================================================

def deep_analyze(profile: dict, notes: list, stats: dict, tag_freq: list) -> dict:
    """一轮 LLM 调用完成全部风格分析"""
    if not _LLM_AVAILABLE:
        return {}

    # Sample top 20 notes
    sample_notes = sorted(notes, key=lambda n: n.get("likes", 0), reverse=True)[:20]

    # Collect comments from top 10
    top_10 = sample_notes[:10]
    all_comments = []
    for n in top_10:
        for c in (n.get("comment_list") or [])[:10]:
            text = c.get("content", "").strip()
            likes = c.get("likes", c.get("likeCount", 0))
            if text:
                all_comments.append({"content": text, "likes": likes})

    all_comments.sort(key=lambda x: x.get("likes", 0), reverse=True)
    top_comments = all_comments[:20]

    # Build prompt data
    profile_text = f"昵称: {profile.get('nickname', '?')}\n简介: {profile.get('desc', '?')[:200]}\n粉丝: {profile.get('fans', '?')}"
    
    samples = []
    for i, n in enumerate(sample_notes[:15]):
        desc = (n.get("desc", "") or "")[:200]
        tags = n.get("tags", [])[:5]
        samples.append(
            f"[#{i+1}] 标题:{n.get('title','')[:60]} | "
            f"赞{n.get('likes',0)}评{n.get('comments_count',0)}藏{n.get('collects',0)} | "
            f"标签:{','.join(tags)}\n{desc}\n"
        )
    samples_text = "\n".join(samples)

    top_tags = [f"#{t[0]}" for t in tag_freq[:15]]

    comment_samples = []
    for c in top_comments[:15]:
        comment_samples.append(f"[赞{c['likes']}] {c['content'][:120]}")
    comment_text = "\n".join(comment_samples)

    system_prompt = """你是一个专业的社交媒体内容分析师。分析以下博主的数据，输出完整分析报告。

请严格按照以下 JSON 格式输出，只输出 JSON：
{
  "style": {
    "tone": "情感基调",
    "stance": "语气立场",
    "audience": "目标受众群体",
    "language_features": "语言特征（句式、用词风格、人称使用）",
    "title_patterns": ["标题模式1", "标题模式2"],
    "style_tags": ["风格标签1", "风格标签2"]
  },
  "content_strategy": {
    "categories": [{"name": "类别名", "pct": 占比数字}],
    "core_opinions": ["核心观点1", "核心观点2"],
    "value_words": ["价值词1", "价值词2"]
  },
  "comment_insight": {
    "sentiment": {"positive": 数字, "neutral": 数字, "negative": 数字},
    "pain_points": [{"point": "痛点", "evidence": "评论依据"}],
    "user_needs": [{"need": "需求", "evidence": "评论依据"}],
    "notable_comments": [{"content": "评论", "likes": 赞数}],
    "interaction_style": "互动特征"
  }
}

情感基调可选：理性客观 / 温暖治愈 / 犀利直白 / 幽默俏皮 / 高级克制 / 热血有力 / 文艺感性 / 共情倾诉
语气立场可选：平等对话 / 权威指导 / 朋友分享 / 官方正式 / 自嘲玩梗"""

    user_prompt = f"""【博主资料】
{profile_text}

【高频标签】
{', '.join(top_tags)}

【数据统计】
样本量: {stats.get('total', 0)}
均赞: {stats.get('avg_likes', 0)} | 均评: {stats.get('avg_comments', 0)} | 均藏: {stats.get('avg_collects', 0)}

【内容样本（Top 15）】
{samples_text}

【评论样本（Top 15）】
{comment_text}

请输出分析 JSON。"""

    response = _call_llm(system_prompt, user_prompt)
    result = _extract_json(response)
    if result:
        print(f"  ✅ LLM 综合分析完成")
    return result or {}
