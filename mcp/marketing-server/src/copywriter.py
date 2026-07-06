"""
文案创作引擎 — 基于三平台创作方法论的结构化文案生成

平台规则来源：小红书/抖音/公众号的核心指标 + 创作方法 + 参考值
"""

import re
from style_analyzer import analyze_style

# ============================================================
# 平台规则定义
# ============================================================

PLATFORM_RULES = {
    "xiaohongshu": {
        "name": "小红书",
        "emoji": "📕",
        # 标题规则
        "title": {
            "length": (15, 22),
            "formula": "数字 / 利益 / 痛点 + emoji + 悬念 / 关键词",
            "examples": [
                "3 个租房避坑技巧｜再也不被中介坑钱了！",
                "律师告诉你：这5种情况不用请律师",
                "劳动合同这样签，公司不敢坑你 😱",
            ],
        },
        # 正文规则
        "body": {
            "length": (300, 800),
            "paragraph_max_lines": 3,
            "structure": [
                ("开头", "直接给好处 / 痛点，用第一人称"),
                ("中间", "分点讲干货 / 真实体验，emoji 分隔段落"),
                ("结尾", "互动引导：'姐妹们觉得呢？评论区聊聊～'"),
            ],
            "tone": "第一人称“我 / 姐妹们”，种草分享感，不说教",
            "tags": "5–10 个：1–2 大词 + 3–5 精准长尾词 + 1–2 话题词",
        },
        # KPI 参考值
        "kpi": {
            "收藏率": {"优质": ">8%", "爆款": ">15%"},
            "完读率": {"流量池": ">30%"},
            "核心指标": ["收藏率（最高权重）", "深度阅读率", "互动率", "点击率", "关键词匹配度"],
        },
    },
    "douyin": {
        "name": "抖音",
        "emoji": "🎵",
        "title": {
            "length": (15, 30),
            "formula": "反常识 / 提问 / 冲突 / 结果前置",
            "examples": [
                "90% 的人都不知道的维权方法",
                "律师被问烂了：离婚财产到底怎么分？",
                "千万别在合同上签这个字！",
            ],
        },
        "body": {
            "length_seconds": (15, 60),
            "structure_60s": [
                ("0–3秒", "钩子：反常识、提问、冲突、结果前置"),
                ("3–30秒", "展开：痛点→原因→方案，短句≤15字"),
                ("30–50秒", "亮点/反转/干货：给增量信息"),
                ("50–60秒", "强引导：点赞收藏/评论/关注"),
            ],
            "tone": "口语化，短句≤15字，信息紧凑",
            "tags": "3–5 个，主赛道 + 精准词 + 热点词",
            "video_length": {"新手": "15–30秒", "成熟账号": "60–120秒"},
        },
        "kpi": {
            "完播率": {"A级": "≥45%", "S级": "≥65%"},
            "3秒留存": {"基准": "≥60%"},
            "核心指标": ["完播率（权重第一）", "3秒留存率", "互动率", "复播率", "停留时长"],
        },
    },
    "wechat": {
        "name": "公众号",
        "emoji": "📰",
        "title": {
            "length": (20, 30),
            "formula": "利益 / 冲突 / 悬念 / 反差 / 热点 + 价值承诺",
            "examples": [
                "月薪5k和月薪3万的差距，根本不在努力",
                "2024年最新劳动法解读：这3条不知道亏大了",
                "一个律师的忠告：别等吃了亏才看这篇文章",
            ],
        },
        "body": {
            "length": (1200, 2500),
            "paragraph_lines": (2, 4),
            "structure": [
                ("导语", "金句/问题引入，抓住注意力"),
                ("提出问题", "引入场景/案例"),
                ("分层论述", "案例/数据/观点，重点加粗"),
                ("总结观点", "金句收尾"),
                ("互动引导", "在看+转发引导"),
            ],
            "tone": "专业但不生硬，有观点有温度",
            "formatting": "行间距1.5-1.75，配图3-5张，段落间留白，重点突出",
            "publish_time": ["早 7:30–9:00", "午 12:00–13:30", "晚 20:00–22:30"],
        },
        "kpi": {
            "打开率": {"新号": "≥5%", "活跃号": "≥12%", "优质号": "≥20%"},
            "读完率": {"基准": ">40%"},
            "阅读时长": {"基准": ">2分钟"},
            "核心指标": ["打开率", "平均阅读时长", "在看率", "留言率", "转发率"],
        },
    },
}


# ============================================================
# 标题生成
# ============================================================

TITLE_TEMPLATES = {
    "xiaohongshu": {
        "数字+利益": ["{num}个{keyword}，{benefit}"],
        "痛点+解决方案": ["{pain}？{solution}"],
        "反问+悬念": ["你不会还不知道{keyword}吧？"],
        "对比+结果": ["{a}vs{b}，区别竟然这么大"],
    },
    "douyin": {
        "反常识": ["90%的人都不知道的{keyword}"],
        "结果前置": ["{action}前千万别{taboo}！"],
        "提问": ["{keyword}到底怎么{question}？"],
        "冲突": ["{a}和{b}，你选哪个？"],
    },
    "wechat": {
        "热点+价值": ["2024最新{keyword}解读：{value}"],
        "冲突+悬念": ["月薪5k和月薪5w的差距，根本不在{common_belief}"],
        "身份+忠告": ["一个{identity}的忠告：{warning}"],
        "数字+揭秘": ["{num}个你不知道的{keyword}真相"],
    },
}


def generate_titles(topic: str, platform: str, count: int = 3) -> list:
    """
    根据主题和平台生成标题建议
    实际使用中由 Agent 结合语义理解生成，此函数提供模板框架
    """
    platform = platform.lower()
    if platform not in TITLE_TEMPLATES:
        return [f"【{topic}】— 值得了解的内容"]

    templates = TITLE_TEMPLATES[platform]
    suggestions = []

    # GenAI 会用这些模板配合语义生成
    for style, tmpl_list in templates.items():
        for tmpl in tmpl_list:
            # Agent 会根据主题填充模板变量
            suggestions.append({
                "style": style,
                "template": tmpl,
                "platform_rules": PLATFORM_RULES[platform]["title"]["length"],
            })

    return suggestions[:count]


# ============================================================
# 文案结构生成
# ============================================================

def generate_outline(topic: str, platform: str, tone: str = None) -> dict:
    """
    根据主题和平台生成文案大纲
    返回包含结构化的章节指南，Agent 据此展开写全文
    """
    platform = platform.lower()
    if platform not in PLATFORM_RULES:
        return {"error": f"不支持的平台：{platform}"}

    rules = PLATFORM_RULES[platform]
    structure_key = "structure_60s" if platform == "douyin" else "structure"
    structure = rules["body"][structure_key]

    outline = {
        "platform": rules["name"],
        "emoji": rules["emoji"],
        "topic": topic,
        "title_rules": {
            "length": f"{rules['title']['length'][0]}-{rules['title']['length'][1]}字",
            "formula": rules['title']['formula'],
            "examples": rules['title']['examples'],
        },
        "body_rules": {
            "tone": rules["body"]["tone"],
            "structure_key": structure_key,
        "structure": [{"section": s[0], "guide": s[1]} for s in structure],
        },
        "sections": [s[0] for s in structure],
        "kpi_reference": rules.get("kpi", {}),
    }

    # 平台特有参数
    if platform == "douyin":
        outline["video_timing"] = rules["body"]["structure_60s"]
        outline["suggested_duration"] = rules["body"]["video_length"]
    elif platform == "xiaohongshu":
        outline["word_count"] = f"{rules['body']['length'][0]}-{rules['body']['length'][1]}字"
        outline["tag_guide"] = rules["body"]["tags"]
    elif platform == "wechat":
        outline["word_count"] = f"{rules['body']['length'][0]}-{rules['body']['length'][1]}字"
        outline["formatting"] = rules["body"]["formatting"]
        outline["publish_time"] = rules["body"]["publish_time"]

    return outline


# ============================================================
# 跨平台适配
# ============================================================

def adapt_across_platforms(content: str, source_platform: str, target_platform: str) -> dict:
    """
    将一篇文案适配到其他平台，附带每个平台的转换建议
    """
    source = source_platform.lower()
    target = target_platform.lower()

    if source not in PLATFORM_RULES or target not in PLATFORM_RULES:
        return {"error": "不支持的平台"}

    source_info = PLATFORM_RULES[source]
    target_info = PLATFORM_RULES[target]

    # 分析源文风格
    style = analyze_style(content)

    return {
        "from": source_info["name"],
        "to": target_info["name"],
        "style_analysis": style["summary"],
        "conversion_notes": [
            f"长度：从{source_info['body'].get('length', ['?'])}格式转为{target_info['body'].get('length', ['?'])}格式",
            f"语气：保持{style['structured_features']['tone']}基调，适配{target_info['body']['tone']}",
            f"结构：按 {target_info['name']} 的标准结构重新组织",
        ],
        "target_outline": generate_outline(
            style.get("keywords", ["该主题"])[0] if style.get("keywords") else "内容",
            target_platform
        ),
    }


# ============================================================
# 平台规则查询
# ============================================================

def get_platform_kpi(platform: str) -> dict:
    """获取指定平台的 KPI 参考值"""
    platform = platform.lower()
    if platform not in PLATFORM_RULES:
        return {"error": f"不支持的平台：{platform}"}
    return {
        "platform": PLATFORM_RULES[platform]["name"],
        "kpi": PLATFORM_RULES[platform].get("kpi", {}),
        "core_metrics": PLATFORM_RULES[platform]["kpi"]["核心指标"],
    }


def get_all_platforms_summary() -> list:
    """获取所有平台规则摘要"""
    summary = []
    for key, rule in PLATFORM_RULES.items():
        summary.append({
            "key": key,
            "name": rule["name"],
            "emoji": rule["emoji"],
            "title_length": rule["title"]["length"],
            "body_format": rule["body"].get("length", rule["body"].get("length_seconds")),
            "core_kpi": rule["kpi"]["核心指标"][:3],
        })
    return summary
