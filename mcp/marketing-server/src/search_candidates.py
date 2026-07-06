"""搜索博主候选人模块 — 通过 TikHub API 搜索并返回候选人列表供用户选择"""

import os
import sys
import json

# distiller scripts 路径
_DISTILLER_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "mcp", "blogger-distiller")
)
_SCRIPTS_DIR = os.path.join(_DISTILLER_DIR, "scripts")

_CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".xiaohongshu", "tikhub_config.json")


def _get_token() -> str:
    if not os.path.exists(_CONFIG_FILE):
        return ""
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("tikhub_api_token", "").strip()
    except (json.JSONDecodeError, OSError):
        return ""


def search_blogger_candidates(keyword: str, platform: str = "xhs") -> dict:
    """
    搜索博主，返回候选人列表供用户选择
    
    Args:
        keyword: 搜索关键词（博主名）
        platform: "xhs" 或 "douyin"
    
    Returns:
        {
            "found": True/False,
            "candidates": [{ "uid", "nickname", "fans", "desc", "avatar", "display" }, ...],
            "message": "..."
        }
    """
    token = _get_token()
    if not token:
        return {"found": False, "candidates": [], "message": "🔒 分析权限未开通，请联系微信 iodun001 开通"}

    # 动态导入 distiller 模块
    sys.path.insert(0, _SCRIPTS_DIR)
    try:
        from utils.tikhub_client import TikHubClient
        from utils.endpoint_router import EndpointRouter
        from utils.common import parse_count
    except ImportError as e:
        return {"found": False, "candidates": [], "message": f"blogger-distiller 导入失败: {e}"}

    try:
        router = EndpointRouter(token)
        client = TikHubClient(token, router)
        user_data = client.search_users(keyword)
    except Exception as e:
        return {"found": False, "candidates": [], "message": f"搜索失败: {e}"}

    # 解析候选人
    raw_users = []
    if isinstance(user_data, dict):
        data = user_data.get("data", {})
        items = data.get("items") or data.get("user_list") or data.get("users") or []
        if isinstance(items, list):
            raw_users = items
        elif isinstance(items, dict):
            raw_users = items.get("items", [])

    candidates = []
    seen_uids = set()
    for item in raw_users:
        u = item.get("user_info") or item.get("user") or item
        uid = str(u.get("id") or u.get("user_id") or u.get("userid") or u.get("userId") or "")
        if not uid or uid in seen_uids:
            continue
        seen_uids.add(uid)
        nick = u.get("name") or u.get("nickname") or u.get("nick_name") or "未知"
        sub_title = u.get("sub_title") or u.get("fans") or ""
        fans = parse_count(sub_title.replace("粉丝", "").strip()) if "粉丝" in str(sub_title) else 0
        desc = u.get("desc") or u.get("signature") or ""
        avatar = u.get("avatar") or u.get("head_image") or ""

        candidates.append({
            "uid": uid,
            "nickname": nick,
            "fans": fans,
            "desc": desc[:100] if desc else "",
            "avatar": avatar,
            "display": f"{nick} | {_fmt_fans(fans)}粉丝" + (f" | {desc[:60]}" if desc else ""),
        })

    if not candidates:
        return {"found": False, "candidates": [], "message": f"未找到与「{keyword}」匹配的博主"}

    return {
        "found": True,
        "candidates": candidates,
        "message": f"找到 {len(candidates)} 个匹配结果",
        "keyword": keyword,
    }


def _fmt_fans(n: int) -> str:
    if n >= 10000:
        return f"{n/10000:.1f}万"
    return str(n)
