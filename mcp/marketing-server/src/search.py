import numpy as np
from embedding import embed, cosine_similarity, vec_from_bytes
from database import get_conn

def search_knowledge(query: str, type_filter: str = None, platform_filter: str = None, top_k: int = 5):
    query_vec = embed(query)
    conn = get_conn("knowledge")
    results = []

    tables = ["content_samples", "my_articles", "brand_profile", "personal_notes"]
    for table in tables:
        cursor = conn.execute(f"SELECT * FROM {table}")
        for row in cursor.fetchall():
            if not row["embedding"]:
                continue
            vec = vec_from_bytes(row["embedding"])
            score = cosine_similarity(query_vec, vec)
            results.append({
                "table": table,
                "id": row["id"],
                "content": row["content"],
                "score": score,
                "metadata": {k: row[k] for k in row.keys() if k not in ("content", "embedding")}
            })

    conn.close()
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]

def search_analysis(query: str, top_k: int = 5):
    query_vec = embed(query)
    conn = get_conn("knowledge")
    results = []

    for table in ("competitor_analysis", "hot_topics"):
        cursor = conn.execute(f"SELECT * FROM {table}")
        for row in cursor.fetchall():
            if not row["embedding"]:
                continue
            vec = vec_from_bytes(row["embedding"])
            score = cosine_similarity(query_vec, vec)
            results.append({
                "table": table,
                "id": row["id"],
                "content": row["report"] if table == "competitor_analysis" else row["topic"],
                "score": score,
                "metadata": {k: row[k] for k in row.keys() if k not in ("report", "content", "topic", "embedding")}
            })

    conn.close()
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]
