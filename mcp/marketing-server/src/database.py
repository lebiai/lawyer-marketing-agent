import sqlite3
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SEED_DB = os.path.join(DATA_DIR, "seed.db")
KNOWLEDGE_DB = os.path.join(DATA_DIR, "knowledge.db")
PROFILE_DB = os.path.join(DATA_DIR, "profile.db")

def init_databases():
    os.makedirs(DATA_DIR, exist_ok=True)
    _init_knowledge_db()
    _init_profile_db()

def _init_knowledge_db():
    conn = sqlite3.connect(KNOWLEDGE_DB)
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS content_samples (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            platform TEXT NOT NULL,
            account_name TEXT,
            content TEXT NOT NULL,
            embedding BLOB,
            features TEXT,
            tags TEXT,
            quality_score REAL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_cs_type ON content_samples(type);
        CREATE INDEX IF NOT EXISTS idx_cs_platform ON content_samples(platform);

        CREATE TABLE IF NOT EXISTS brand_profile (
            id INTEGER PRIMARY KEY,
            dimension TEXT NOT NULL,
            content TEXT NOT NULL,
            embedding BLOB,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS competitor_analysis (
            id INTEGER PRIMARY KEY,
            account_name TEXT NOT NULL,
            platform TEXT NOT NULL,
            analysis_type TEXT NOT NULL,
            report TEXT NOT NULL,
            embedding BLOB,
            raw_data TEXT,
            analyzed_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_ca_account ON competitor_analysis(account_name);

        CREATE TABLE IF NOT EXISTS my_articles (
            id INTEGER PRIMARY KEY,
            platform TEXT NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            embedding BLOB,
            style_ref INTEGER,
            published INTEGER DEFAULT 0,
            performance TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS hot_topics (
            id INTEGER PRIMARY KEY,
            platform TEXT NOT NULL,
            topic TEXT NOT NULL,
            description TEXT,
            heat_score REAL,
            trend TEXT,
            related_keywords TEXT,
            captured_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS personal_notes (
            id INTEGER PRIMARY KEY,
            title TEXT,
            content TEXT NOT NULL,
            embedding BLOB,
            tags TEXT,
            source TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS platform_rules (
            id INTEGER PRIMARY KEY,
            platform TEXT NOT NULL UNIQUE,
            rules TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()

def _init_profile_db():
    conn = sqlite3.connect(PROFILE_DB)
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS user_profile (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS conversation_logs (
            id INTEGER PRIMARY KEY,
            session_id TEXT NOT NULL,
            user_input TEXT NOT NULL,
            agent_response TEXT NOT NULL,
            skill_used TEXT,
            knowledge_refs TEXT,
            user_rating INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS billing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
            action TEXT NOT NULL,
            target TEXT NOT NULL,
            platform TEXT NOT NULL,
            notes_count INTEGER,
            estimated_cost TEXT,
            actual_cost REAL,
            status TEXT NOT NULL DEFAULT 'success',
            error_message TEXT
        );
        CREATE TABLE IF NOT EXISTS account_tags (
            account_name TEXT NOT NULL,
            platform TEXT NOT NULL,
            industry_tags TEXT DEFAULT '[]',
            location_tags TEXT DEFAULT '[]',
            sub_areas TEXT DEFAULT '[]',
            role_tag TEXT DEFAULT '',
            audience_tag TEXT DEFAULT '',
            tone_tag TEXT DEFAULT '',
            content_types TEXT DEFAULT '[]',
            tag_source TEXT DEFAULT '{}',
            confidence TEXT DEFAULT 'low',
            notes_count INTEGER DEFAULT 0,
            analyzed_at TEXT DEFAULT (datetime('now')),
            UNIQUE(account_name, platform)
        );
        CREATE INDEX IF NOT EXISTS idx_account_tags_industry ON account_tags(industry_tags);
        CREATE INDEX IF NOT EXISTS idx_account_tags_location ON account_tags(location_tags);

        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY,
            account_name TEXT NOT NULL,
            platform TEXT NOT NULL,
            analysis_type TEXT NOT NULL,
            analysis_data TEXT NOT NULL,
            raw_data_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_ar_account ON analysis_results(account_name);
    """)
    conn.commit()
    conn.close()

def get_conn(db_name: str) -> sqlite3.Connection:
    path = {"knowledge": KNOWLEDGE_DB, "profile": PROFILE_DB, "seed": SEED_DB}.get(db_name)
    if not path:
        raise ValueError(f"Unknown db: {db_name}")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn
