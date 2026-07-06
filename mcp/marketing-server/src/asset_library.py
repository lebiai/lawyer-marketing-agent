"""素材库管理模块"""
from database import get_conn

ASSET_CATEGORIES = {
    "image_template": "图片模板",
    "video_clip": "视频片段",
    "brand_color": "品牌色板",
    "font_style": "字体风格",
    "icon_set": "图标集",
    "music_track": "背景音乐",
    "voice_sample": "语音样本",
    "other": "其他"
}

def store_asset(name: str, category: str, description: str, tags: list = None) -> dict:
    conn = get_conn("knowledge")
    conn.execute(
        "INSERT INTO personal_notes (title, content, tags, source) VALUES (?, ?, ?, ?)",
        (name, description, str(tags or []), f"asset:{category}")
    )
    conn.commit()
    asset_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]
    conn.close()
    return {"status": "ok", "asset_id": asset_id, "message": f"素材「{name}」已存入"}

def search_assets(query: str = None, category: str = None) -> list:
    conn = get_conn("knowledge")
    if category:
        rows = conn.execute(
            "SELECT id, title, content, tags, source, created_at FROM personal_notes WHERE source = ?",
            (f"asset:{category}",)
        ).fetchall()
    elif query:
        rows = conn.execute(
            "SELECT id, title, content, tags, source, created_at FROM personal_notes WHERE title LIKE ? OR content LIKE ?",
            (f"%{query}%", f"%{query}%")
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, title, content, tags, source, created_at FROM personal_notes WHERE source LIKE 'asset:%'"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_asset_stats() -> dict:
    conn = get_conn("knowledge")
    total = conn.execute("SELECT COUNT(*) as c FROM personal_notes WHERE source LIKE 'asset:%'").fetchone()["c"]

    by_category = {}
    cur = conn.execute("SELECT source, COUNT(*) as c FROM personal_notes WHERE source LIKE 'asset:%' GROUP BY source")
    for row in cur.fetchall():
        cat = row["source"].replace("asset:", "")
        by_category[ASSET_CATEGORIES.get(cat, cat)] = row["c"]

    conn.close()
    return {"total": total, "by_category": by_category}

def get_categories() -> dict:
    return ASSET_CATEGORIES
