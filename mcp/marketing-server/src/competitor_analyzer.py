"""竞品账号分析模块 V3 — blogger-distiller 集成版

工作流：
  1. 检查 TikHub Token → 无则引导加微信
  2. 有 Token → 调 blogger-distiller 采集+分析
  3. 解析 analysis.json → 存入 knowledge.db
  4. 提取风格特征 → 存入 content_samples
"""

import os
import json
import subprocess
import re
import urllib.request
import urllib.error
import shutil
import concurrent.futures
from datetime import datetime
from urllib.parse import urlparse
from search_candidates import search_blogger_candidates, _CONFIG_FILE
from account_link import parse_account_link, get_cost_estimate, format_cost_message
from llm_analyzer import deep_analyze, is_llm_available
from database import get_conn

# ============================================================
# 项目路径
# ============================================================

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_DISTILLER_DIR = os.path.join(_PROJECT_ROOT, "mcp", "blogger-distiller")
_DISTILLER_SCRIPTS = os.path.join(_DISTILLER_DIR, "scripts")
_DISTILLER_DATA = os.path.join(_DISTILLER_DIR, "data")

# ============================================================
# 账号分析导出目录
# ============================================================
_ACCOUNT_ANALYSIS_DIR = os.path.join(_PROJECT_ROOT, "账号分析")


def _sanitize_folder_name(name: str, max_len: int = 40) -> str:
    """\u5c06\u6807\u9898\u8f6c\u4e3a\u5b89\u5168\u7684\u6587\u4ef6\u5939\u540d\uff0c\u53bb\u9664\u7279\u6b8a\u5b57\u7b26\u3001\u622a\u65ad\u957f\u5ea6"""
    if not name:
        return "\u672a\u547d\u540d"
    # \u53bb\u9664 # \u6807\u7b7e\u548c @\u63d0\u4eba
    import re as _re
    name = _re.sub(r"[#@#​\u200c]", "", name)
    # \u53bb\u9664\u884c\u5185\u94fe\u63a5
    name = _re.sub(r"https?://\S+", "", name)
    # \u53bb\u9664 Windows \u6587\u4ef6\u540d\u7981\u6b62\u5b57\u7b26
    clean = _re.sub(r'[\\/:*?"<>|]', "", name)
    # \u53bb\u9664\u9996\u5c3e\u7a7a\u767d\u548c\u70b9
    clean = clean.strip(". \t\n\r")
    if not clean:
        return "\u672a\u547d\u540d"
    # \u622a\u65ad
    if len(clean) > max_len:
        clean = clean[:max_len].rstrip()
    return clean


def export_account_analysis(result: dict, report_text: str = "", billing_info: dict = None, style_features: dict = None):
    """
    将 distiller 分析结果镜像导出到 账号分析/ 目录。

    目录结构：
        账号分析/
        └── {account_name}/
            └── {platform}_{YYYYMMDD}/
                ├── notes_details.json   原样复制
                ├── analysis.json        原样复制
                ├── report.md            图文报告
                ├── style_profile.json   风格特征
                ├── billing.json         费用账单
                └── 内容_1/
                    ├── cover.jpg             封面图
                    ├── img_1.jpg             正文配图
                    ├── img_2.jpg
                    ├── video.mp4             视频（如果有）
                    ├── comments.json         该条评论
                    └── info.json             标题/正文/互动数据等元信息
                └── 内容_2/
                    └── ...
    不影响 notes_details 和 analysis 的内容，仅做文件系统镜像。
    """
    account_name = result.get("account_name", "unknown")
    platform = result.get("platform", "xhs")
    data_dir = result.get("data_dir", "")
    analysis_file = result.get("analysis_file", "")

    if not data_dir or not os.path.exists(data_dir):
        print("  ⚠️ 无数据目录\uff0c跳过文件系统导出")
        return

    platform_label = "小红书" if platform == "xhs" else "抖音" if platform == "douyin" else platform
    date_suffix = datetime.now().strftime("%Y%m%d")
    safe_name = safe_filename(account_name)

    export_dir = os.path.join(_ACCOUNT_ANALYSIS_DIR, safe_name, f"{platform_label}_{date_suffix}")
    os.makedirs(export_dir, exist_ok=True)

    print(f"📁 导出到: {export_dir}")

    # ---- 1. 复制 notes_details.json ----
    details_file = None
    for fname in os.listdir(data_dir):
        if fname.endswith("_notes_details.json") or fname.endswith("_videos_details.json") or fname.endswith("_details.json"):
            details_file = os.path.join(data_dir, fname)
            break
    if details_file and os.path.exists(details_file):
        shutil.copy2(details_file, os.path.join(export_dir, "notes_details.json"))
        print(f"  ✅ notes_details.json")
    else:
        print(f"  ⚠️ 未找到 notes_details.json")

    # ---- 2. 复制 analysis.json ----
    if analysis_file and os.path.exists(analysis_file):
        shutil.copy2(analysis_file, os.path.join(export_dir, "analysis.json"))
        print(f"  ✅ analysis.json")

    # ---- 3. 每条内容独立文件夹 ----
    content_count = 0
    if details_file and os.path.exists(details_file):
        with open(details_file, "r", encoding="utf-8") as f:
            details = json.load(f)

        for i, entry in enumerate(details):
            if "_error" in entry:
                continue

            content_count += 1
            note_id = entry.get("_feed_id", f"note_{i}")
            note_obj = entry.get("note") or {}
            video_obj = entry.get("video") or {}
            # 用标题命名文件夹
            raw_title = note_obj.get("title") or note_obj.get("displayTitle") or video_obj.get("title") or ""
            raw_desc = note_obj.get("desc") or video_obj.get("desc") or ""
            if not raw_title.strip():
                first_parts = raw_desc.split("#")
                first_line = first_parts[0].strip() if first_parts else raw_desc.strip()
                raw_title = first_line[:60] if first_line else "未命名"
            content_name = _sanitize_folder_name(raw_title)
            content_dir = os.path.join(export_dir, content_name)
            if os.path.exists(content_dir):
                content_dir = os.path.join(export_dir, f"{content_name}_{content_count}")
            os.makedirs(content_dir, exist_ok=True)

            # --- info.json: \u8be5\u6761内容\u7684\u5143\u4fe1\u606f ---
            interact = note_obj.get("interactInfo") or video_obj.get("interactInfo") or {}
            info = {
                "note_id": note_id,
                "title": note_obj.get("title") or note_obj.get("displayTitle") or note_obj.get("display_title") or video_obj.get("title") or "",
                "desc": note_obj.get("desc") or video_obj.get("desc") or "",
                "type": note_obj.get("type") or video_obj.get("type") or "",
                "create_time": note_obj.get("time") or note_obj.get("createTime") or video_obj.get("create_time") or "",
                "likes": interact.get("likedCount") or interact.get("liked_count") or "0",
                "comments": interact.get("commentCount") or interact.get("comment_count") or "0",
                "collects": interact.get("collectedCount") or interact.get("collected_count") or "0",
                "shares": interact.get("shareCount") or interact.get("shareCount") or interact.get("shared_count") or "0",
                "tags": note_obj.get("tagList") or video_obj.get("tagList") or [],
            }
            with open(os.path.join(content_dir, "info.json"), "w", encoding="utf-8") as f:
                json.dump(info, f, ensure_ascii=False, indent=2)

            # --- 下载图片 ---
            image_list = (
                note_obj.get("imageList") or
                note_obj.get("image_list") or
                note_obj.get("images") or
                video_obj.get("imageList") or
                video_obj.get("images") or
                []
            )
            img_count = 0
            if isinstance(image_list, list):
                for j, img in enumerate(image_list):
                    if isinstance(img, dict):
                        img_url = (
                            img.get("urlDefault") or
                            img.get("url_default") or
                            img.get("urlPre") or
                            img.get("url_pre") or
                            img.get("url") or
                            (img.get("infoList", [{}])[0].get("url") if img.get("infoList") else None)
                        )
                    elif isinstance(img, str):
                        img_url = img
                    else:
                        continue
                    if img_url and _download_media(img_url, content_dir, f"img_{j}"):
                        img_count += 1

            # --- 封面图\uff08\u65e0内容\u56fe\u7247\u65f6\u4f5c\u4e3a\u66ff\u4ee3\uff09 ---
            if img_count == 0:
                # Try coverUrl directly (Douyin), then cover object (XHS)
                cover_url = note_obj.get("coverUrl") or video_obj.get("coverUrl") or ""
                if not cover_url:
                    cover = note_obj.get("cover") or {}
                    if isinstance(cover, dict):
                        cover_url = cover.get("urlDefault") or cover.get("url_default") or cover.get("urlPre") or cover.get("url_pre") or cover.get("url") or ""
                    elif isinstance(cover, str):
                        cover_url = cover
                    else:
                        cover_url = ""
                if cover_url:
                    ext = ".jpg"
                    if "mp4" in cover_url.lower() or "video" in cover_url.lower():
                        ext = ".mp4"
                    _download_media(cover_url, content_dir, "cover", ext)
                    img_count = 1

            # --- 下载视频 ---
            video_url = ""
            if isinstance(note_obj.get("video"), dict):
                video_url = note_obj["video"].get("url") or note_obj["video"].get("videoUrl") or note_obj["video"].get("video_url") or ""
            if not video_url:
                video_url = note_obj.get("videoUrl") or note_obj.get("video_url") or ""
            if not video_url:
                video_url = video_obj.get("videoUrl") or video_obj.get("video_url") or ""
            if not video_url:
                if isinstance(note_obj.get("videoInfo"), dict):
                    video_url = note_obj["videoInfo"].get("url") or ""
            if video_url:
                ext = _guess_ext(video_url, ".mp4")
                _download_media(video_url, content_dir, "video", ext)

            # --- comments.json: 该条评论 ---
            comments_data = entry.get("comments", {})
            if isinstance(comments_data, dict):
                comment_list = comments_data.get("list") or comments_data.get("comments") or []
            elif isinstance(comments_data, list):
                comment_list = comments_data
            else:
                comment_list = []
            if comment_list:
                with open(os.path.join(content_dir, "comments.json"), "w", encoding="utf-8") as f:
                    json.dump(comment_list, f, ensure_ascii=False, indent=2)

            folder_name = os.path.basename(content_dir)
            print(f"  📁 {folder_name}: {note_id[:10]}... {img_count}\u56fe" + (" 🎬 \u89c6\u9891" if video_url else ""))

    print(f"  ✅ 共 {content_count} \u6761内容导出到 {export_dir}")

    # ---- 4. 生成 report.md ----
    if report_text:
        with open(os.path.join(export_dir, "report.md"), "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"  📄 report.md")

    # ---- 5. 生成 billing.json ----
    if billing_info:
        with open(os.path.join(export_dir, "billing.json"), "w", encoding="utf-8") as f:
            json.dump(billing_info, f, ensure_ascii=False, indent=2)
        print(f"  💰 billing.json")

    # ---- 6. 生成 style_profile.json ----
    if style_features:
        with open(os.path.join(export_dir, "style_profile.json"), "w", encoding="utf-8") as f:
            json.dump(style_features, f, ensure_ascii=False, indent=2, default=str)
        print(f"  🎨 style_profile.json")

    # 统计媒体摘要
    content_folders = []
    for item in os.listdir(export_dir):
        item_path = os.path.join(export_dir, item)
        if os.path.isdir(item_path):
            folder_info = {'name': item}
            files = os.listdir(item_path)
            folder_info['images'] = len([f for f in files if f.startswith('img_') or f.startswith('cover')])
            folder_info['has_video'] = any(f.endswith('.mp4') for f in files)
            folder_info['has_comments'] = 'comments.json' in files
            content_folders.append(folder_info)
    dump_summary = {
        'export_dir': export_dir,
        'content_count': len(content_folders),
        'total_images': sum(f['images'] for f in content_folders),
        'total_videos': sum(1 for f in content_folders if f['has_video']),
    }
    print(f"  ✅ 导出完成")
    return dump_summary


def _download_media(url: str, dest_dir: str, filename: str, ext_hint: str = None) -> bool:
    """Download media file locally, auto-detect extension via Content-Type"""
    if not url or not url.startswith("http"):
        return False
    ext = ext_hint or _guess_ext(url, ".jpg")
    filepath = os.path.join(dest_dir, f"{filename}{ext}")
    if os.path.exists(filepath):
        return True
    referers = ["https://www.douyin.com/", "https://www.xiaohongshu.com/"]
    last_err = None
    for ref in referers:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Referer": ref,
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            if len(data) < 1024:
                last_err = f"data too small ({len(data)} bytes)"
                continue
            # Detect real extension from Content-Type header
            ct = resp.headers.get("Content-Type", "") or ""
            real_ext = _ct_to_ext(ct)
            if real_ext and real_ext != ext:
                filepath = os.path.join(dest_dir, f"{filename}{real_ext}")
            with open(filepath, "wb") as f:
                f.write(data)
            # 自动将 WebP/HEIC 转为 JPEG（macOS 预览兼容性）
            if real_ext in (".webp", ".heic") and ct.startswith("image/"):
                jpg_path = os.path.join(dest_dir, f"{filename}.jpg")
                if real_ext == ".webp":
                    _try_convert_webp_to_jpg(filepath, jpg_path)
                elif real_ext == ".heic":
                    _try_convert_heic_to_jpg(filepath, jpg_path)
                if os.path.exists(jpg_path):
                    os.remove(filepath)
                    filepath = jpg_path
            return True
        except Exception as e:
            last_err = str(e)[:60]
            continue
    if last_err and "403" not in last_err and "429" not in last_err:
        print(f"  Download failed {url[:50]}...: {last_err}")
    return False


def _try_convert_webp_to_jpg(src: str, dst: str):
    """Convert WebP to JPEG using system tools"""
    try:
        import subprocess as _sp
        # Try PIL/Pillow first
        try:
            from PIL import Image
            img = Image.open(src)
            img = img.convert("RGB")
            img.save(dst, "JPEG", quality=92)
            return
        except ImportError:
            pass
        # Fallback: macOS sips command
        _sp.run(["sips", "-s", "format", "jpeg", src, "--out", dst],
                capture_output=True, timeout=30)
    except Exception:
        pass


def _try_convert_heic_to_jpg(src: str, dst: str):
    """Convert HEIC to JPEG using system tools"""
    try:
        import subprocess as _sp
        try:
            from PIL import Image
            img = Image.open(src)
            img = img.convert("RGB")
            img.save(dst, "JPEG", quality=92)
            return
        except ImportError:
            pass
        # Fallback: macOS sips or magick
        _sp.run(["sips", "-s", "format", "jpeg", src, "--out", dst],
                capture_output=True, timeout=30)
    except Exception:
        pass


_CONTENT_TYPE_MAP = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/x-msvideo": ".avi",
    "video/x-flv": ".flv",
}


