"""
文案创作引擎 V3 — 平台规则来自DB，Agent完成文案生成

数据流：
  MCP: 提供平台规则 + 结构框架 + KPI参考
  Agent: 读取规则 → 按结构展开写全文 → 调用 store_knowledge 存储
"""

import json
import re
from database import get_conn


def _load_rules(platform: str) -> dict:
    """从 platform_rules 表读取平台规则"""
    conn = get_conn("seed")
    cur = conn.execute("SELECT rules FROM platform_rules WHERE platform = ?", (platform.lower(),))
    row = cur.fetchone()
    conn.close()
    return json.loads(row["rules"]) if row else {}


def generate_titles(topic: str, platform: str, count: int = 3) -> list:
    """
    提供平台标题规则和公式模板，Agent 据此生成具体标题。
    不做模板填充式"生成"。
    """
    rules = _load_rules(platform)
    if not rules:
        return [{"style": "通用", "template": f"【{topic}】— 值得了解的内容", "platform_rules": []}]

    title_rules = rules.get("title", {})
    formulas = title_rules.get("formulas", ["利益/痛点/悬念/数字"])
    length_range = title_rules.get("length", [15, 30])

    suggestions = []
    for formula in formulas[:count]:
        suggestions.append({
            "style": formula,
            "template_hint": f"按「{formula}」公式创作标题",
            "platform_rules": {"min": length_range[0], "max": length_range[1]},
        })

    return suggestions


def generate_outline(topic: str, platform: str, tone: str = None) -> dict:
    """
    根据主题和平台规则生成文案大纲。
    返回结构框架和规则，Agent 据此写全文。
    """
    rules = _load_rules(platform)
    if not rules:
        return {"error": f"不支持的平台：{platform}"}

    title_rules = rules.get("title", {})
    body_rules = rules.get("body", {})
    structure = body_rules.get("structure", [])
    kpi = rules.get("kpi", {})
    meta = rules.get("_meta", {"name": platform, "emoji": ""})

    outline = {
        "platform": meta.get("name", platform),
        "emoji": meta.get("emoji", ""),
        "topic": topic,
        "title_rules": {
            "length": title_rules.get("length", [15, 30]),
            "formulas": title_rules.get("formulas", []),
            "examples": title_rules.get("examples", [])[:3],
        },
        "body_rules": {
            "length": body_rules.get("length", [300, 800]),
            "tone": body_rules.get("tone", ""),
            "paragraph_max_lines": body_rules.get("paragraph_max_lines", 3),
        },
        "structure": [{"section": s[0], "guide": s[1]} for s in structure],
        "sections": [s[0] for s in structure],
        "kpi_reference": kpi,
    }

    # 平台特有参数
    if platform == "douyin":
        timing = body_rules.get("structure_60s", [])
        outline["video_timing"] = timing
        outline["suggested_duration"] = body_rules.get("video_length", {})
    elif platform == "xiaohongshu":
        outline["tag_guide"] = body_rules.get("tags", "")
    elif platform == "wechat":
        outline["formatting"] = body_rules.get("formatting", "")
        outline["publish_time"] = body_rules.get("publish_time", [])

    return outline


def adapt_across_platforms(content: str, source_platform: str, target_platform: str) -> dict:
    """
    跨平台适配建议。
    仅对比两个平台的规则差异和结构要求，实际改写给 Agent。
    """
    source_rules = _load_rules(source_platform)
    target_rules = _load_rules(target_platform)
    if not source_rules or not target_rules:
        return {"error": "不支持的平台，请先 store_platform_rules"}

    source_name = source_rules.get("_meta", {}).get("name", source_platform)
    target_name = target_rules.get("_meta", {}).get("name", target_platform)

    src_body = source_rules.get("body", {})
    tgt_body = target_rules.get("body", {})

    return {
        "from": source_name,
        "to": target_name,
        "source_rules": source_rules,
        "target_rules": target_rules,
        "conversion_notes": [
            f"长度：{src_body.get('length', ['?'])} \u2192 {tgt_body.get('length', ['?'])}",
            f"语气：{src_body.get('tone', '?')} \u2192 {tgt_body.get('tone', '?')}",
        ],
        "agent_tasks": [
            f"将内容从 {source_name} 语气转为 {target_name} 风格",
            "按目标平台结构重组段落",
            f"参考 {target_name} 的 KPI 指标优化",
        ],
        "target_outline": generate_outline(
            content.split("\n")[0][:30] if content else "内容", target_platform
        ),
    }


def get_platform_kpi(platform: str) -> dict:
    """读取指定平台的 KPI 参考值"""
    rules = _load_rules(platform)
    if not rules:
        return {"error": f"不支持的平台：{platform}"}
    return {
        "platform": rules.get("_meta", {}).get("name", platform),
        "kpi": rules.get("kpi", {}),
        "core_metrics": rules.get("kpi", {}).get("\u6838\u5fc3\u6307\u6807", []),
    }


def get_all_platforms_summary() -> list:
    """从DB读取所有平台规则摘要"""
    conn = get_conn("seed")
    rows = conn.execute("SELECT platform, rules FROM platform_rules").fetchall()
    conn.close()

    summary = []
    for row in rows:
        rules = json.loads(row["rules"])
        meta = rules.get("_meta", {})
        body = rules.get("body", {})
        kpi = rules.get("kpi", {})
        summary.append({
            "key": row["platform"],
            "name": meta.get("name", row["platform"]),
            "emoji": meta.get("emoji", ""),
            "title_length": rules.get("title", {}).get("length", []),
            "body_format": body.get("length", body.get("length_seconds", [])),
            "core_kpi": kpi.get("\u6838\u5fc3\u6307\u6807", [])[:3],
        })
    return summary


