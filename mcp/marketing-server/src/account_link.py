"""账号链接解析模块 — 从用户提供的链接提取平台和 user_id"""

import re

# ============================================================
# 成本估算（基于 blogger-distiller 实际运行统计）
# ============================================================

COST_ESTIMATES = {
    30: {"min": 0.5, "max": 1.5, "display": "¥0.5~1.5"},
    50: {"min": 1.0, "max": 3.0, "display": "¥1.0~3.0"},
    80: {"min": 2.0, "max": 5.0, "display": "¥2.0~5.0"},
}

# ============================================================
# 链接解析
# ============================================================

def parse_account_link(url: str) -> dict:
    """
    解析用户提供的账号链接，返回平台和 user_id
    
    支持格式：
      小红书: https://www.xiaohongshu.com/user/profile/xxxxx
      抖音:   https://www.douyin.com/user/xxxxx
              https://v.douyin.com/xxxxx (短链接，需二次解析)
    
    Returns:
        {"platform": "xhs"/"douyin"/None, "user_id": str/None, "display_name": str, "error": str/None}
    """
    url = url.strip()

    # === 小红书 ===
    xhs_patterns = [
        r"(?:https?://)?(?:www\.)?xiaohongshu\.com/user/profile/([a-zA-Z0-9]+)",
        r"(?:https?://)?(?:www\.)?xhslink\.com/([a-zA-Z0-9]+)",
    ]
    for pat in xhs_patterns:
        m = re.search(pat, url)
        if m:
            return {
                "platform": "xhs",
                "platform_label": "小红书",
                "user_id": m.group(1),
                "url": url,
                "error": None,
            }

    # === 抖音 ===
    dy_patterns = [
        r"(?:https?://)?(?:www\.)?douyin\.com/user/([a-zA-Z0-9_-]+)",
        r"(?:https?://)?v\.douyin\.com/([a-zA-Z0-9_-]+)",
    ]
    for pat in dy_patterns:
        m = re.search(pat, url)
        if m:
            return {
                "platform": "douyin",
                "platform_label": "抖音",
                "user_id": m.group(1),
                "url": url,
                "error": None,
            }

    return {
        "platform": None,
        "platform_label": None,
        "user_id": None,
        "url": url,
        "error": "无法识别链接，请提供小红书或抖音账号主页链接\n"
                 "✅ 小红书：https://www.xiaohongshu.com/user/profile/xxx\n"
                 "✅ 抖音：https://www.douyin.com/user/xxx",
    }


def get_cost_estimate(max_notes: int) -> dict:
    """获取指定采集数量的成本估算"""
    estimate = COST_ESTIMATES.get(max_notes, COST_ESTIMATES[50])
    return {
        "max_notes": max_notes,
        "cost_display": estimate["display"],
        "cost_min": estimate["min"],
        "cost_max": estimate["max"],
    }


def format_cost_message(notes_count: int, actual_cost: float = None) -> str:
    """格式化成本信息"""
    est = get_cost_estimate(notes_count)
    if actual_cost is not None:
        return f"本次分析共采集 {notes_count} 条，费用 ¥{actual_cost:.2f}"
    return f"分析约 {notes_count} 条内容，预计费用 {est['cost_display']}"
