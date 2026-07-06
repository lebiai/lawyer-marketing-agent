#!/usr/bin/env python3
import os

SEED_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "seed.db")
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge.db")

if not os.path.exists(SEED_PATH):
    print("⚠️ 种子数据库不存在，请运行 build-seed.py")
if not os.path.exists(DB_PATH):
    print("📝 个人知识库将在首次调用时自动创建")
