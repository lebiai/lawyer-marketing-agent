"""品牌一致性检查模块 V2

数据流：
  MCP: 存储品牌规范 → 读取规则 → 返回原始数据
  Agent: 读取品牌规范 + 原文 → 分析一致性 → 给出建议
"""
from database import get_conn


def check_brand_consistency(content: str, platform: str = None) -> dict:
    """
    读取品牌规范，返回原始数据供 Agent 检查一致性。
    不进行关键词匹配式的一致性判断。
    """
    conn = get_conn("knowledge")
    profiles = conn.execute("SELECT * FROM brand_profile WHERE is_active=1").fetchall()
    conn.close()

    if not profiles:
        return {
            "has_profile": False,
            "message": "尚未配置品牌规范，请先通过 store_knowledge(brand_profile) 设置",
            "profiles": [],
            "content_length": len(content),
            "platform": platform,
        }

    brand_rules = []
    for p in profiles:
        brand_rules.append({
            "dimension": p["dimension"],
            "rule": p["content"],
            "created_at": p.get("created_at", ""),
        })

    return {
        "has_profile": True,
        "content_length": len(content),
        "platform": platform,
        "profiles": brand_rules,
        "raw_content": content,
        "note": "品牌规范已返回，一致性分析由 Agent 完成",
    }


def suggest_improvements(content: str, platform: str) -> list:
    """
    读取平台规则，检查内容是否符合基础平台规范。
    （纯规则校验，非关键词分析）
    """
    conn = get_conn("seed")
    cur = conn.execute("SELECT rules FROM platform_rules WHERE platform = ?", (platform,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return ["未知平台，无法提供优化建议"]

    import json
    rules = json.loads(row["rules"])
    suggestions = []

    title = content.split("\n")[0] if content else ""
    title_len = len(title)
    max_title = rules.get("title_max_length", 999)
    if title_len > max_title:
        suggestions.append(f"标题过长（{title_len}字），建议控制在{max_title}字以内")

    min_title = rules.get("title_min_length", 0)
    if title_len < min_title:
        suggestions.append(f"标题过短（{title_len}字），建议至少{min_title}字")

    max_body = rules.get("body_max_length", 99999)
    if len(content) > max_body:
        suggestions.append(f"正文过长（{len(content)}字），建议控制在{max_body}字以内")

    if not suggestions:
        suggestions.append("文案基本符合平台规范")

    return suggestions
