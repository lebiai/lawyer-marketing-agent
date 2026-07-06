"""品牌一致性检查模块"""
from database import get_conn

def check_brand_consistency(content: str, platform: str = None) -> dict:
    conn = get_conn("knowledge")
    profiles = conn.execute("SELECT * FROM brand_profile WHERE is_active=1").fetchall()
    conn.close()
    
    if not profiles:
        return {
            "has_profile": False,
            "message": "尚未配置品牌规范，请先通过 store_knowledge(brand_profile) 设置",
            "checks": []
        }
    
    checks = []
    issues = []
    for p in profiles:
        dim = p["dimension"]
        rule = p["content"].lower()
        
        if dim == "tone":
            if any(w in rule for w in ["严肃", "严谨", "专业"]) and any(w in content for w in ["哈哈", "嘻嘻", "😂"]):
                issues.append("品牌设定为严肃语气，但文案包含轻佻表达")
                checks.append({"dimension": "语气", "status": "❌", "detail": "存在轻佻表达"})
            elif "亲切" in rule and not any(w in content for w in ["你", "我们", "~"]):
                issues.append("品牌设定为亲切语气，建议增加第二人称")
                checks.append({"dimension": "语气", "status": "⚠️", "detail": "亲切感不足"})
            else:
                checks.append({"dimension": "语气", "status": "✅", "detail": f"符合 {rule[:20]} 设定"})
        
        elif dim == "taboo":
            found = [w.strip() for w in rule.split(",") if w.strip() in content]
            if found:
                issues.append(f"包含违禁词：{', '.join(found)}")
                checks.append({"dimension": "违禁词", "status": "❌", "detail": f"发现：{', '.join(found)}"})
            else:
                checks.append({"dimension": "违禁词", "status": "✅", "detail": "未发现违禁词"})
        
        elif dim == "keywords":
            keywords = [w.strip() for w in rule.split(",")]
            covered = [k for k in keywords if k in content]
            if len(covered) < len(keywords) * 0.5:
                issues.append(f"核心关键词覆盖率不足（{len(covered)}/{len(keywords)}）")
                checks.append({"dimension": "关键词覆盖", "status": "⚠️", "detail": f"覆盖 {len(covered)}/{len(keywords)}"})
            else:
                checks.append({"dimension": "关键词覆盖", "status": "✅", "detail": f"覆盖 {len(covered)}/{len(keywords)}"})
        
        elif dim == "target_audience":
            checks.append({"dimension": "受众匹配", "status": "✅", "detail": f"面向：{p['content'][:40]}..."})
        
        else:
            checks.append({"dimension": dim, "status": "✅", "detail": p['content'][:50]})
    
    return {
        "has_profile": True,
        "content_length": len(content),
        "platform": platform,
        "checks": checks,
        "issues": issues,
        "pass": len(issues) == 0,
        "summary": f"检查通过 ✅" if len(issues) == 0 else f"发现 {len(issues)} 个问题 ❌"
    }

def suggest_improvements(content: str, platform: str) -> list:
    conn = get_conn("seed")
    cur = conn.execute("SELECT rules FROM platform_rules WHERE platform = ?", (platform,))
    row = cur.fetchone()
    conn.close()
    
    if not row:
        return ["未知平台，无法提供优化建议"]
    
    import json
    rules = json.loads(row["rules"])
    suggestions = []
    
    title_len = len(content.split("\n")[0]) if content else 0
    max_title = rules.get("title_max_length", 999)
    if title_len > max_title:
        suggestions.append(f"标题过长（{title_len}字），建议控制在{max_title}字以内")
    
    taboo = rules.get("taboo", [])
    for word in taboo:
        if word in content:
            suggestions.append(f"避免使用违禁词：{word}")
    
    if not suggestions:
        suggestions.append("文案基本符合平台规范")
    
    return suggestions
