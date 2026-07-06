"""多平台文案适配器"""

def adapt_content(content: str, source_platform: str, target_platform: str, rules: dict) -> dict:
    """
    将文案从源平台格式转换为目标平台格式
    返回 {title, body, tips}
    """
    if target_platform == "xiaohongshu":
        return _to_xiaohongshu(content, rules)
    elif target_platform == "douyin":
        return _to_douyin(content, rules)
    elif target_platform == "wechat":
        return _to_wechat(content, rules)
    else:
        return {"title": "", "body": content, "tips": ["未知平台"]}

def _to_xiaohongshu(content: str, rules: dict) -> dict:
    max_title = rules.get("title_max_length", 20)
    lines = content.strip().split("\n")
    title = lines[0][:max_title] if lines else ""
    body_lines = []
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        body_lines.append(line)
    body = "\n\n".join(body_lines)
    return {
        "title": title,
        "body": body,
        "tips": [
            "建议每段 2-4 行",
            "结尾加上相关话题标签",
            "适当添加 emoji 增加可读性"
        ]
    }

def _to_douyin(content: str, rules: dict) -> dict:
    max_title = rules.get("title_max_length", 30)
    lines = content.strip().split("\n")
    title = lines[0][:max_title] if lines else ""
    body_parts = []
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        body_parts.append(line)
    body = "\n".join(body_parts)
    return {
        "title": title,
        "body": body,
        "tips": [
            "开场 3 秒必须抛出钩子",
            "控制在 15-60 秒口播量",
            "结尾加上引导互动的话术"
        ]
    }

def _to_wechat(content: str, rules: dict) -> dict:
    max_title = rules.get("title_max_length", 64)
    lines = content.strip().split("\n")
    title = lines[0][:max_title] if lines else ""
    body = "\n\n".join(lines[1:])
    return {
        "title": title,
        "body": body,
        "tips": [
            "建议插入小标题分段",
            "在结尾加金句总结",
            "可加入互动引导"
        ]
    }
