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
from datetime import datetime
from search_candidates import search_blogger_candidates

# ============================================================
# 项目路径
# ============================================================

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_DISTILLER_DIR = os.path.join(_PROJECT_ROOT, "mcp", "blogger-distiller")
_DISTILLER_SCRIPTS = os.path.join(_DISTILLER_DIR, "scripts")
_DISTILLER_DATA = os.path.join(_DISTILLER_DIR, "data")


# ============================================================
# TikHub 状态检查
# ============================================================

_CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".xiaohongshu", "tikhub_config.json")


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


def run_distiller(account_name: str, platform: str, max_notes: int = 50, user_id: str = None) -> dict:
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
    crawl_cmd = [
        "python3", crawl_script,
        account_name,
        "-o", data_dir,
        "--max-notes", str(max_notes),
        "--platform", plat,
    ]
    if user_id:
        crawl_cmd.extend(["--user-id", user_id])

    print(f"📡 正在采集 {account_name} 的 {max_notes} 篇内容，约需 30-45 分钟...")
    result = subprocess.run(crawl_cmd, capture_output=True, text=True, cwd=_DISTILLER_DIR)
    if result.returncode != 0:
        error_msg = result.stderr or result.stdout or "未知错误"
        return {"error": True, "message": f"采集失败: {error_msg[:200]}"}

    # ---- Phase 2: 数据分析 ----
    safe_name = safe_filename(account_name)
    details_file = os.path.join(data_dir, f"{safe_name}_notes_details.json")

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

    return {
        "error": False,
        "account_name": account_name,
        "platform": plat,
        "data_dir": data_dir,
        "analysis_file": analysis_file,
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

def build_report_from_distiller(result: dict) -> dict:
    """
    将 distiller 的分析结果转为我们的 6维报告格式+风格特征
    """
    stats = result.get("stats", {})
    category_stats = result.get("category_stats", {})
    tag_freq = result.get("tag_freq", [])
    top10 = result.get("top10", [])
    opinion = result.get("opinion_candidates", [])
    value_words = result.get("value_words", [])

    # ---- 定位与基调（从观点句中推断） ----
    tone = "中性"
    stance = "中性叙述"
    audience = "泛人群"
    opinion_text = " ".join(c["sentence"] for c in opinion[:20])
    if opinion_text:
        if any(w in opinion_text for w in ["必须", "一定", "绝不", "警告", "警惕"]):
            tone = "犀利直白"
        elif any(w in opinion_text for w in ["温暖", "别怕", "没关系", "一起"]):
            tone = "温暖治愈"
        elif any(w in opinion_text for w in ["数据", "研究", "分析", "从法律"]):
            tone = "理性客观"
        if any(w in opinion_text for w in ["我觉得", "我认为", "我的"]):
            stance = "朋友分享"
        elif any(w in opinion_text for w in ["记住", "千万", "注意", "法律规定"]):
            stance = "权威指导"

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

    # ---- 风格特征（用于存入 content_samples） ----
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
        report_lines.append(f"  ▸ \"{o[:60]}...\"")
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
        "疑问型": r"[？?]|怎么|如何|为什么|什么",
        "感叹型": r"[！!]|绝了|太|真的|居然",
        "教程型": r"教程|手把手|保姆级|步骤|方法|攻略",
        "列表型": r"合集|盘点|推荐|必备|top|榜",
        "对比型": r"vs|对比|区别|差异|还是",
        "故事型": r"我|亲身|经历|踩坑|分享|心得",
        "悬念型": r"\.\.\.|…|竟然|没想到|万万|千万",
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

def analyze_account(account_name: str, platform: str, posts: list = None, user_id: str = None) -> dict:
    """
    完整的竞品账号分析入口
    
    流程：
      1. 检查 TikHub Token
      2. 无 Token → 返回引导信息
      3. 有 Token → 调 blogger-distiller → 产出报告
    
    Args:
        account_name: 博主名
        platform: "xiaohongshu" / "douyin"
        posts: 保留参数，未使用
        user_id: 可选。由 search_blogger_candidates 选定后传入
    """
    # 检查权限
    status = check_tikhub_status()
    if not status["configured"]:
        return {
            "report": "🔒 竞品/对标账号分析需要开通权限\n\n"
                      "竞品分析使用 blogger-distiller 数据分析引擎，"
                      "通过 TikHub API 采集小红书/抖音公开数据进行深度分析。\n\n"
                      "📱 请添加微信 iodun001 开通分析权限\n"
                      "开通后可分析任意小红书/抖音博主的内容策略、风格特征、互动数据。",
            "needs_permission": True,
            "suggested_tags": [],
        }

    # 运行 distiller（可选指定 user_id 跳过搜索阶段）
    max_notes = 50  # 默认
    result = run_distiller(account_name, platform, max_notes, user_id=user_id)

    if result.get("error"):
        return {
            "report": f"❌ 分析失败：{result.get('message', '未知错误')}\n\n请检查：\n1. 博主名是否正确\n2. 网络连接是否正常\n3. 联系微信 iodun001",
            "error": result.get("message", ""),
            "suggested_tags": [],
        }

    # 构建报告
    report_data = build_report_from_distiller(result)
    return report_data


# 兼容旧接口
def generate_analysis_report(account_name: str, platform: str, raw_data: dict) -> str:
    result = analyze_account(account_name, platform, raw_data.get("posts", []))
    return result.get("report", result.get("error", "未知错误"))


def extract_style_tags(report_text: str) -> list:
    return []
