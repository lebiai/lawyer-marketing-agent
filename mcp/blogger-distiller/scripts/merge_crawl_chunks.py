"""merge_crawl_chunks.py — 合并多个 chunk 的详情文件为一个完整的 notes_details.json

用法：
    python merge_crawl_chunks.py <output_dir> <safe_name> --chunks chunk_1.json chunk_2.json chunk_3.json
"""
import os
import sys
import json
import argparse


def merge_chunks(output_dir, safe_name, chunk_files):
    """合并多个 chunk 文件，去重后写入 output_dir/{safe_name}_notes_details.json"""
    merged = {}
    duplicates = 0
    for cf in chunk_files:
        if not os.path.exists(cf):
            print(f"  ⚠️ chunk 文件不存在: {cf}")
            continue
        with open(cf, "r", encoding="utf-8") as f:
            items = json.load(f)
        for item in items:
            feed_id = item.get("_feed_id", "")
            if not feed_id:
                continue
            if feed_id in merged:
                duplicates += 1
            merged[feed_id] = item

    details = list(merged.values())
    output_path = os.path.join(output_dir, f"{safe_name}_notes_details.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(details, f, ensure_ascii=False, indent=2)

    print(f"\n📦 合并完成: {len(details)} 条（去重 {duplicates} 条重复）")
    print(f"💾 输出: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="合并多个 crawl chunk 的详情文件")
    parser.add_argument("output_dir", help="输出目录")
    parser.add_argument("safe_name", help="安全文件名前缀")
    parser.add_argument("--chunks", nargs="+", required=True, help="chunk 文件列表")
    args = parser.parse_args()

    merge_chunks(args.output_dir, args.safe_name, args.chunks)


if __name__ == "__main__":
    main()
