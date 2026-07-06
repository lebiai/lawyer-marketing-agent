# 营销创作 Agent — P0 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建律师营销 AI Agent 的基础框架，跑通「风格学习 → 文案创作 → 归档」完整闭环

**Architecture:** 三层架构：AGENTS.md（行为规则）+ Skills（创作的领域能力）+ MCP Server（Python + SQLite + bge-base-zh-v1.5 向量搜索）。混合架构，必选 Skills 保证闭环，可选按需激活。

**Tech Stack:** Python 3.10+, sentence-transformers, sqlite3 (built-in), bge-base-zh-v1.5, agent-reach (hot topics), JSON 规则配置

---

### Task 1: 创建项目骨架

**Files:**
- Create: `AGENTS.md`
- Create: `setup.mjs`
- Create: `.codex/config.toml`
- Create: `.codex/hooks.json`
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `build-seed.py`

- [ ] **Step 1: 创建 `AGENTS.md`**

```markdown
# 律师营销 AI 助手 — 工作规范

## 核心原则
- 只回答与律师行业内容创作相关的问题
- 非领域问题一律不回答，回复：「我是律师营销助手，专注于帮助律师创作者完成内容创作、账号分析、热点追踪等工作。无法回答此问题，请提出营销创作相关的问题。」
- 回答必须引用已有知识库内容或联网搜索结果
- 每次交互后必须执行 store_knowledge + log_conversation

## 首次使用引导
用户第一次使用时，回复：
「🎯 我是你的律师营销助手。我可以帮你：
1. 📝 学习对标账号的风格
2. ✍️ 撰写小红书/抖音/公众号文案
3. 🌐 多平台内容适配
4. 🔥 追踪行业热点
5. 📊 分析竞品账号

直接告诉我你的需求开始吧！」

## 文案创作
### 流程：
1. 收到主题 → 生成 3 个方向让用户选择
2. 用户选定方向 → 检索知识库匹配风格
3. 根据所选平台规则生成完整文案
4. 调用 store_knowledge(my_articles)
5. 调用 log_conversation

## 风格学习
### 流程：
1. 用户提供文案样本
2. 提取风格特征（语气、句式、emoji密度、开头方式）
3. 存入 content_samples
4. 调用 log_conversation

## 多平台适配
### 流程：
1. 读取平台规则（JSON 配置文件）
2. 按规则转换格式
3. 输出适配后的文案
4. 调用 store_knowledge
5. 调用 log_conversation

## 回答前：搜索知识库
必须调用 search_knowledge 搜索已有知识。
禁止直接 sqlite3 查询 database。

## 回答后：归档知识
两步操作，缺一不可：
1. 调用 store_knowledge — 存储提炼后的知识点
2. 调用 log_conversation — 记录交互（用于用户画像）

## 自动更新
知识库在每次 Thread 启动时自动检查更新。

## 安装指引
- 仓库：GitHub 地址待定
- 安装命令：「帮我安装 https://github.com/用户/律师营销助手」
```

- [ ] **Step 2: 创建 `setup.mjs`**

```javascript
#!/usr/bin/env node
import { execSync } from 'child_process';
import { existsSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

console.log('🚀 正在安装律师营销助手...\n');

console.log('📦 检查 Python...');
const pythonVer = execSync('python3 --version', { encoding: 'utf-8' }).trim();
console.log(`   ✅ ${pythonVer}`);

console.log('📦 安装 Python 依赖...');
execSync('pip3 install -r requirements.txt', { cwd: __dirname, stdio: 'inherit' });

console.log('📦 预下载嵌入模型 bge-base-zh-v1.5...');
execSync('python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer(\'BAAI/bge-base-zh-v1.5\')"', { stdio: 'inherit' });

console.log('📦 构建种子知识库...');
execSync('python3 build-seed.py', { cwd: __dirname, stdio: 'inherit' });

console.log('\n✅ 安装完成！');
console.log('📋 按以下步骤使用：');
console.log('   1. 在 Codex 中创建新 Thread');
console.log('   2. 开始使用（如："学习这个账号的风格"）');
```