def _ct_to_ext(content_type: str) -> str:
    """Map HTTP Content-Type to file extension"""
    if not content_type:
        return ""
    base = content_type.split(";")[0].strip().lower()
    return _CONTENT_TYPE_MAP.get(base, "")
def _guess_ext(url: str, fallback: str = ".jpg") -> str:
    """Infer file extension from URL path, domain, and query params"""
    path = urlparse(url).path
    _, ext = os.path.splitext(path)
    if ext and ext.lower() in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov", ".avi", ".flv"):
        return ext.lower()
    domain = urlparse(url).hostname or ""
    if "rednotecdn" in domain or "xhscdn" in domain:
        return ".jpg"
    if "douyinpic" in domain or "douyinvod" in domain or "zjcdn" in domain:
        return ".jpg"
    if "jpg" in url.lower() or "jpeg" in url.lower():
        return ".jpg"
    if "png" in url.lower():
        return ".png"
    if "webp" in url.lower():
        return ".webp"
    if "mp4" in url.lower():
        return ".mp4"
    qs = urlparse(url).query.lower()
    if "fmt=jpg" in qs or "imageView2" in qs:
        return ".jpg"
    if "fmt=png" in qs:
        return ".png"
    if "fmt=webp" in qs:
        return ".webp"
    return fallback
