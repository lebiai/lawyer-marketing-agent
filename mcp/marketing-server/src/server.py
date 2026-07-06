#!/usr/bin/env python3
from hot_tracker import get_search_queries, HOT_TOPIC_SEARCHES
from platform_adapter import adapt_content
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
        queries = get_search_queries(industry)
        return {"jsonrpc": "2.0", "id": request_id, "result": {
            "search_queries": queries,
            "industry_terms": HOT_TOPIC_SEARCHES.get(industry, {}).get("industry_terms", []),
            "instruction": "请使用 agent-reach 搜索以上关键词，然后调用 filter_by_industry 筛选结果"
        }}

    elif method == "adapt_platform":
        content = params.get("content", "")
        source = params.get("source_platform", "general")
        target = params.get("target_platform", "xiaohongshu")
        from database import get_conn
        import json
        conn = get_conn("seed")
        cur = conn.execute("SELECT rules FROM platform_rules WHERE platform = ?", (target,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return {"jsonrpc": "2.0", "id": request_id, "result": {"error": f"No rules for platform: {target}"}}
        rules = json.loads(row["rules"])
        result = adapt_content(content, source, target, rules)
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