- [ ] **Step 3: 创建 `.codex/config.toml`**

```toml
[project]
name = "lawyer-marketing-agent"
version = "0.1.0"

[mcp_servers.marketing_server]
command = "python3"
args = ["mcp/marketing-server/src/server.py"]
env = { PYTHONPATH = "${PROJECT_DIR}/mcp/marketing-server/src" }
```

- [ ] **Step 4: 创建 `.codex/hooks.json`**

```json
{
  "on_thread_start": [
    {
      "type": "command",
      "command": "python3",
      "args": ["mcp/marketing-server/scripts/check-update.py"]
    }
  ]
}
```

- [ ] **Step 5: 创建 `.gitignore`**

```
knowledge.db
profile.db
__pycache__/
*.pyc
.env
dist/
node_modules/
.venv/
```

- [ ] **Step 6: 创建 `requirements.txt`**

```
sentence-transformers>=2.2.0
numpy>=1.24.0
```

- [ ] **Step 7: 创建 `build-seed.py`**

```python
#!/usr/bin/env python3
"""构建种子知识库 seed.db"""
import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "mcp/marketing-server/data/seed.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.executescript("""
CREATE TABLE IF NOT EXISTS industry_knowledge (
  id INTEGER PRIMARY KEY,
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  embedding BLOB,
  source TEXT,
  tags TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_ik_type ON industry_knowledge(type);

CREATE TABLE IF NOT EXISTS platform_rules (
  id INTEGER PRIMARY KEY,
  platform TEXT NOT NULL UNIQUE,
  rules TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now'))
);
""")

seeds = [
    ("template", "律师小红书爆款标题公式",
     "【律师科普体】「XX罪/XX纠纷，不知道这些你就亏大了」\n【案例体】「因为XX，她/他赔了XX万」\n【避坑体】「律师告诉你，XX千万别做」\n【对比体】「XX和XX的区别，90%的人不知道」",
     "律师创作经验", '["标题","小红书","爆款"]'),
    ("template", "律师抖音口播钩子模板",
     "开场3秒钩子：\n1. 数字型：「XX万赔偿，他只做对了一件事」\n2. 反问型：「你以为XX就没事了？」\n3. 对比型：「同一件事，有人赔钱有人赚钱」\n4. 悬念型：「XX案件最新判例，颠覆你的认知」",
     "律师创作经验", '["抖音","口播","钩子"]'),
    ("template", "律师公众号文章结构",
     "【科普类】\n一、问题引入（真实案例/热点）\n二、法律分析（法条+解读）\n三、实操建议（行动指南）\n四、总结金句\n\n【热点评论类】\n一、热点事件回顾\n二、法律视角解读\n三、对普通人的启示\n四、互动引导",
     "律师创作经验", '["公众号","文章结构"]'),
    ("term", "AIDA创作框架",
     "Attention（引起注意）→ Interest（激发兴趣）→ Desire（唤起欲望）→ Action（促成行动）。适用于营销文案的经典漏斗框架。",
     "营销经典", '["框架","写作","营销"]'),
    ("term", "FAB销售法则",
     "Feature（特点）→ Advantage（优势）→ Benefit（利益）。先陈述事实特点，再说明对比优势，最后落到对用户的好处。",
     "营销经典", '["框架","写作","销售"]'),
]

cursor.executemany(
    "INSERT INTO industry_knowledge (type, title, content, source, tags) VALUES (?, ?, ?, ?, ?)", seeds
)

platform_rules = [
    ("xiaohongshu", json.dumps({
        "title_max_length": 20,
        "title_style": "吸引眼球，多用数字和疑问句",
        "body_style": "图文分段，每段2-4行，emoji丰富",
        "structure": ["标题", "正文段落", "话题标签"],
        "features": ["emoji_density_high", "段落分明", "视觉友好"],
        "taboo": ["硬广词汇", "绝对化表述"]
    }, ensure_ascii=False)),
    ("douyin", json.dumps({
        "title_max_length": 30,
        "title_style": "简短有力，开场即钩子",
        "body_style": "口播脚本格式，含镜头提示",
        "structure": ["3秒开场钩子", "正文铺陈", "互动引导"],
        "video_length": "15-60秒",
        "features": ["开场即高潮", "语言口语化", "节奏紧凑"],
        "taboo": ["长句", "专业术语堆砌"]
    }, ensure_ascii=False)),
    ("wechat", json.dumps({
        "title_max_length": 64,
        "title_style": "信息量大，兼顾吸引力和权威感",
        "body_style": "长文分段，可插入小标题",
        "structure": ["标题", "导语/引言", "正文分节", "金句总结", "互动引导"],
        "features": ["信息密度高", "有深度", "结构清晰"],
        "taboo": ["口语化过度"]
    }, ensure_ascii=False)),
]

cursor.executemany(
    "INSERT INTO platform_rules (platform, rules) VALUES (?, ?)", platform_rules
)

conn.commit()
conn.close()
print(f"✅ 种子数据库已创建：{DB_PATH}")
```