def check_tikhub_balance() -> dict:
    """调用 TikHub API 检查账户余额是否充足"""
    token = _get_token_from_config()
    if not token:
        return {"ok": False, "message": "未配置 TikHub Token"}

    try:
        req = urllib.request.Request(
            "https://api.tikhub.dev/api/v1/tikhub/user/get_user_info",
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            # 余额信息通常在 data.balance 或类似字段
            balance = data.get("data", {}).get("balance") or data.get("balance")
            return {"ok": True, "balance": balance, "message": f"余额充足" if balance is None or balance > 0 else "余额不足"}
    except urllib.error.HTTPError as e:
        if e.code == 402:
            return {"ok": False, "message": "TikHub 账户余额不足，请联系微信 iodun001 充值"}
        return {"ok": False, "message": f"TikHub API 返回错误 (HTTP {e.code})"}
    except Exception as e:
        # 网络问题等，允许继续（不做硬性阻断）
        return {"ok": True, "message": "余额检测跳过（网络问题），将继续采集"}


def _get_token_from_config() -> str:
    if not os.path.exists(_CONFIG_FILE):
        return ""
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("tikhub_api_token", "").strip()
    except (json.JSONDecodeError, OSError):
        return ""


def record_billing(action: str, target: str, platform: str, notes_count: int, estimated_cost: str, actual_cost: float = None, status: str = "success", error_message: str = None) -> dict:
    """记录账单到 profile.db"""
    try:
        conn = get_conn("profile")
        conn.execute(
            "INSERT INTO billing (action, target, platform, notes_count, estimated_cost, actual_cost, status, error_message) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (action, target, platform, notes_count, estimated_cost, actual_cost, status, error_message),
        )
        conn.commit()
        bill_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return {"bill_id": bill_id, "ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def check_tikhub_status() -> dict:
    """检查 TikHub Token 是否已配置"""
    if not os.path.exists(_CONFIG_FILE):
        return {
            "configured": False,
            "message": "🔒 竞品/对标账号分析需要开通权限，请联系微信 iodun001 开通"
        }
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        token = cfg.get("tikhub_api_token", "").strip()
        if not token:
            return {
                "configured": False,
                "message": "🔒 竞品/对标账号分析需要开通权限，请联系微信 iodun001 开通"
            }
        return {
            "configured": True,
            "message": "✅ 分析权限已开通",
            "token": token[:8] + "..."  # 只暴露前8位
        }
    except (json.JSONDecodeError, OSError):
        return {
            "configured": False,
            "message": "🔒 竞品/对标账号分析需要开通权限，请联系微信 iodun001 开通"
        }


def _save_tikhub_token(token: str):
    """保存 TikHub Token（由管理员开通时使用）"""
    os.makedirs(os.path.dirname(_CONFIG_FILE), exist_ok=True)
    cfg = {}
    if os.path.exists(_CONFIG_FILE):
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    cfg["tikhub_api_token"] = token
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ============================================================
# Blogger-distiller 执行
# ============================================================

PLATFORM_MAP = {
    "xiaohongshu": "xhs",
    "xhs": "xhs",
    "douyin": "douyin",
    "抖音": "douyin",
    "小红书": "xhs",
}

COUNT_MAP = {"1": 30, "2": 50, "3": 80}


def run_distiller(account_name: str, platform: str, max_notes: int = 50, user_id: str = None, max_comments: int = 20, parallel_workers: int = 3) -> dict:
    """
    运行 blogger-distiller 全流程（Phase 1 采集 + Phase 2 分析）
    
    Args:
        account_name: 博主名（用于展示）
        platform: "xiaohongshu" / "douyin"
        max_notes: 30 / 50 / 80
        user_id: 可选。指定 user_id 可跳过搜索阶段，直接爬取
    
    Returns:
        分析结果 dict
    """
    plat = PLATFORM_MAP.get(platform, "xhs")
    data_dir = os.path.join(_DISTILLER_DATA, safe_filename(account_name))
    os.makedirs(data_dir, exist_ok=True)

    # ---- Phase 1: 数据采集 ----
    crawl_script = os.path.join(_DISTILLER_SCRIPTS, "crawl_blogger.py")
    safe_name = safe_filename(account_name)
    details_file = os.path.join(data_dir, f"{safe_name}_notes_details.json")
    
    if parallel_workers > 1 and max_notes >= 30:
        # ==================== 并行模式 ====================
        # Step 1a: list-only 模式 — 只获取笔记ID列表
        list_cmd = [
            "python3", crawl_script,
            account_name,
            "-o", data_dir,
            "--max-notes", str(max_notes),
            "--platform", plat,
            "--list-only",
        ]
        if user_id:
            list_cmd.extend(["--user-id", user_id])
        
        print(f"📋 阶段1/4: 获取 {account_name} 的笔记ID列表...")
        list_result = subprocess.run(list_cmd, capture_output=True, text=True, cwd=_DISTILLER_DIR)
        if list_result.returncode != 0:
            error_msg = (list_result.stderr or list_result.stdout or "未知错误").lower()
            if "402" in error_msg or "余额" in error_msg or "insufficient" in error_msg or "out of credit" in error_msg:
                return {"error": True, "message": "TikHub 账户余额不足，请联系微信 iodun001 充值", "credit_error": True}
            return {"error": True, "message": f"获取笔记列表失败: {error_msg[:200]}"}
        
        # 加载笔记ID
        ids_path = os.path.join(data_dir, f"{safe_name}_note_ids.json")
        if not os.path.exists(ids_path):
            return {"error": True, "message": f"未找到笔记ID文件: {ids_path}"}
        with open(ids_path, "r", encoding="utf-8") as f:
            ids_data = json.load(f)
        all_ids = ids_data.get("note_ids", [])
        if not all_ids:
            return {"error": True, "message": "笔记ID列表为空"}
        
        print(f"✅ 共获取 {len(all_ids)} 条笔记ID，开始并行采集...")
        
        # Step 1b: 拆分为 N 个 chunk
        n_workers = min(parallel_workers, len(all_ids))
        chunk_size = max(1, len(all_ids) // n_workers)
        chunks = [all_ids[i:i + chunk_size] for i in range(0, len(all_ids), chunk_size)]
        print(f"  拆分 {len(chunks)} 个 chunk (每个约 {chunk_size} 条)")
        
        # Step 1c: 为每个 chunk 创建 chunk 文件
        chunk_files = []
        for ci, chunk_ids in enumerate(chunks):
            chunk_file = os.path.join(data_dir, f"{safe_name}_chunk_{ci}_ids.json")
            chunk_data = {
                "nickname": ids_data.get("nickname", account_name),
                "user_id": ids_data.get("user_id", user_id or ""),
                "platform": plat,
                "note_ids": chunk_ids,
                "total": len(chunk_ids),
            }
            with open(chunk_file, "w", encoding="utf-8") as f:
                json.dump(chunk_data, f, ensure_ascii=False, indent=2)
            chunk_files.append(chunk_file)
        
        # Step 1d: 并行采集每个 chunk
        def _run_chunk(chunk_path, ci):
            chunk_cmd = [
                "python3", crawl_script,
                account_name,
                "-o", data_dir,
                "--platform", plat,
                "--chunk-file", chunk_path,
                "--max-comments", str(max_comments),
            ]
            chunk_out = os.path.join(data_dir, f"{safe_name}_chunk_{ci}_details.json")
            print(f"  🚀 Chunk {ci+1}/{len(chunks)}: {len(json.load(open(chunk_path))['note_ids'])} 条")
            r = subprocess.run(chunk_cmd, capture_output=True, text=True, cwd=_DISTILLER_DIR, timeout=600)
            if r.returncode != 0:
                return {"error": r.stderr or r.stdout or "unknown", "ci": ci}
            # 查找 chunk 输出的详情文件
            for fname in os.listdir(data_dir):
                if fname.endswith("_notes_details.json") and fname.startswith(safe_name):
                    src = os.path.join(data_dir, fname)
                    dst = os.path.join(data_dir, f"{safe_name}_chunk_{ci}_details.json")
                    if src != dst:
                        import shutil as _sh
                        _sh.copy2(src, dst)
                    break
            return {"ok": True, "ci": ci}
        
        results = {}
        print(f"\n📡 阶段2/4: 并行采集 {len(chunks)} 个 chunk...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(chunks)) as executor:
            future_map = {executor.submit(_run_chunk, cf, ci): ci for ci, cf in enumerate(chunk_files)}
            for future in concurrent.futures.as_completed(future_map):
                r = future.result()
                if r.get("error"):
                    print(f"  ❌ Chunk {r['ci']+1} 失败: {r['error'][:100]}")
                else:
                    print(f"  ✅ Chunk {r['ci']+1} 完成")
                results[r['ci']] = r
        
        # Step 1e: 合并 chunks
        print(f"\n🔗 阶段3/4: 合并 {len(chunks)} 个 chunk...")
        chunk_detail_files = []
        for ci in range(len(chunks)):
            cf = os.path.join(data_dir, f"{safe_name}_chunk_{ci}_details.json")
            if os.path.exists(cf):
                chunk_detail_files.append(cf)
        
        if not chunk_detail_files:
            return {"error": True, "message": "所有 chunk 采集均失败"}
        
        merge_script = os.path.join(_DISTILLER_SCRIPTS, "merge_crawl_chunks.py")
        merge_cmd = [
            "python3", merge_script,
            data_dir,
            safe_name,
            "--chunks",
        ] + chunk_detail_files
        merge_result = subprocess.run(merge_cmd, capture_output=True, text=True, cwd=_DISTILLER_DIR)
        if merge_result.returncode != 0:
            print(f"  ⚠️ 合并 stdout: {merge_result.stdout[:200]}")
            print(f"  ⚠️ 合并 stderr: {merge_result.stderr[:200]}")
        
        # 清理临时文件
        for f in chunk_files + chunk_detail_files:
            try:
                os.remove(f)
            except OSError:
                pass
        
        if not os.path.exists(details_file):
            return {"error": True, "message": f"合并后未找到详情文件: {details_file}"}
        
        print(f"   ✅ 合并完成: {details_file}")
        
    else:
        # ==================== 顺序模式（单线程，原流程）====================
        crawl_cmd = [
            "python3", crawl_script,
            account_name,
            "-o", data_dir,
            "--max-notes", str(max_notes),
            "--platform", plat,
        ]
        if user_id:
            crawl_cmd.extend(["--user-id", user_id])
        crawl_cmd.extend(["--max-comments", str(max_comments)])
        
        print(f"📡 正在采集 {account_name} 的 {max_notes} 篇内容，约需 30-45 分钟...")
        result = subprocess.run(crawl_cmd, capture_output=True, text=True, cwd=_DISTILLER_DIR)
        if result.returncode != 0:
            error_msg = (result.stderr or result.stdout or "未知错误").lower()
            if "402" in error_msg or "余额" in error_msg or "insufficient" in error_msg or "out of credit" in error_msg:
                return {"error": True, "message": "TikHub 账户余额不足，请联系微信 iodun001 充值", "credit_error": True}
            return {"error": True, "message": f"采集失败: {error_msg[:200]}"}

    # ---- Phase 2: 数据分析 ----
    if not os.path.exists(details_file):
        return {"error": True, "message": f"未找到采集数据: {details_file}"}

    analyze_script = os.path.join(_DISTILLER_SCRIPTS, "analyze.py")
    analyze_cmd = [
        "python3", analyze_script,
        details_file,
        "-o", data_dir,
    ]

    print("📊 正在分析数据...")
    result2 = subprocess.run(analyze_cmd, capture_output=True, text=True, cwd=_DISTILLER_DIR)
    if result2.returncode != 0:
        error_msg = result2.stderr or result2.stdout or "未知错误"
        return {"error": True, "message": f"分析失败: {error_msg[:200]}"}

    # ---- 读取分析结果 ----
    analysis_file = os.path.join(data_dir, f"{safe_name}_analysis.json")
    if not os.path.exists(analysis_file):
        return {"error": True, "message": f"未找到分析结果: {analysis_file}"}

    with open(analysis_file, "r", encoding="utf-8") as f:
        analysis_data = json.load(f)

    # 读取 profile 数据
    profile_data = {}
    safe_name_local = safe_filename(account_name)
    for fname in os.listdir(data_dir):
        if fname.endswith("_profile.json"):
            try:
                with open(os.path.join(data_dir, fname), "r", encoding="utf-8") as pf:
                    profile_data = json.load(pf)
            except Exception:
                pass
            break

    return {
        "error": False,
        "account_name": account_name,
        "platform": plat,
        "data_dir": data_dir,
        "analysis_file": analysis_file,
        "profile": profile_data,
        "stats": analysis_data.get("stats", {}),
        "category_stats": analysis_data.get("category_stats", {}),
        "tag_freq": analysis_data.get("tag_freq", []),
        "top10": analysis_data.get("top10", []),
        "opinion_candidates": analysis_data.get("opinion_candidates", []),
        "writing_structure": analysis_data.get("writing_structure", {}),
        "value_words": analysis_data.get("value_words", []),
        "notes_count": analysis_data.get("notes_count", 0),
        "raw_data": analysis_data,
    }


def safe_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip()


# ============================================================
# 从 distiller 分析结果构建报告+风格
# ============================================================

def build_report_from_distiller(result: dict, llm_data: dict = None) -> dict:
    """
    将 distiller 的分析结果转为我们的 6维报告格式+风格特征
    """
    stats = result.get("stats", {})
    category_stats = result.get("category_stats", {})
    tag_freq = result.get("tag_freq", [])
    top10 = result.get("top10", [])
    opinion = result.get("opinion_candidates", [])
    value_words = result.get("value_words", [])

    # ---- 定位与基调（从观点句 + 标签 + 互动特征推断） ----
    tone = "中性"
    stance = "中性叙述"
    audience = "泛人群"
    opinion_text = " ".join(c["sentence"] for c in opinion[:20])
    all_tags_text = " ".join(t[0] for t in tag_freq[:20])
    combined_text = opinion_text + " " + all_tags_text
    
    # --- 情感基调（8种风格） ---
    if combined_text:
        tone_score = {}
        # 犀利直白
        if any(w in combined_text for w in ["必须", "一定", "绝不", "警告", "警惕", "千万别", "马上", "立即", "立刻", "停止"]):
            tone_score["犀利直白"] = sum(combined_text.count(w) for w in ["必须", "一定", "绝不", "警告", "警惕", "千万别", "马上", "立即"])
        # 温暖治愈
        if any(w in combined_text for w in ["温暖", "别怕", "没关系", "一起", "陪伴", "加油", "温柔", "爱自己", "治愈", "拥抱"]):
            tone_score["温暖治愈"] = sum(combined_text.count(w) for w in ["温暖", "别怕", "一起", "加油", "温柔", "治愈"])
        # 理性客观
        if any(w in combined_text for w in ["数据", "研究", "分析", "根据", "统计", "调查", "报告", "趋势", "比例", "案例"]):
            tone_score["理性客观"] = sum(combined_text.count(w) for w in ["数据", "分析", "根据", "统计", "调查"])
        # 幽默风趣
        if any(w in combined_text for w in ["笑死", "哈哈哈", "笑", "搞笑", "段子", "离谱", "整活", "沙雕"]):
            tone_score["幽默风趣"] = sum(combined_text.count(w) for w in ["笑死", "搞笑", "离谱", "沙雕"])
        # 文艺感性
        if any(w in combined_text for w in ["月光", "诗意", "浪漫", "灵魂", "时光", "岁月", "星辰", "山海", "温柔"]):
            tone_score["文艺感性"] = sum(combined_text.count(w) for w in ["诗意", "浪漫", "灵魂", "时光", "星辰"])
        # 热血有力
        if any(w in combined_text for w in ["改变", "突破", "奋斗", "逆袭", "坚持", "力量", "强大", "成长", "觉醒"]):
            tone_score["热血有力"] = sum(combined_text.count(w) for w in ["突破", "奋斗", "逆袭", "坚持", "强大", "觉醒"])
        # 高级克制
        if any(w in combined_text for w in ["极简", "质感", "审美", "设计", "品味", "风格"]):
            tone_score["高级克制"] = sum(combined_text.count(w) for w in ["极简", "质感", "审美", "设计", "品味"])
        # 共情倾诉
        if any(w in combined_text for w in ["懂你", "我懂", "经历过", "一样", "也是", "感同身受", "理解"]):
            tone_score["共情倾诉"] = sum(combined_text.count(w) for w in ["懂你", "经历过", "一样", "感同身受", "理解"])
        
        if tone_score:
            tone = max(tone_score, key=tone_score.get)
    
    # --- 语气立场（5种） ---
    if combined_text:
        stance_score = {}
        # 朋友分享
        if any(w in combined_text for w in ["我觉得", "我认为", "我的", "我", "分享"]):
            stance_score["朋友分享"] = sum(combined_text.count(w) for w in ["我觉得", "我的", "我", "分享"])
        # 权威指导
        if any(w in combined_text for w in ["记住", "千万", "注意", "法律规定", "必须", "一定", "绝对", "所有人"]):
            stance_score["权威指导"] = sum(combined_text.count(w) for w in ["记住", "注意", "法律规定", "必须", "绝对"])
        # 平等对话
        if any(w in combined_text for w in ["我们", "一起", "大家", "姐妹们", "兄弟们"]):
            stance_score["平等对话"] = sum(combined_text.count(w) for w in ["我们", "一起", "大家"])
        # 自嘲玩梗
        if any(w in combined_text for w in ["本", "本人", "菜", "社恐", "i人", "懒人", "手残"]):
            stance_score["自嘲玩梗"] = sum(combined_text.count(w) for w in ["菜", "社恐", "懒人", "手残"])
        # 官方正式
        if any(w in combined_text for w in ["公告", "通知", "声明", "说明"]):
            stance_score["官方正式"] = sum(combined_text.count(w) for w in ["公告", "通知", "声明"])
        
        if stance_score:
            stance = max(stance_score, key=stance_score.get)
    
    # --- 目标受众（从标签+内容推断） ---
    audience_map = [
        (["职场", "工作", "上班", "打工人", "同事", "老板"], "职场人群"),
        (["宝妈", "育儿", "孩子", "宝宝", "妈妈", "亲子", "孕"], "宝妈/育儿群体"),
        (["学生", "考研", "高考", "考公", "留学", "校园", "大学生"], "学生群体"),
        (["单身", "恋爱", "对象", "男朋友", "女朋友", "相亲", "结婚"], "婚恋群体"),
        (["减肥", "健身", "运动", "健康", "养生", "饮食"], "健康养生群体"),
        (["穿搭", "化妆", "护肤", "变美", "时尚", "发型"], "时尚美妆群体"),
        (["投资", "理财", "买房", "赚钱", "副业", "存钱"], "理财投资群体"),
        (["律师", "打官司", "离婚", "合同", "维权", "法律"], "法律需求群体"),
        (["退休", "老年", "养老", "社保", "医保"], "中老年群体"),
        (["00后", "90后", "年轻", "年轻人"], "年轻群体"),
    ]
    best_match = None
    best_count = 0
    for keywords, label in audience_map:
        count = sum(combined_text.count(kw) for kw in keywords)
        if count > best_count:
            best_count = count
            best_match = label
    if best_match:
        audience = best_match

    # 如果观点句太少且没有标签匹配，fallback 到统计推断
    if audience == "泛人群" and title_patterns:
        # 从标题模式推断
        if "故事型" in title_patterns and title_patterns["故事型"].get("pct", 0) > 30:
            audience = "故事共鸣型读者"
        elif "教程型" in title_patterns and title_patterns["教程型"].get("pct", 0) > 30:
            audience = "学习实操型读者"
        elif "数字型" in title_patterns and title_patterns["数字型"].get("pct", 0) > 30:
            audience = "效率信息型读者"

    # ---- 语言与文字（从 top10 统计） ----
    if top10:
        sample_titles = [n.get("title", "") for n in top10]
        avg_title_len = round(sum(len(t) for t in sample_titles) / len(sample_titles)) if sample_titles else 0
        title_patterns = _detect_title_patterns(sample_titles)
    else:
        avg_title_len = 0
        title_patterns = {}

    # ---- 互动表现 ----
    total = stats.get("total", 0)
    engagement = {
        "avg_likes": stats.get("avg_likes", 0),
        "avg_comments": stats.get("avg_comments", 0),
        "avg_collects": stats.get("avg_collects", 0),
        "avg_shares": stats.get("avg_shares", 0),
        "total_likes": stats.get("total_likes", 0),
        "total_samples": total,
        "collected_rate": stats.get("collected_rate", 0),
    }

    # ---- 内容策略 ----
    main_categories = []
    if category_stats:
        sorted_cats = sorted(category_stats.items(), key=lambda x: x[1].get("count", 0), reverse=True)
        main_categories = [
            {"name": name, "count": v.get("count", 0), "pct": v.get("pct", 0), "avg_likes": v.get("avg_likes", 0)}
            for name, v in sorted_cats[:6]
        ]

    # ---- 高频话题 ----
    topics = []
    for tag, count in tag_freq[:15]:
        topics.append({"topic": tag, "frequency": count})

    # ---- 高互动内容 ----
    best_performers = []
    for i, n in enumerate(top10[:5]):
        best_performers.append({
            "rank": i + 1,
            "title": n.get("title", ""),
            "desc": n.get("desc", ""),
            "likes": n.get("likes_raw", 0),
            "collects": n.get("collects_raw", 0),
            "comments": n.get("comments_raw", 0),
            "category": n.get("category", ""),
            "tags": n.get("tags", []),
        })

    # ---- 认知层----
    cognitive = {
        "core_opinions": [c["sentence"] for c in opinion[:10]],
        "value_words": [v["word"] for v in value_words[:10]],
        "writing_structure": result.get("writing_structure", {}),
    }

    # ---- 风格特征 ----
    # LLM 分析优先，回退到规则引擎
    if llm_data and llm_data.get("style"):
        s = llm_data["style"]
        tone = s.get("tone", tone)
        stance = s.get("stance", stance)
        audience = s.get("audience", audience)
        if s.get("title_patterns"):
            title_patterns = {p: {"pct": 0} for p in s["title_patterns"]}
        if s.get("language_features"):
            _language_features = s["language_features"]
    
    if llm_data and llm_data.get("content_strategy"):
        cs = llm_data["content_strategy"]
        if cs.get("categories"):
            main_categories = [
                {"name": c["name"], "count": int(round(c["pct"] * stats.get("total", 0) / 100)), 
                 "pct": c["pct"], "avg_likes": stats.get("avg_likes", 0)}
                for c in cs["categories"][:6] if c.get("pct", 0) > 0
            ]
        if cs.get("core_opinions"):
            opinion = [{"sentence": o} for o in cs["core_opinions"]]
        if cs.get("value_words"):
            value_words = [{"word": w, "count": 0} for w in cs["value_words"]]

    style_features = {
        "tone": tone,
        "stance": stance,
        "audience": audience,
        "title_avg_length": avg_title_len,
        "title_patterns": title_patterns,
        "main_content_type": main_categories[0]["name"] if main_categories else "",
        "avg_engagement": {
            "likes": engagement["avg_likes"],
            "comments": engagement["avg_comments"],
            "collects": engagement["avg_collects"],
        },
        "topic_tags": [t["topic"] for t in topics[:8]],
        "value_words": [v["word"] for v in value_words[:8]],
    }

    account_name = result.get("account_name", "")
    platform = result.get("platform", "xhs")
    platform_label = "小红书" if platform == "xhs" else "抖音"

    # ---- 报告文本 ----
    report_lines = [
        f"╔══ 竞品账号分析报告：{account_name}",
        f"║ 📌 平台：{platform_label}",
        f"║ 📊 样本：{total} 篇内容 | 均赞 {engagement['avg_likes']:,} | 均藏 {engagement['avg_collects']:,}",
        f"║ 🔬 来源：blogger-distiller 数据分析引擎\n",
        "【📌 定位与基调】",
        f"  ▸ 目标受众：{audience}",
        f"  ▸ 情感基调：{tone}",
        f"  ▸ 语气立场：{stance}\n",
        "【✏️ 语言与文字】",
        f"  ▸ 标题平均长度：{avg_title_len}字",
        f"  ▸ 标题模式：{', '.join(title_patterns.keys()) if title_patterns else '多样'}\n",
        "【📋 内容策略】",
    ]
    for cat in main_categories[:5]:
        report_lines.append(f"  ▸ {cat['name']}: {cat['count']}篇 ({cat['pct']}%) · 均赞{cat['avg_likes']:,}")
    report_lines.append("")
    report_lines.append("【💬 互动表现】")
    report_lines.append(f"  ▸ 均赞 {engagement['avg_likes']:,} · 均评 {engagement['avg_comments']} · 均藏 {engagement['avg_collects']:,}")
    report_lines.append(f"  ▸ 藏赞比 {engagement['collected_rate']}（越高说明内容越实用）")
    report_lines.append("")
    report_lines.append("【🔥 高频话题】")
    for t in topics[:10]:
        report_lines.append(f"  ▸ #{t['topic']} ({t['frequency']}次)")
    report_lines.append("")
    report_lines.append("【🏆 高互动内容 TOP5】")
    for b in best_performers:
        report_lines.append(f"  ▸ [{b['likes']}赞] {b['title'][:50]}")
    report_lines.append("")
    report_lines.append("【🧠 认知层】")
    for o in cognitive["core_opinions"][:5]:
        report_lines.append(f"  ▸ \"{o[:120]}...\"")
    report_lines.append("")
    report_lines.append("【🏷️ 风格总结】")
    tags = f"{tone} · {stance} · {main_categories[0]['name'] if main_categories else '综合'}"
    report_lines.append(f"  ▸ {tags}")

    return {
        "report": "\n".join(report_lines),
        "四层风格分析": {
            "定位与基调": {"目标受众": audience, "情感基调": tone, "语气立场": stance},
            "语言与文字": {"标题平均长度": f"{avg_title_len}字", "标题模式": title_patterns},
            "表达与修辞": {"叙事逻辑": cognitive["writing_structure"], "观点句": cognitive["core_opinions"][:5]},
            "传播与适配": {"平台": platform_label},
        },
        "内容策略": {"types_distribution": {c["name"]: f"{c['pct']}%" for c in main_categories[:6]}},
        "互动表现": engagement,
        "高频话题": {"topics": topics[:10], "total_topics": len(topics)},
        "best_performers": best_performers,
        "认知层": cognitive,
        "suggested_tags": [tone, stance, main_categories[0]["name"] if main_categories else "综合"],
        "style_features": style_features,
        "raw_distiller_data": result.get("raw_data"),
    }


def _detect_title_patterns(titles: list) -> dict:
    patterns = {
        "数字型": r"\d+",
        "疑问型": r"[？?]|怎么|如何|为什么|什么|该不该|要不要",
        "感叹型": r"[！!]|绝了|太|真的|居然|太好|太绝",
        "教程型": r"教程|手把手|保姆级|步骤|方法|攻略|技巧|指南",
        "列表型": r"合集|盘点|推荐|必备|top|榜|清单|N个",
        "对比型": r"vs|对比|区别|差异|还是|哪个好",
        "故事型": r"我|亲身|经历|踩坑|分享|心得|回忆|那年",
        "悬念型": r"\.\.\.|…|竟然|没想到|万万|千万|警惕|小心",
        "痛点型": r"别再|不要|千万别|后悔|踩雷|避坑|当心|注意",
        "结果前置型": r"月入|涨了|减了|拿下|搞定|实现|学会|做到",
        "反常识型": r"颠覆|打破|原来|不是|骗|假的|误区|谣言|真相",
        "场景代入型": r"如果你|当你|假如|假设|每次|每次看到",
    }
    results = {}
    for name, regex in patterns.items():
        count = sum(1 for t in titles if re.search(regex, t))
        if count > 0:
            pct = round(count / len(titles) * 100, 1) if titles else 0
            results[name] = {"count": count, "pct": pct}
    return results


# ============================================================
# 对外接口
# ============================================================

def analyze_account(account_name: str, platform: str, posts: list = None, user_id: str = None, url: str = None, max_notes: int = 50, max_comments: int = 20, parallel_workers: int = 3) -> dict:
    """
    完整的竞品账号分析入口
    
    流程：
      1. 检查 TikHub Token → 无则引导加微信
      2. 检查 TikHub 余额 → 不足则引导充值
      3. 调 blogger-distiller → 产出报告
      4. 记录账单
    
    Args:
        account_name: 博主名
        platform: "xiaohongshu" / "douyin"
        posts: 保留参数
        user_id: 可选。直接指定 user_id 爬取
        url: 可选。用户提供的链接
        max_notes: 采集数量 30/50/80
    """
    # 检查权限
    status = check_tikhub_status()
    if not status["configured"]:
        return {
            "report": "🔒 竞品/对标账号分析需要开通权限\n\n"
                      "竞品分析使用 blogger-distiller 数据分析引擎，"
                      "通过 TikHub API 采集小红书/抖音公开数据进行深度分析。\n\n"
                      "📱 请添加微信 iodun001 开通分析权限",
            "needs_permission": True,
            "suggested_tags": [],
        }

    # 检查余额
    balance = check_tikhub_balance()
    if not balance.get("ok"):
        err_msg = balance.get("message", "余额检查失败")
        record_billing("竞品账号分析", account_name, platform, max_notes, get_cost_estimate(max_notes)["cost_display"], status="failed", error_message=err_msg)
        return {
            "report": f"❌ {err_msg}\n\n请联系微信 iodun001 充值后重试。",
            "credit_error": True,
            "suggested_tags": [],
        }

    # 运行 distiller
    cost_est = get_cost_estimate(max_notes)
    result = run_distiller(account_name, platform, max_notes, user_id=user_id, max_comments=max_comments, parallel_workers=parallel_workers)

    if result.get("error") or result.get("credit_error"):
        err_msg = result.get("message", "分析失败")
        record_billing("竞品账号分析", account_name, platform, max_notes, cost_est["cost_display"], status="failed", error_message=err_msg)
        return {
            "report": f"❌ {err_msg}",
            "error": err_msg,
            "suggested_tags": [],
        }

    # 构建报告
    # LLM 深度分析（替代关键词匹配）
    llm_data = {}
    if is_llm_available():
        try:
            notes = (result.get("raw_data") or {}).get("notes", [])
            stats = (result.get("raw_data") or {}).get("stats", {})
            tag_freq = (result.get("raw_data") or {}).get("tag_freq", [])
            profile = result.get("profile", {})
            print("  🤖 LLM 深度分析中...")
            llm_data = deep_analyze(profile, notes, stats, tag_freq)
        except Exception as e:
            print(f"  ⚠️ LLM 分析异常: {e}")
    
    report_data = build_report_from_distiller(result, llm_data=llm_data)
    
    # 记录账单（使用估算中间值作为实际费用）
    actual_cost = round((cost_est["cost_min"] + cost_est["cost_max"]) / 2, 2)
    billing = record_billing("竞品账号分析", account_name, platform, result.get("notes_count", max_notes), cost_est["cost_display"], actual_cost=actual_cost)
    
    billing_info = {
        "cost_display": cost_est["cost_display"],
        "actual_cost": actual_cost,
        "bill_id": billing.get("bill_id"),
    }
    report_data["billing"] = billing_info
    report_data["report"] += f"\n\n💰 本次分析费用：¥{actual_cost}（估算 {cost_est['cost_display']}）"
    
    # 导出到 账号分析/ 目录
    export_summary = export_account_analysis(
        result=result,
        report_text=report_data.get("report", ""),
        billing_info=billing_info,
        style_features=report_data.get("style_features"),
    )
    
    report_data["export_summary"] = export_summary
    report_data["full_analysis_data"] = result.get("raw_data", {})
    
    # 评论洞察分析（LLM 优先，回退到关键词引擎）
    full_data = result.get("raw_data", {})
    if llm_data and llm_data.get("comment_insight"):
        ci = llm_data["comment_insight"]
        comment_insight = {
            "sentiment": ci.get("sentiment", {}),
            "sentiment_label": ci.get("sentiment_label", "中性"),
            "pain_conclusions": [p.get("point", "") for p in ci.get("pain_points", [])],
            "need_conclusions": [n.get("need", "") for n in ci.get("user_needs", [])],
            "top_comments": [
                {"content": c.get("content", ""), "likes": c.get("likes", 0), 
                 "user": c.get("user", "读者")}
                for c in ci.get("notable_comments", [])[:5]
            ],
            "total_comment_count": sum(
                len(n.get("comment_list", [])) for n in (full_data.get("notes", []) or (full_data.get("top10") or []))
            ),
            "interaction_summary": ci.get("interaction_style", ""),
        }
        print(f"  ✅ LLM 评论洞察已应用")
    else:
        comment_insight = analyze_comments(full_data)
    report_data["comment_insight"] = comment_insight
    
    # 生成 HTML 报告
    export_dir = (export_summary or {}).get("export_dir", "")
    if export_dir:
        try:
            # 获取 profile 数据（从 result 中）
            distiller_profile = result.get("profile", {})
            html_path = generate_html_report(
                account_name=account_name,
                platform=platform,
                report_data=report_data,
                full_data=full_data,
                comment_insight=comment_insight,
                export_dir=export_dir,
                profile=distiller_profile,
            )
            report_data["html_report_path"] = html_path
            # 注册到报告注册表
            register_report(account_name, platform, html_path, export_dir)
            # 自动打开浏览器
            open_html_browser(html_path)
        except Exception as e:
            print(f"  ⚠️ 生成HTML报告失败: {e}")
    
    return report_data


# 兼容旧接口
def generate_analysis_report(account_name: str, platform: str, raw_data: dict) -> str:
    result = analyze_account(account_name, platform, raw_data.get("posts", []))
    return result.get("report", result.get("error", "未知错误"))


def extract_style_tags(report_text: str) -> list:
    return []


# ============================================================
# 报告注册表 — 支持"打开xxx的分析报告"
# ============================================================

_REPORT_REGISTRY_DB = os.path.join(os.path.join(os.path.dirname(__file__), "..", "data"), "report_registry.json")

def _ensure_report_registry():
    os.makedirs(os.path.dirname(_REPORT_REGISTRY_DB), exist_ok=True)
    if not os.path.exists(_REPORT_REGISTRY_DB):
        with open(_REPORT_REGISTRY_DB, "w", encoding="utf-8") as f:
            json.dump([], f)


def register_report(account_name: str, platform: str, html_path: str, export_dir: str):
    """将报告路径注册到注册表"""
    _ensure_report_registry()
    with open(_REPORT_REGISTRY_DB, "r", encoding="utf-8") as f:
        reports = json.load(f)
    # 去重：同账号同平台同日期不重复添加
    entry = {
        "account_name": account_name,
        "platform": platform,
        "html_path": html_path,
        "export_dir": export_dir,
        "created_at": datetime.now().isoformat(),
    }
    reports.append(entry)
    with open(_REPORT_REGISTRY_DB, "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)


def find_report(account_name: str) -> dict:
    """按账号名查找最近的报告"""
    _ensure_report_registry()
    if not os.path.exists(_REPORT_REGISTRY_DB):
        return None
    with open(_REPORT_REGISTRY_DB, "r", encoding="utf-8") as f:
        reports = json.load(f)
    # 模糊匹配 + 按时间倒序
    matches = [r for r in reports if account_name.lower() in r.get("account_name", "").lower()]
    if not matches:
        return None
    matches.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return matches[0]


def open_report(account_name: str) -> str:
    """打开指定账号的最新报告，返回状态消息"""
    report = find_report(account_name)
    if not report:
        return f"\u274c 未找到 {account_name} 的分析报告，请先进行竞品分析"
    html_path = report.get("html_path", "")
    if not html_path or not os.path.exists(html_path):
        return f"\u274c {account_name} 的HTML报告文件已丢失（{html_path}）"
    try:
        import subprocess as _sp
        import platform as _pf
        if _pf.system() == "Darwin":
            _sp.Popen(["open", html_path])
        else:
            _sp.Popen(["xdg-open", html_path])
        return f"\u2705 已打开 {account_name} 的分析报告"
    except Exception as e:
        return f"\u26a0\ufe0f 打开失败: {e}"




# ============================================================
# ============================================================
# 评论分析 + HTML 报告生成
# ============================================================

import collections
import html as _html_module
from datetime import datetime

# 情绪关键词
_POSITIVE_WORDS = {"好", "喜欢", "好看", "棒", "厉害", "优秀", "绝", "赞", "值得", "推荐", "神仙", "宝藏", "佩服", "牛逼", "太棒", "美", "帅", "精致", "高级", "大气", "绝绝子", "冲", "种草", "爱了", "yyds", "惊艳", "天花板", "封神", "满分", "无敌", "完美", "满意", "超出预期", "回购", "无限回购", "一生推", "强烈推荐", "必入", "必买", "惊喜", "期待", "太可", "太好", "绝美", "绝绝"}
_NEGATIVE_WORDS = {"差", "难", "不好", "不行", "失望", "踩雷", "后悔", "垃圾", "坑", "贵", "不值", "丑", "避雷", "上当", "黑心", "翻车", "浪费", "太坑", "糟心", "踩坑", "辣鸡", "智商税", "割韭菜", "虚假宣传", "鸡肋", "踩坑", "无力吐槽", "一生黑", "再也不会", "别买", "退退退", "冤大头", "亏了", "不值当", "慎入", "落差大", "照骗", "避而远之"}
_PAIN_KEYWORDS = {"怎么", "如何", "为什么", "怎么办", "求助", "救", "帮", "有没有", "有人", "求推荐", "求建议", "避雷", "踩坑", "后悔", "纠结", "难", "输", "错", "失败", "焦虑", "担心", "害怕", "迷茫", "困惑", "没用", "无效", "浪费"}
_NEED_KEYWORDS = {"想要", "希望", "求", "需要", "推荐", "建议", "有没有", "有人", "教", "方法", "技巧", "攻略", "教程", "怎么", "如何"}


def analyze_comments(full_analysis_data: dict) -> dict:
    top10 = full_analysis_data.get("top10", [])

    all_comments = []
    pain_hits = collections.defaultdict(list)
    need_hits = collections.defaultdict(list)
    author_reply_count = 0
    reader_comment_count = 0
    pos_count = 0
    neg_count = 0

    for note in top10:
        comment_list = note.get("comment_list", [])
        for c in comment_list:
            content = c.get("content", "").strip()
            likes = c.get("likes", 0)
            is_author = c.get("is_author", False)
            if not content:
                continue
            all_comments.append({"content": content, "likes": likes, "user": c.get("user", ""), "is_author": is_author})
            if not is_author:
                reader_comment_count += 1
            has_pos = any(w in content for w in _POSITIVE_WORDS)
            has_neg = any(w in content for w in _NEGATIVE_WORDS)
            if has_pos and not has_neg:
                pos_count += 1
            elif has_neg:
                neg_count += 1
            for kw in _PAIN_KEYWORDS:
                if kw in content:
                    pain_hits[kw].append(content[:80])
            for kw in _NEED_KEYWORDS:
                if kw in content:
                    need_hits[kw].append(content[:80])
            for sub in c.get("sub_comments", []):
                sub_content = sub.get("content", "").strip()
                sub_is_author = sub.get("is_author", False)
                if sub_content:
                    if sub_is_author:
                        author_reply_count += 1
                    all_comments.append({"content": sub_content, "likes": 0, "user": sub.get("user", ""), "is_author": sub_is_author})

    total = len(all_comments)
    neu_count = total - pos_count - neg_count

    pain_conclusions = []
    if pain_hits:
        sorted_pains = sorted(pain_hits.items(), key=lambda x: len(x[1]), reverse=True)
        for kw, examples in sorted_pains[:5]:
            count = len(examples)
            if kw in ("怎么", "如何"):
                pain_conclusions.append("用户普遍关注\u300c方法/操作\u300d问题（出现%d次），如如何解决特定场景难题" % count)
            elif kw in ("为什么",):
                pain_conclusions.append("用户频繁追问原因（出现%d次），对现象背后的逻辑有强烈求知欲" % count)
            elif kw in ("后悔", "踩坑", "避雷"):
                pain_conclusions.append("用户有踩坑/后悔经历（出现%d次），需要避坑指南和真实经验参考" % count)
            elif kw in ("焦虑", "担心", "害怕", "迷茫"):
                pain_conclusions.append("用户存在明显的焦虑/迷茫情绪（出现%d次），需要情感共鸣和方向指引" % count)
            elif kw in ("难", "失败", "输", "错"):
                pain_conclusions.append("用户面临挫折和困难（出现%d次），需要解决方案和心理支持" % count)
            elif kw in ("纠结",):
                pain_conclusions.append("用户在多个选择间纠结（出现%d次），需要决策参考和对比分析" % count)
            else:
                pain_conclusions.append("用户使用\u300c%s\u300d表达困扰（出现%d次）" % (kw, count))

    need_conclusions = []
    if need_hits:
        sorted_needs = sorted(need_hits.items(), key=lambda x: len(x[1]), reverse=True)
        for kw, examples in sorted_needs[:5]:
            count = len(examples)
            if kw in ("求", "想要", "希望"):
                need_conclusions.append("用户有明确的求助/索取需求（出现%d次），希望获得具体资源或方案" % count)
            elif kw in ("推荐", "建议"):
                need_conclusions.append("用户需要产品/内容推荐（出现%d次），依赖他人建议做决策" % count)
            elif kw in ("方法", "技巧", "攻略", "教程"):
                need_conclusions.append("用户渴求实操方法（出现%d次），需要可落地的步骤指南" % count)
            elif kw in ("教",):
                need_conclusions.append("用户希望被手把手教导（出现%d次），教程类内容需求旺盛" % count)
            elif kw in ("怎么", "如何"):
                need_conclusions.append("用户的核心需求是获取方法论（出现%d次），\u300c怎么做\u300d类内容最受欢迎" % count)
            else:
                need_conclusions.append("用户使用\u300c%s\u300d表达诉求（出现%d次）" % (kw, count))

    sorted_comments = sorted(all_comments, key=lambda x: x["likes"], reverse=True)
    top_comments = []
    seen = set()
    for c in sorted_comments:
        if c["content"] not in seen and len(top_comments) < 5:
            top_comments.append(c)
            seen.add(c["content"])

    reply_rate = round(author_reply_count / max(reader_comment_count, 1) * 100, 1)

    if pos_count >= neu_count and pos_count >= neg_count:
        sl = "正面"
    elif neg_count >= pos_count and neg_count >= neu_count:
        sl = "负面"
    else:
        sl = "中性"

    return {
        "sentiment": {"positive": pos_count, "neutral": neu_count, "negative": neg_count, "total": total},
        "pain_conclusions": pain_conclusions,
        "need_conclusions": need_conclusions,
        "pain_raw_count": len(pain_hits),
        "need_raw_count": len(need_hits),
        "top_comments": top_comments,
        "author_reply_rate": reply_rate,
        "total_comment_count": total,
        "sentiment_label": sl,
    }


def _sentiment_pct(sentiment: dict, key: str) -> float:
    total = sentiment.get("total", 0)
    if total == 0:
        return 0
    return round(sentiment.get(key, 0) / total * 100, 1)


def _build_category_html(category_stats: dict) -> str:
    if not category_stats:
        return '<div class="empty">暂无分类数据</div>'
    sorted_cats = sorted(category_stats.items(), key=lambda x: x[1].get("count", 0), reverse=True)
    colors = ["#6366f1", "#a855f7", "#ec4899", "#06b6d4", "#10b981", "#f59e0b"]
    parts = []
    for i, (name, info) in enumerate(sorted_cats):
        pct = info.get("pct", 0)
        count = info.get("count", 0)
        avg_likes = info.get("avg_likes", 0)
        top_note = info.get("top_note", "")
        color = colors[i % len(colors)]
        title_sample = ""
        if top_note:
            title_sample = " 例: " + _html_module.escape(top_note[:30])
        label = _html_module.escape(name)[:24]
        parts.append(
            '<div class="br">'
            '<div class="bl">%s</div>'
            '<div class="bt"><div class="bf" style="width:%d%%;background:%s">%s</div></div>'
            '<div class="bv">%d篇 均赞%s</div>'
            '</div>' % (label, pct, color, label, count, format(avg_likes, ','))
        )
    return '\n'.join(parts)


def _build_tags_html(tag_freq: list) -> str:
    if not tag_freq:
        return '<div class="empty">暂无话题标签</div>'
    tags = []
    for tag, count in tag_freq[:20]:
        tags.append('<span class="tg">#%s<span class="c">%d</span></span>' % (_html_module.escape(tag), count))
    rows = []
    for i in range(0, len(tags), 5):
        rows.append('<div style="margin:4px 0">' + ''.join(tags[i:i+5]) + '</div>')
    return '\n'.join(rows)


def _build_top_html(best_performers: list) -> str:
    if not best_performers:
        return '<div class="empty">暂无数据</div>'
    parts = []
    for i, p in enumerate(best_performers[:5]):
        rk = "rk%d" % (i+1) if i < 3 else ""
        title_raw = p.get("title", "") or p.get("desc", "")
        title = _html_module.escape(title_raw[:80]) if title_raw else "无标题"
        likes = int(p.get("likes", 0) or 0)
        comments = int(p.get("comments", 0) or 0)
        collects = int(p.get("collects", 0) or 0)
        parts.append(
            '<div class="ti">'
            '<span class="rk %s">%d</span><span class="tl">%s</span>'
            '<div class="im"><span>\u2764\ufe0f %s</span><span>\U0001f4ac %s</span><span>\U0001f4cc %s</span></div>'
            '</div>' % (rk, i+1, title, format(likes, ","), format(comments, ","), format(collects, ","))
        )
    return '\n'.join(parts)


def _build_sentiment_html(sentiment: dict) -> str:
    pos_pct = _sentiment_pct(sentiment, "positive")
    neu_pct = _sentiment_pct(sentiment, "neutral")
    neg_pct = _sentiment_pct(sentiment, "negative")
    pos_cnt = sentiment.get("positive", 0)
    neu_cnt = sentiment.get("neutral", 0)
    neg_cnt = sentiment.get("negative", 0)
    return (
        '<div class="emotion-bar">'
        '<div class="emotion-seg emotion-pos" style="width:%d%%">%d%%</div>'
        '<div class="emotion-seg emotion-neu" style="width:%d%%">%d%%</div>'
        '<div class="emotion-seg emotion-neg" style="width:%d%%">%d%%</div>'
        '</div>'
        '<div class="emotion-legend">'
        '<span><span class="dot" style="background:#10b981"></span>\u6b63\u9762 %d%%\uff08%d\u6761\uff09</span>'
        '<span><span class="dot" style="background:#9ca3af"></span>\u4e2d\u6027 %d%%\uff08%d\u6761\uff09</span>'
        '<span><span class="dot" style="background:#ef4444"></span>\u8d1f\u9762 %d%%\uff08%d\u6761\uff09</span>'
        '</div>'
        % (pos_pct, pos_pct, neu_pct, neu_pct, neg_pct, neg_pct,
           pos_pct, pos_cnt, neu_pct, neu_cnt, neg_pct, neg_cnt)
    )


def _build_title_patterns_html(patterns: dict) -> str:
    if not patterns:
        return '<span style="font-size:0.8em;color:#7c7c9a">\u6807\u9898\u6a21\u5f0f\u591a\u6837</span>'
    parts = []
    for name, info in patterns.items():
        pct = info.get("pct", 0)
        parts.append('<span class="tg">%s<span class="c">%d%%</span></span>' % (_html_module.escape(name), pct))
    if not parts:
        return ''
    return ' '.join(parts)


def _build_opinion_html(opinion: list) -> str:
    if not opinion:
        return '<div class="empty">\u6682\u65e0\u8ba4\u77e5\u5c42\u6570\u636e</div>'
    parts = []
    for o in opinion[:6]:
        sentence = o.get("sentence", "") if isinstance(o, dict) else str(o)
        parts.append('<span class="ot">\U0001f4a1 %s</span>' % _html_module.escape(sentence))
    return '<div class="tag-group">' + '\n'.join(parts) + '</div>'


def generate_html_report(account_name: str, platform: str, report_data: dict, full_data: dict, comment_insight: dict, export_dir: str, profile: dict = None) -> str:
    style = report_data.get("style_features", {})
    stats = full_data.get("stats", {})
    tag_freq = full_data.get("tag_freq", [])
    category_stats = full_data.get("category_stats", {})
    opinion = full_data.get("opinion_candidates", [])
    value_words = full_data.get("value_words", [])
    sentiment = comment_insight.get("sentiment", {})
    engagement = report_data.get("\u4e92\u52a8\u8868\u73b0", {})

    user_info = {}
    if profile:
        if platform == "xhs":
            basic = (profile.get("userBasicInfo") or profile.get("user") or {})
            # Try multiple field names for each attribute
            nickname = (basic.get("nickname") or profile.get("nickname") or 
                       profile.get("nickName") or profile.get("user_name") or account_name)
            desc_text = (basic.get("desc") or basic.get("description") or 
                        profile.get("desc") or profile.get("description") or "")
            fans_count = (basic.get("fans") or basic.get("fansCount") or basic.get("fans_count") or 
                         basic.get("followerCount") or basic.get("followers") or "")
            avatar = (basic.get("avatar") or basic.get("avatarUrl") or basic.get("headUrl") or
                     basic.get("head_img") or profile.get("avatar") or "")
            user_info = {
                "nickname": nickname,
                "desc": desc_text,
                "fans": fans_count,
                "avatar": avatar,
            }
        else:
            user = profile.get("user", {})
            nickname = (user.get("nickname") or profile.get("nickname") or 
                       profile.get("nickName") or account_name)
            desc_text = (user.get("description") or profile.get("description") or "")
            fans_count = (user.get("fans") or user.get("followerCount") or 
                         user.get("follower_count") or "")
            avatar = (user.get("avatar") or user.get("avatarLarger") or 
                     user.get("avatarThumb") or profile.get("avatar") or "")
            user_info = {
                "nickname": nickname,
                "desc": desc_text,
                "fans": fans_count,
                "avatar": avatar,
            }

    collect_rate = engagement.get("collected_rate", 0) if isinstance(engagement, dict) else 0
    pain_conclusions = comment_insight.get("pain_conclusions", [])
    need_conclusions = comment_insight.get("need_conclusions", [])

    category_html = _build_category_html(category_stats)
    tags_html = _build_tags_html(tag_freq)
    top_html = _build_top_html(report_data.get("best_performers", []))
    sentiment_html = _build_sentiment_html(sentiment)
    opinion_html = _build_opinion_html(opinion)
    title_patterns_html = _build_title_patterns_html(style.get("title_patterns", {}))

    pain_html_parts = []
    for c in pain_conclusions:
        pain_html_parts.append('<div class="insight-card pain"><div class="ic-label">😣 痛点发现</div><div class="ic-text">%s</div></div>' % _html_module.escape(c))
    pain_html = '\n'.join(pain_html_parts) if pain_html_parts else '<div class="empty">\u6682\u65e0\u8db3\u591f\u8bc4\u8bba\u6570\u636e\u63d0\u53d6\u75db\u70b9\u5206\u6790</div>'

    need_html_parts = []
    for c in need_conclusions:
        need_html_parts.append('<div class="insight-card need"><div class="ic-label">💪 需求发现</div><div class="ic-text">%s</div></div>' % _html_module.escape(c))
    need_html = '\n'.join(need_html_parts) if need_html_parts else '<div class="empty">\u6682\u65e0\u8db3\u591f\u8bc4\u8bba\u6570\u636e\u63d0\u53d6\u9700\u6c42\u5206\u6790</div>'

    top_cm_parts = []
    for c in comment_insight.get("top_comments", [])[:5]:
        top_cm_parts.append(
            '<div class="cm">'
            '<div class="cm-t">%s</div>'
            '<div class="cm-m">\u2764\ufe0f %s \u00b7 %s</div>'
            '</div>' % (_html_module.escape(c["content"][:120]), format(c.get("likes", 0), ","), _html_module.escape(c.get("user", "\u8bfb\u8005")))
        )
    top_cm_html = '\n'.join(top_cm_parts) if top_cm_parts else '<div class="empty">\u6682\u65e0\u8bc4\u8bba\u6570\u636e</div>'

    vw_parts = []
    for v in value_words[:10]:
        word = v if isinstance(v, str) else v.get("word", "")
        if word:
            vw_parts.append('<span class="ot">\U0001f3af %s</span>' % _html_module.escape(word))
    value_words_html = ('<div style="margin-top:10px"><div class="tag-group" style="margin-top:4px">' + ''.join(vw_parts) + '</div></div>') if vw_parts else ''

    fans_str = str(user_info.get("fans", "")) if user_info.get("fans") else "N/A"
    desc_str = _html_module.escape(user_info.get("desc", "")[:120]) if user_info.get("desc") else ""

    vars_dict = {
        "account_name": _html_module.escape(account_name),
        "real_nickname": _html_module.escape(user_info.get("nickname", account_name)),
        "platform": "\u5c0f\u7ea2\u4e66" if platform == "xhs" else "\u6296\u97f3",
        "avatar_url": _html_module.escape(user_info.get("avatar", "")),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "fans": fans_str,
        "desc": desc_str,
        "total_notes": str(stats.get("total", 0)),
        "avg_likes": format(stats.get("avg_likes", 0), ","),
        "avg_comments": format(stats.get("avg_comments", 0), ","),
        "avg_comments_note": "（API返回总数，已采集" + str(comment_insight.get("total_comment_count", 0)) + "条评论样本）",
        "avg_collects": format(stats.get("avg_collects", 0), ","),
        "total_comment_count": str(comment_insight.get("total_comment_count", 0)),
        "cost": str(report_data.get("billing", {}).get("actual_cost", "?") if isinstance(report_data.get("billing"), dict) else "?"),
        "audience": _html_module.escape(style.get("audience", "\u6cdb\u4eba\u7fa4")),
        "tone": _html_module.escape(style.get("tone", "\u4e2d\u6027")),
        "stance": _html_module.escape(style.get("stance", "\u4e2d\u6027\u53d9\u8ff0")),
        "title_avg_len": str(style.get("title_avg_length", 0)),
        "title_patterns_html": title_patterns_html,
        "category_html": category_html,
        "tags_html": tags_html,
        "top_html": top_html,
        "sentiment_html": sentiment_html,
        "sentiment_label": comment_insight.get("sentiment_label", "\u4e2d\u6027"),
        "pain_conclusions_html": pain_html,
        "need_conclusions_html": need_html,
        "top_cm_html": top_cm_html,
        "author_reply_rate": str(comment_insight.get("author_reply_rate", 0)),
        "collect_rate": str(collect_rate),
        "opinion_html": opinion_html,
        "value_words_html": value_words_html,
    }

    template_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "mcp", "blogger-distiller", "scripts", "report_template.html"),
        "/tmp/report_template.html",
    ]
    template = None
    for tp in template_paths:
        if os.path.exists(tp):
            with open(tp, "r", encoding="utf-8") as f:
                template = f.read()
            break

    if not template:
        print("  \u26a0\ufe0f HTML\u6a21\u677f\u672a\u627e\u5230")
        return ""

    html = template
    for key, val in vars_dict.items():
        html = html.replace("{{" + key + "}}", str(val))

    output_path = os.path.join(export_dir, "report.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print("  \U0001f310 HTML \u62a5\u544a: " + output_path)
    return output_path


def open_html_browser(html_path: str):
    """\u6253\u5f00 HTML \u6587\u4ef6\u5230\u9ed8\u8ba4\u6d4f\u89c8\u5668"""
    import subprocess as _sp
    import platform as _pf
    try:
        if _pf.system() == "Darwin":
            _sp.Popen(["open", html_path])
        elif _pf.system() == "Linux":
            _sp.Popen(["xdg-open", html_path])
        elif _pf.system() == "Windows":
            _sp.Popen(["start", html_path], shell=True)
    except Exception as e:
        print("  \u26a0\ufe0f \u65e0\u6cd5\u81ea\u52a8\u6253\u5f00\u6d4f\u89c8\u5668: " + str(e))
