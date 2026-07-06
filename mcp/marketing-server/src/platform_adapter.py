"""
多平台文案适配器 V3 — 规则来自DB，结构转换可配置

架构：
  MCP: 读取平台规则 → 提供结构化框架 + 格式转换
  Agent: 基于规则+框架写完整文案
"""

import json
import re
from database import get_conn


def _load_rules(platform: str) -> dict:
    """从 platform_rules 表读取平台规则"""
    conn = get_conn("seed")
    cur = conn.execute("SELECT rules FROM platform_rules WHERE platform = ?", (platform,))
    row = cur.fetchone()
    conn.close()
    if row:
        return json.loads(row["rules"])
    # 兜底默认值
    return {
        "title_max_length": 30,
        "title_min_length": 8,
        "body_max_length": 2500,
        "body_min_length": 100,
        "paragraph_max_lines": 3,
    }


def adapt_content(content: str, source_platform: str, target_platform: str) -> dict:
    """
    智能跨平台适配 - 基于DB规则的结构转换
    实际内容改写和创意优化由 Agent 完成。
    """
    target = target_platform.lower()
    rules = _load_rules(target)

    lines = [l.strip() for l in content.split("\n") if l.strip()]
    original_title = lines[0] if lines else ""
    body_lines = lines[1:] if len(lines) > 1 else lines

    max_title = rules.get("title_max_length", 30)
    min_title = rules.get("title_min_length", 8)
    max_pl = rules.get("paragraph_max_lines", 3)

    # 标题适配
    adapted_title = original_title
    if len(original_title) > max_title:
        adapted_title = original_title[:max_title - 1] + "\u2026"
    elif len(original_title) < min_title:
        adapted_title = original_title  # Agent 会基于规则扩展

    # 段落拆分（纯格式转换）
    formatted_body = []
    for para in body_lines:
        sents = [s.strip() for s in para.replace("\n", "").split("\u3002") if s.strip()]
        for i in range(0, len(sents), max_pl):
            chunk = "\u3002".join(sents[i:i + max_pl]) + "\u3002"
            chunk = chunk.strip()
            if chunk and chunk != "\u3002":
                formatted_body.append(chunk)

    if not formatted_body:
        formatted_body = body_lines

    return {
        "title": adapted_title,
        "title_rules": {"min": min_title, "max": max_title, "current": len(adapted_title)},
        "body": "\n\n".join(formatted_body) if formatted_body else content,
        "body_line_count": len(formatted_body),
        "platform_rules": rules,
        "conversion_notes": [
            f"来源：{source_platform} → {target}",
            f"标题：{len(original_title)}字 \u2192 {len(adapted_title)}字",
            f"正文：{len(body_lines)}段 \u2192 {len(formatted_body)}段（每段\u2264{max_pl}行）",
        ],
        "agent_tasks": [
            "根据目标平台规则优化标题公式",
            "添加平台特定的语气和表达方式",
            "生成话题标签（小红书）或口播标注（抖音）",
            "添加互动引导结尾",
        ],
    }