---

### Task 2: 构建 MCP Server（Python）

**Files:**
- Create: `mcp/marketing-server/src/__init__.py`
- Create: `mcp/marketing-server/src/embedding.py`
- Create: `mcp/marketing-server/src/database.py`
- Create: `mcp/marketing-server/src/search.py`
- Create: `mcp/marketing-server/src/server.py`
- Create: `mcp/marketing-server/scripts/check-update.py`

- [ ] **Step 1: 创建 `__init__.py`**

空文件，使目录成为 Python 包。

- [ ] **Step 2: 创建 `mcp/marketing-server/src/embedding.py`**

```python
import numpy as np
from sentence_transformers import SentenceTransformer

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("BAAI/bge-base-zh-v1.5")
    return _model

def embed(text: str) -> bytes:
    model = get_model()
    vec = model.encode(text, normalize_embeddings=True)
    return vec.astype(np.float32).tobytes()

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))
```

- [ ] **Step 3: 创建 `mcp/marketing-server/src/database.py`**

```python
import sqlite3
import json
import os
import numpy as np

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
```

- [ ] **Step 4: 创建 `mcp/marketing-server/src/search.py`**

```python
import numpy as np
from .embedding import embed, cosine_similarity
from .database import get_conn

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
            vec = np.frombuffer(row["embedding"], dtype=np.float32)
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
            vec = np.frombuffer(row["embedding"], dtype=np.float32)
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
```

- [ ] **Step 5: 创建 `mcp/marketing-server/src/server.py`**

```python
#!/usr/bin/env python3
import json
import sys
from .database import init_databases
from .embedding import embed, get_model
from .search import search_knowledge, search_analysis

def handle_request(request):
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")

    if method == "initialize":
        init_databases()
        model_info = get_model()
        return {
            "jsonrpc": "2.0", "id": request_id,
            "result": {"server_name": "marketing-server", "model": str(model_info), "vector_dim": 768, "status": "ready"}
        }
    elif method == "search_knowledge":
        results = search_knowledge(params.get("query", ""), params.get("type_filter"), params.get("platform_filter"), params.get("top_k", 5))
        return {"jsonrpc": "2.0", "id": request_id, "result": results}
    elif method == "search_analysis":
        results = search_analysis(params.get("query", ""), params.get("top_k", 5))
        return {"jsonrpc": "2.0", "id": request_id, "result": results}
    elif method == "store_knowledge":
        from .database import get_conn
        conn = get_conn("knowledge")
        table = params.get("table")
        data = params.get("data", {})
        content = data.get("content", "")
        vec = embed(content)

        if table == "content_samples":
            conn.execute("INSERT INTO content_samples (type, platform, content, embedding, features, tags) VALUES (?, ?, ?, ?, ?, ?)",
                (data.get("type"), data.get("platform"), content, vec,
                 json.dumps(data.get("features", {}), ensure_ascii=False),
                 json.dumps(data.get("tags", []), ensure_ascii=False)))
        elif table == "my_articles":
            conn.execute("INSERT INTO my_articles (platform, title, content, embedding, style_ref) VALUES (?, ?, ?, ?, ?)",
                (data.get("platform"), data.get("title"), content, vec, data.get("style_ref")))
        elif table == "brand_profile":
            conn.execute("INSERT INTO brand_profile (dimension, content, embedding) VALUES (?, ?, ?)",
                (data.get("dimension"), content, vec))
        elif table == "competitor_analysis":
            conn.execute("INSERT INTO competitor_analysis (account_name, platform, analysis_type, report, embedding, raw_data) VALUES (?, ?, ?, ?, ?, ?)",
                (data.get("account_name"), data.get("platform"), data.get("analysis_type"),
                 content, vec, json.dumps(data.get("raw_data", {}), ensure_ascii=False)))
        elif table == "hot_topics":
            conn.execute("INSERT INTO hot_topics (platform, topic, description, heat_score, trend, related_keywords) VALUES (?, ?, ?, ?, ?, ?)",
                (data.get("platform"), data.get("topic"), data.get("description"),
                 data.get("heat_score"), data.get("trend"),
                 json.dumps(data.get("related_keywords", []), ensure_ascii=False)))
        elif table == "personal_notes":
            conn.execute("INSERT INTO personal_notes (title, content, embedding, tags, source) VALUES (?, ?, ?, ?, ?)",
                (data.get("title"), content, vec,
                 json.dumps(data.get("tags", []), ensure_ascii=False), data.get("source")))
        conn.commit()
        conn.close()
        return {"jsonrpc": "2.0", "id": request_id, "result": {"status": "ok"}}
    elif method == "log_conversation":
        from .database import get_conn
        conn = get_conn("profile")
        conn.execute("INSERT INTO conversation_logs (session_id, user_input, agent_response, skill_used, knowledge_refs) VALUES (?, ?, ?, ?, ?)",
            (params.get("session_id"), params.get("user_input"), params.get("agent_response"),
             params.get("skill_used"), json.dumps(params.get("knowledge_refs", []))))
        conn.commit()
        conn.close()
        return {"jsonrpc": "2.0", "id": request_id, "result": {"status": "ok"}}
    elif method == "get_user_profile":
        from .database import get_conn
        conn = get_conn("profile")
        cursor = conn.execute("SELECT key, value FROM user_profile")
        profile = {row["key"]: json.loads(row["value"]) for row in cursor.fetchall()}
        conn.close()
        return {"jsonrpc": "2.0", "id": request_id, "result": profile}
    elif method == "get_platform_rule":
        from .database import get_conn
        conn = get_conn("seed")
        cursor = conn.execute("SELECT rules FROM platform_rules WHERE platform = ?", (params.get("platform"),))
        row = cursor.fetchone()
        conn.close()
        return {"jsonrpc": "2.0", "id": request_id, "result": json.loads(row["rules"]) if row else None}
    elif method == "export_knowledge":
        data = {}
        for db_name in ("knowledge", "profile"):
            conn = get_conn(db_name)
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            for table_row in cursor.fetchall():
                table = table_row["name"]
                rows = conn.execute(f"SELECT * FROM {table}").fetchall()
                data[f"{db_name}.{table}"] = [dict(r) for r in rows]
            conn.close()
        return {"jsonrpc": "2.0", "id": request_id, "result": data}
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}

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
            print(json.dumps({"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}}), flush=True)

if __name__ == "__main__":
    main()
```

- [ ] **Step 6: 创建 `mcp/marketing-server/scripts/check-update.py`**

```python
#!/usr/bin/env python3
import os

SEED_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "seed.db")
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge.db")

if not os.path.exists(SEED_PATH):
    print("⚠️ 种子数据库不存在，请运行 build-seed.py")
if not os.path.exists(DB_PATH):
    print("📝 个人知识库将在首次调用时自动创建")
```

---

### Task 3: 风格学习 Skill

**Files:**
- Create: `.agents/skills/风格学习/SKILL.md`

- [ ] **Step 1: 创建 `风格学习/SKILL.md`**

```markdown
---
name: 风格学习
description: 当用户说「学习这个账号的风格」「分析这段文案的风格」「帮我学一下这个」时执行
---

# 风格学习

当用户提供文案样本时执行。

## 工作流

```
Step 1: 提取风格特征
  - 语气：严肃/幽默/亲切/专业/犀利
  - 句式特点：长句/短句/混合
  - emoji密度：高/中/低
  - 开头方式：提问/陈述/案例/数据
  - 排版习惯：分段/不分段/列表/引用

Step 2: 计算 embedding → 存入 content_samples
Step 3: 调用 log_conversation
```

## 输出格式

```
════════════════════════════════
📋 风格分析报告
════════════════════════════════

一、语气风格 ✔
  [识别结果]

二、句式特点 ✔
  [识别结果]

三、emoji密度 ✔
  [密度等级 + 示例]

四、开头方式 ✔
  [识别结果]

五、排版习惯 ✔
  [识别结果]
════════════════════════════════
```

## ⚠️ 自查清单
- [ ] 是否提取了至少 4 个风格维度
- [ ] 是否调用了 store_knowledge
- [ ] 是否调用了 log_conversation
```

---

### Task 4: 文案创作 Skill

**Files:**
- Create: `.agents/skills/文案创作/SKILL.md`

- [ ] **Step 1: 创建 `文案创作/SKILL.md`**

```markdown
---
name: 文案创作
description: 当用户说「帮我写一篇XX平台的文案」「生成一篇关于XX的文章」「写个小红书笔记」时执行
---

# 文案创作

## 工作流

```
Step 1: 搜索知识库 → 匹配风格样本
Step 2: 生成 3 个方向让用户选择
        方向 A：[标题1]
        方向 B：[标题2]
        方向 C：[标题3]
Step 3: 用户选定方向
Step 4: 按所选平台规则生成完整文案
Step 5: 调用 store_knowledge(my_articles)
Step 6: 调用 log_conversation
```

## 输出格式

用户选择前：
```
════════════════════════════════
📋 【主题】创作方向
════════════════════════════════

方向 A：📌 [标题]
  [一句话说明切入角度]

方向 B：📌 [标题]
  [一句话说明切入角度]

方向 C：📌 [标题]
  [一句话说明切入角度]

请选择一个方向，我继续展开写全文。
════════════════════════════════
```

用户选定后：
```
════════════════════════════════
📝 [标题]
════════════════════════════════

[完整文案内容]
════════════════════════════════
```

## ⚠️ 自查清单
- [ ] 是否先生成了 3 个方向
- [ ] 是否检索了风格知识库
- [ ] 是否按所选平台规则输出
- [ ] 是否调用了 store_knowledge
- [ ] 是否调用了 log_conversation
```

---

### Task 5: 多平台适配 Skill

**Files:**
- Create: `.agents/skills/多平台适配/SKILL.md`

- [ ] **Step 1: 创建 `多平台适配/SKILL.md`**