def initialize_platform_rules():
    """
    初始化种子数据到 platform_rules 表。
    仅在首次使用时调用。
    """
    seed_rules = {
        "xiaohongshu": {
            "_meta": {"name": "小红书", "emoji": "\U0001f4d5"},
            "title": {
                "length": [15, 22],
                "formulas": ["数字+利益", "痛点+解决方案", "反问+悬念"],
                "examples": ["3 个租房避坑技巧\uff5c再也不被中介坑钱了！", "律师告诉你：这5种情况不用请律师"],
            },
            "body": {
                "length": [300, 800],
                "paragraph_max_lines": 3,
                "structure": [
                    ["\u5f00\u5934", "直接给好处/痛点，第一人称"],
                    ["\u4e2d\u95f4", "分点讲干货/真实体验，emoji分隔"],
                    ["\u7ed3\u5c3e", "互动引导：姐妹们觉得呢？评论区聊聊"],
                ],
                "tone": "第一人称，种草分享感，不说教",
                "tags": "5-10个：1-2大词+3-5精准词+1-2话题词",
            },
            "kpi": {
                "\u6536\u85cf\u7387": {"\u4f18\u8d28": ">8%", "\u7206\u6b3e": ">15%"},
                "\u5b8c\u8bfb\u7387": {"\u6d41\u91cf\u6c60": ">30%"},
                "\u6838\u5fc3\u6307\u6807": ["\u6536\u85cf\u7387", "\u6df1\u5ea6\u9605\u8bfb\u7387", "\u4e92\u52a8\u7387", "\u70b9\u51fb\u7387", "\u5173\u952e\u8bcd\u5339\u914d\u5ea6"],
            },
        },
        "douyin": {
            "_meta": {"name": "抖音", "emoji": "\U0001f3b5"},
            "title": {
                "length": [15, 30],
                "formulas": ["反常识", "提问", "冲突", "结果前置"],
                "examples": ["90% 的人都不知道的维权方法", "离婚财产到底怎么分？"],
            },
            "body": {
                "length_seconds": [15, 60],
                "paragraph_max_lines": 1,
                "structure_60s": [
                    ["0-3\u79d2", "钩子：反常识/提问/冲突/结果前置"],
                    ["3-30\u79d2", "展开：痛点\u2192原因\u2192方案，短句\u226415字"],
                    ["30-50\u79d2", "亮点/反转/干货"],
                    ["50-60\u79d2", "强引导：点赞收藏/评论/关注"],
                ],
                "tone": "口语化，短句\u226415字，信息紧凑",
                "tags": "3-5个，主赛道+精准词+热点词",
                "video_length": {"\u65b0\u624b": "15-30\u79d2", "\u6210\u719f\u8d26\u53f7": "60-120\u79d2"},
            },
            "kpi": {
                "\u5b8c\u64ad\u7387": {"A\u7ea7": "\u226545%", "S\u7ea7": "\u226565%"},
                "3\u79d2\u7559\u5b58": {"\u57fa\u51c6": "\u226560%"},
                "\u6838\u5fc3\u6307\u6807": ["\u5b8c\u64ad\u7387", "3\u79d2\u7559\u5b58\u7387", "\u4e92\u52a8\u7387", "\u590d\u64ad\u7387", "\u505c\u7559\u65f6\u957f"],
            },
        },
        "wechat": {
            "_meta": {"name": "公众号", "emoji": "\U0001f4f0"},
            "title": {
                "length": [20, 30],
                "formulas": ["利益", "冲突", "悬念", "反差", "热点+价值承诺"],
                "examples": ["月薪5k和月薪3万的差距", "2024年最新劳动法解读"],
            },
            "body": {
                "length": [1200, 2500],
                "paragraph_max_lines": 4,
                "structure": [
                    ["\u5bfc\u8bed", "金句/问题引入"],
                    ["\u63d0\u51fa\u95ee\u9898", "引入场景/案例"],
                    ["\u5206\u5c42\u8bba\u8ff0", "案例/数据/观点，重点加粗"],
                    ["\u603b\u7ed3\u89c2\u70b9", "金句收尾"],
                    ["\u4e92\u52a8\u5f15\u5bfc", "在看+转发引导"],
                ],
                "tone": "专业但不生硬，有观点有温度",
                "formatting": "行间距1.5-1.75，配图3-5张，段落间留白",
                "publish_time": ["\u65e9 7:30-9:00", "\u5348 12:00-13:30", "\u665a 20:00-22:30"],
            },
            "kpi": {
                "\u6253\u5f00\u7387": {"\u65b0\u53f7": "\u22655%", "\u6d3b\u8dc3\u53f7": "\u226512%", "\u4f18\u8d28\u53f7": "\u226520%"},
                "\u8bfb\u5b8c\u7387": {"\u57fa\u51c6": ">40%"},
                "\u9605\u8bfb\u65f6\u957f": {"\u57fa\u51c6": ">2\u5206\u949f"},
                "\u6838\u5fc3\u6307\u6807": ["\u6253\u5f00\u7387", "\u5e73\u5747\u9605\u8bfb\u65f6\u957f", "\u5728\u770b\u7387", "\u7559\u8a00\u7387", "\u8f6c\u53d1\u7387"],
            },
        },
    }

    conn = get_conn("seed")
    for platform, rules in seed_rules.items():
        conn.execute(
            "INSERT OR REPLACE INTO platform_rules (platform, rules) VALUES (?, ?)",
            (platform, json.dumps(rules, ensure_ascii=False)),
        )
    conn.commit()
    conn.close()
    return {"status": "ok", "platforms": list(seed_rules.keys())}
