#!/usr/bin/env python3
from hot_tracker import get_search_strategy, analyze_hot_topics, get_content_suggestions, get_historical_trends, check_search_tools, get_search_instruction
from platform_adapter import adapt_content as adapt_content_platform
from competitor_analyzer import check_tikhub_status, analyze_account, open_report, search_accounts_by_tags, store_analysis_result
from search_candidates import search_blogger_candidates
from account_link import parse_account_link, get_cost_estimate
from video_prompt import generate_video_prompt, generate_templates
from data_analyzer import get_content_stats, analyze_performance
from scheduler import generate_calendar, get_templates
from comment_assistant import suggest_reply, analyze_sentiment
from brand_checker import check_brand_consistency, suggest_improvements
from asset_library import store_asset, search_assets, get_asset_stats, get_categories
from style_analyzer import analyze_style, compare_styles
from copywriter import generate_outline, adapt_across_platforms, get_platform_kpi, get_all_platforms_summary, initialize_platform_rules
import json
import sys
import os
# Ensure this directory is on the path for direct script execution
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_databases
from embedding import embed, embed_to_bytes, get_model
from search import search_knowledge, search_analysis

def handle_request(request):
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")

    if method == "initialize":
        init_databases()
        model_info = get_model()
        # 初始化平台规则种子数据
        try:
            initialize_platform_rules()
        except Exception:
            pass
        return {
            "jsonrpc": "2.0", "id": request_id,
            "result": {
                "server_name": "marketing-server",
                "model": str(model_info),
                "vector_dim": 768,
                "status": "ready"
            }
        }

    elif method == "search_knowledge":
        results = search_knowledge(
            params.get("query", ""),
            params.get("type_filter"),
            params.get("platform_filter"),
            params.get("top_k", 5)
        )
        return {"jsonrpc": "2.0", "id": request_id, "result": results}

    elif method == "search_analysis":
        results = search_analysis(
            params.get("query", ""),
            params.get("top_k", 5)
        )
        return {"jsonrpc": "2.0", "id": request_id, "result": results}

    elif method == "store_knowledge":
        from database import get_conn as get_knowledge_conn
        conn = get_knowledge_conn("knowledge")
        table = params.get("table")
        data = params.get("data", {})
        content = data.get("content", "")
        vec = embed_to_bytes(content)

        if table == "content_samples":
            conn.execute(
                "INSERT INTO content_samples (type, platform, content, embedding, features, tags) VALUES (?, ?, ?, ?, ?, ?)",
                (data.get("type"), data.get("platform"), content, vec,
                 json.dumps(data.get("features", {}), ensure_ascii=False),
                 json.dumps(data.get("tags", []), ensure_ascii=False))
            )
        elif table == "my_articles":
            conn.execute(
                "INSERT INTO my_articles (platform, title, content, embedding, style_ref) VALUES (?, ?, ?, ?, ?)",
                (data.get("platform"), data.get("title"), content, vec, data.get("style_ref"))
            )
        elif table == "brand_profile":
            conn.execute(
                "INSERT INTO brand_profile (dimension, content, embedding) VALUES (?, ?, ?)",
                (data.get("dimension"), content, vec)
            )
        elif table == "competitor_analysis":
            conn.execute(
                "INSERT INTO competitor_analysis (account_name, platform, analysis_type, report, embedding, raw_data) VALUES (?, ?, ?, ?, ?, ?)",
                (data.get("account_name"), data.get("platform"), data.get("analysis_type"),
                 content, vec, json.dumps(data.get("raw_data", {}), ensure_ascii=False))
            )
        elif table == "hot_topics":
            conn.execute(
                "INSERT INTO hot_topics (platform, topic, description, heat_score, trend, related_keywords) VALUES (?, ?, ?, ?, ?, ?)",
                (data.get("platform"), data.get("topic"), data.get("description"),
                 data.get("heat_score"), data.get("trend"),
                 json.dumps(data.get("related_keywords", []), ensure_ascii=False))
            )
        elif table == "personal_notes":
            conn.execute(
                "INSERT INTO personal_notes (title, content, embedding, tags, source) VALUES (?, ?, ?, ?, ?)",
                (data.get("title"), content, vec,
                 json.dumps(data.get("tags", []), ensure_ascii=False), data.get("source"))
            )
        conn.commit()
        conn.close()
        return {"jsonrpc": "2.0", "id": request_id, "result": {"status": "ok"}}

    elif method == "log_conversation":
        from database import get_conn as get_profile_conn
        conn = get_profile_conn("profile")
        conn.execute(
            "INSERT INTO conversation_logs (session_id, user_input, agent_response, skill_used, knowledge_refs) VALUES (?, ?, ?, ?, ?)",
            (params.get("session_id"), params.get("user_input"), params.get("agent_response"),
             params.get("skill_used"), json.dumps(params.get("knowledge_refs", [])))
        )
        conn.commit()
        conn.close()
        return {"jsonrpc": "2.0", "id": request_id, "result": {"status": "ok"}}

    elif method == "get_user_profile":
        from database import get_conn as get_profile_conn2
        conn = get_profile_conn2("profile")
        cursor = conn.execute("SELECT key, value FROM user_profile")
        profile = {row["key"]: json.loads(row["value"]) for row in cursor.fetchall()}
        conn.close()
        return {"jsonrpc": "2.0", "id": request_id, "result": profile}

    elif method == "get_platform_rule":
        from database import get_conn as get_seed_conn
        conn = get_seed_conn("seed")
        cursor = conn.execute(
            "SELECT rules FROM platform_rules WHERE platform = ?",
            (params.get("platform"),)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"jsonrpc": "2.0", "id": request_id, "result": json.loads(row["rules"])}
        return {"jsonrpc": "2.0", "id": request_id, "result": None}

    elif method == "export_knowledge":
        data = {}
        for db_name in ("knowledge", "profile"):
            from database import get_conn as get_export_conn
            conn = get_export_conn(db_name)
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            for table_row in cursor.fetchall():
                table = table_row["name"]
                rows = conn.execute(f"SELECT * FROM {table}").fetchall()
                items = []
                for r in rows:
                    d = dict(r)
                    d.pop("embedding", None)
                    items.append(d)
                data[f"{db_name}.{table}"] = items
            conn.close()
        return {"jsonrpc": "2.0", "id": request_id, "result": data}

    elif method == "hot_track":
        industry = params.get("industry", "lawyer")
        result = get_search_strategy(industry)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "analyze_topics":
        raw = params.get("raw_topics", [])
        industry = params.get("industry", "lawyer")
        result = analyze_hot_topics(raw, industry)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "get_content_suggestions":
        topic = params.get("topic", {})
        result = get_content_suggestions(topic)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "get_trends":
        days = params.get("days", 30)
        result = get_historical_trends(days)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    elif method == "adapt_platform":
        content = params.get("content", "")
        source = params.get("source_platform", "general")
        target = params.get("target_platform", "xiaohongshu")
        result = adapt_content_platform(content, source, target)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "search_blogger_candidates":
        keyword = params.get("keyword", "")
        platform = params.get("platform", "xhs")
        result = search_blogger_candidates(keyword, platform)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "check_tikhub_status":
        return {"jsonrpc": "2.0", "id": request_id, "result": check_tikhub_status()}

    elif method == "open_report":
        account_name = params.get("account_name", "")
        msg = open_report(account_name)
        return {"jsonrpc": "2.0", "id": request_id, "result": {"message": msg}}

    elif method == "parse_account_link":
        url = params.get("url", "")
        result = parse_account_link(url)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "get_cost_estimate":
        notes = params.get("max_notes", 50)
        result = get_cost_estimate(notes)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "analyze_account":
        account = params.get("account_name", "")
        platform = params.get("platform", "")
        max_notes = params.get("max_notes", 50)
        max_comments = params.get("max_comments", 20)
        parallel_workers = params.get("parallel_workers", 3)
        user_id = params.get("user_id", None)
        url = params.get("url", None)
        result = analyze_account(account, platform, user_id=user_id, url=url, max_notes=max_notes, max_comments=max_comments, parallel_workers=parallel_workers)
        
        if result.get("needs_permission"):
            return {"jsonrpc": "2.0", "id": request_id, "result": {
                "report": result["report"],
                "needs_permission": True,
                "suggested_tags": [],
            }}
        
        export_summary = result.get("export_summary", {})
        analysis_data = result.get("full_analysis_data", {})

        # 构建媒体摘要
        media_summary = {}
        if export_summary:
            media_summary = {
                "export_dir": export_summary.get("export_dir", ""),
                "content_count": export_summary.get("content_count", 0),
                "total_images": export_summary.get("total_images", 0),
                "total_videos": export_summary.get("total_videos", 0),
            }

        return {"jsonrpc": "2.0", "id": request_id, "result": {
            "report": result.get("report", ""),
            "四层风格分析": result.get("四层风格分析", {}),
            "内容策略": result.get("内容策略", {}),
            "互动表现": result.get("互动表现", {}),
            "高频话题": result.get("高频话题", {}),
            "认知层": result.get("认知层", {}),
            "best_performers": result.get("best_performers", []),
            "suggested_tags": result.get("suggested_tags", []),
            "style_features": result.get("style_features", {}),
            "export_summary": media_summary,
            "full_analysis_data": analysis_data,
            "comment_insight": result.get("comment_insight", {}),
            "html_report_path": result.get("html_report_path", ""),
            "data_completeness": result.get("data_completeness", {}),
            "account_tags": result.get("account_tags", {}),
            "storage": {
                "table": "competitor_analysis",
                "data": {
                    "account_name": account,
                    "platform": platform,
                    "analysis_type": "full",
                    "report": result.get("report", ""),
                    "raw_data": analysis_data,
                }
            }
        }}

    elif method == "search_accounts_by_tags":
        results = search_accounts_by_tags(
            industry=params.get("industry"),
            location=params.get("location"),
            keyword=params.get("keyword"),
            platform=params.get("platform"),
            limit=params.get("limit", 10),
        )
        return {"jsonrpc": "2.0", "id": request_id, "result": results}

    elif method == "generate_video_prompt":
        script = params.get("script", "")
        mode = params.get("mode", "live")
        result = generate_video_prompt(script, mode)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "get_video_templates":
        templates = generate_templates()
        return {"jsonrpc": "2.0", "id": request_id, "result": templates}

    elif method == "get_content_stats":
        days = params.get("days", 30)
        stats = get_content_stats(days)
        return {"jsonrpc": "2.0", "id": request_id, "result": stats}

    elif method == "analyze_performance":
        articles = params.get("articles", [])
        result = analyze_performance(articles)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "generate_calendar":
        template = params.get("template", "balanced")
        start = params.get("start_date")
        calendar = generate_calendar(template, start)
        return {"jsonrpc": "2.0", "id": request_id, "result": calendar}

    elif method == "get_schedule_templates":
        templates = get_templates()
        return {"jsonrpc": "2.0", "id": request_id, "result": templates}

    elif method == "suggest_reply":
        comment = params.get("comment", "")
        category = params.get("category")
        result = suggest_reply(comment, category)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "analyze_sentiment":
        comments = params.get("comments", [])
        result = analyze_sentiment(comments)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "check_brand":
        content = params.get("content", "")
        platform = params.get("platform")
        result = check_brand_consistency(content, platform)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "suggest_improvements":
        content = params.get("content", "")
        platform = params.get("platform", "xiaohongshu")
        result = suggest_improvements(content, platform)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "store_asset":
        result = store_asset(
            params.get("name", ""),
            params.get("category", "other"),
            params.get("description", ""),
            params.get("tags")
        )
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "search_assets":
        result = search_assets(params.get("query"), params.get("category"))
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "get_asset_stats":
        result = get_asset_stats()
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "get_asset_categories":
        result = get_categories()
        return {"jsonrpc": "2.0", "id": request_id, "result": result}


    elif method == "analyze_style":
        text = params.get("text", "")
        account = params.get("account_name")
        result = analyze_style(text, account)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "compare_styles":
        samples = params.get("samples", [])
        result = compare_styles(samples)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}


    elif method == "generate_outline":
        topic = params.get("topic", "")
        platform = params.get("platform", "xiaohongshu")
        tone = params.get("tone")
        result = generate_outline(topic, platform, tone)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "adapt_cross_platform":
        content = params.get("content", "")
        source = params.get("source_platform", "wechat")
        target = params.get("target_platform", "xiaohongshu")
        result = adapt_across_platforms(content, source, target)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "get_platform_kpi":
        platform = params.get("platform", "xiaohongshu")
        result = get_platform_kpi(platform)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "get_all_platforms":
        result = get_all_platforms_summary()
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    elif method == "check_search_tools":
        result = check_search_tools()
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "get_search_instruction":
        industry = params.get("industry", "lawyer")
        result = get_search_instruction(industry)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}


    elif method == "store_analysis_result":
        account_name = params.get("account_name", "")
        platform = params.get("platform", "")
        analysis_data = params.get("analysis_data", {})
        result = store_analysis_result(account_name, platform, analysis_data)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}


    return {"jsonrpc": "2.0", "id": request_id, "error": {
        "code": -32601, "message": f"Method not found: {method}"
    }}

def main():
    init_databases()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            print(json.dumps(response, ensure_ascii=False), flush=True)
        except Exception as e:
            print(json.dumps({
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)}
            }), flush=True)

if __name__ == "__main__":
    main()