```markdown
---
name: 多平台适配
description: 当用户说「把这个改成小红书版」「适配成抖音脚本」「转成公众号文章」时执行
---

# 多平台适配

## 工作流

```
Step 1: 调用 get_platform_rule(目标平台)
Step 2: 按规则转换文案格式
Step 3: 输出适配后的文案
Step 4: 调用 store_knowledge(my_articles)
Step 5: 调用 log_conversation
```

## 平台规则摘要

### 🟥 小红书
- 标题 20 字以内，多用数字和疑问句
- 图文分段，每段 2-4 行
- emoji 丰富
- 结尾加话题标签

### 🎵 抖音口播
- 3 秒开场钩子
- 口语化，节奏紧凑
- 时长 15-60 秒
- 结尾引导互动

### 🟩 公众号
- 标题信息量大
- 正文分段加小标题
- 有深度分析
- 结尾金句总结

## ⚠️ 自查清单
- [ ] 是否读取了目标平台的规则
- [ ] 输出是否符合平台格式要求
- [ ] 是否调用了 store_knowledge
- [ ] 是否调用了 log_conversation
```

---

### Task 6: 热点追踪 Skill

**Files:**
- Create: `.agents/skills/热点追踪/SKILL.md`

- [ ] **Step 1: 创建 `热点追踪/SKILL.md`**

```markdown
---
name: 热点追踪
description: 当用户说「今天有什么热点」「最近律师行业有什么热点」时执行
---

# 热点追踪

## 工作流

```
Step 1: 使用 agent-reach 搜索律师行业热点
Step 2: 筛选与律师创作相关的热点
Step 3: 输出热点榜单 + 选题建议
Step 4: 调用 store_knowledge(hot_topics)
Step 5: 调用 log_conversation
```

## 输出格式

```
════════════════════════════════
🔥 律师行业热点追踪
════════════════════════════════

🔥 热点 1：[标题]
  [简介]
  📈 热度：高/中/低
  📌 适合：小红书/抖音/公众号
  💡 选题建议：[建议]

🔥 热点 2：[标题]
  ...
════════════════════════════════
```

## ⚠️ 自查清单
- [ ] 是否调用了 agent-reach 搜索
- [ ] 是否筛选了与行业相关的热点
- [ ] 是否给出了选题建议
- [ ] 是否调用了 store_knowledge
- [ ] 是否调用了 log_conversation
```

---

### Task 7: 验证 P0 闭环

- [ ] **Step 1: 启动 MCP Server**
  ```
  python3 mcp/marketing-server/src/server.py
  ```
  预期：等待标准输入，无报错

- [ ] **Step 2: 测试 initialize**
  输入：`{"jsonrpc":"2.0","method":"initialize","id":1}`
  预期：返回 status: ready

- [ ] **Step 3: 测试 store_knowledge（存入风格样本）**
  输入：`{"jsonrpc":"2.0","method":"store_knowledge","params":{"table":"content_samples","data":{"type":"style_pattern","platform":"xiaohongshu","content":"律师告诉你，XX千万别做","features":{"tone":"警示","sentence_length":"短句"},"tags":["普法","标题"]}},"id":2}`

- [ ] **Step 4: 测试 search_knowledge（搜索能命中）**
  输入：`{"jsonrpc":"2.0","method":"search_knowledge","params":{"query":"律师普法标题","top_k":3},"id":3}`
  预期：返回刚才存入的样本，score > 0

- [ ] **Step 5: 测试 get_platform_rule**
  输入：`{"jsonrpc":"2.0","method":"get_platform_rule","params":{"platform":"xiaohongshu"},"id":4}`
  预期：返回小红书配置 JSON

- [ ] **Step 6: 测试 log_conversation**
  输入：`{"jsonrpc":"2.0","method":"log_conversation","params":{"session_id":"test-1","user_input":"帮我写个小红书普法笔记","agent_response":"...","skill_used":"文案创作","knowledge_refs":[1,3]},"id":5}`
  预期：返回 status: ok

- [ ] **Step 7: 完整运行 setup.mjs**
  ```
  node setup.mjs
  ```
  预期：无报错，输出安装完成提示
