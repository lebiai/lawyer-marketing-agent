# 🧬 营销创作 AI Agent — 设计文档

> 基于 Codex Agent 创造规范（AGENT-CREATION-SPEC.md）设计的营销助手框架

---

## 一、产品定位

**个人创作者的垂直行业内容提效工具。**

核心价值主张：让一个创作者，以最小成本完成从灵感、分析、创作到发布的完整工作流。

**可配置维度：** 垂直行业（通过 seed.db + AGENTS.md 领域边界注入）

---

## 二、架构概览

### 2.1 三层架构

```
┌───────────────────────────────────────────────────────────────┐
│              第一层：行为规则层（AGENTS.md）                      │
│  职责边界、回答规则、知识闭环约束                                 │
├───────────────────────────────────────────────────────────────┤
│              第二层：能力层（Skills）                            │
│  必选：风格学习、文案创作、知识检索/归档                          │
│  可选：竞品分析、热点追踪、视频提示词、多平台适配、                 │
│        数据分析、内容排期、评论助手、品牌一致检查                   │
├───────────────────────────────────────────────────────────────┤
│              第三层：基础设施层（MCP Server）                     │
│  三库架构：seed.db（公共）+ knowledge.db（个人）+ profile.db（画像） │
└───────────────────────────────────────────────────────────────┘
```

### 2.2 混合架构优势

- **技能解耦：** 每个 Skill 独立维护，升级某个创作能力不影响整体
- **行业无关：** 替换 seed.db 即可切换到不同垂直行业
- **渐进增强：** 必选 Skills 保证最小可用，可选 Skills 按需激活

---

## 三、数据库设计

### 3.1 三库分离架构

```
┌──────────────────────────────────────────────┐
│              MCP Server 数据层                 │
│                                                │
│  seed.db（公共只读，纳入 git）                    │
│  ├─ industry_knowledge    ← 行业术语/模板/知识   │
│  └─ hot_topic_definitions ← 热搜分类/标签字典    │
│                                                │
│  knowledge.db（个人读写，.gitignore）             │
│  ├─ content_samples       ← 风格样本/爆款/金句   │
│  ├─ brand_profile         ← 品牌人设规范         │
│  ├─ competitor_analysis   ← 竞品分析报告         │
│  ├─ my_articles           ← 历史创作内容         │
│  ├─ hot_topics            ← 热点追踪记录         │
│  └─ personal_notes        ← 创作灵感/笔记        │
│                                                │
│  profile.db（个人读写，.gitignore）               │
│  ├─ user_profile          ← 画像统计数据         │
│  └─ conversation_logs     ← 对话历史             │
└──────────────────────────────────────────────┘
```

### 3.2 表结构定义

#### seed_db.industry_knowledge — 行业公共知识

```sql
CREATE TABLE industry_knowledge (
  id INTEGER PRIMARY KEY,
  type TEXT NOT NULL,           -- 'term' | 'template' | 'knowledge' | 'guideline'
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  embedding BLOB,               -- 768d (bge-base-zh-v1.5)
  source TEXT,
  tags TEXT,                    -- JSON array
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_ik_type ON industry_knowledge(type);
```

#### knowledge_db.content_samples — 风格样本库

```sql
CREATE TABLE content_samples (
  id INTEGER PRIMARY KEY,
  type TEXT NOT NULL,           -- 'title' | 'hook' | 'golden_sentence' | 'style_pattern' | 'full_article'
  platform TEXT NOT NULL,       -- 'xiaohongshu' | 'douyin' | 'wechat' | 'general'
  account_name TEXT,
  content TEXT NOT NULL,
  embedding BLOB,
  features JSON,                -- {tone, sentence_length, emoji_density, ...}
  tags TEXT,
  quality_score REAL DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_cs_type ON content_samples(type);
CREATE INDEX idx_cs_platform ON content_samples(platform);
```

#### knowledge_db.brand_profile — 人设/品牌规范

```sql
CREATE TABLE brand_profile (
  id INTEGER PRIMARY KEY,
  dimension TEXT NOT NULL,      -- 'tone' | 'visual_style' | 'core_values' | 'target_audience' | 'keywords' | 'taboo'
  content TEXT NOT NULL,
  embedding BLOB,
  is_active INTEGER DEFAULT 1,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);
```

#### knowledge_db.competitor_analysis — 竞品分析

```sql
CREATE TABLE competitor_analysis (
  id INTEGER PRIMARY KEY,
  account_name TEXT NOT NULL,
  platform TEXT NOT NULL,
  analysis_type TEXT NOT NULL,  -- 'overview' | 'content_strategy' | 'frequency' | 'engagement' | 'top_topics'
  report TEXT NOT NULL,
  embedding BLOB,
  raw_data JSON,
  analyzed_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_ca_account ON competitor_analysis(account_name);
```

#### knowledge_db.my_articles — 个人历史文案

```sql
CREATE TABLE my_articles (
  id INTEGER PRIMARY KEY,
  platform TEXT NOT NULL,
  title TEXT,
  content TEXT NOT NULL,
  embedding BLOB,
  style_ref INTEGER,            -- FK -> content_samples.id
  published INTEGER DEFAULT 0,
  performance JSON,             -- {likes, favorites, shares, comments, impressions}
  created_at TEXT DEFAULT (datetime('now'))
);
```

#### knowledge_db.hot_topics — 热点记录

```sql
CREATE TABLE hot_topics (
  id INTEGER PRIMARY KEY,
  platform TEXT NOT NULL,
  topic TEXT NOT NULL,
  description TEXT,
  heat_score REAL,
  trend TEXT,                   -- 'rising' | 'hot' | 'declining'
  related_keywords TEXT,        -- JSON array
  captured_at TEXT DEFAULT (datetime('now'))
);
```

#### knowledge_db.personal_notes — 创作灵感

```sql
CREATE TABLE personal_notes (
  id INTEGER PRIMARY KEY,
  title TEXT,
  content TEXT NOT NULL,
  embedding BLOB,
  tags TEXT,                    -- JSON array
  source TEXT,                  -- 'manual' | 'ai_suggestion' | 'hook_extracted'
  created_at TEXT DEFAULT (datetime('now'))
);
```

#### profile_db.user_profile — 用户画像

```sql
CREATE TABLE user_profile (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL           -- JSON value
);
-- 预置维度：
-- totalConversations: number
-- totalKnowledge: number
-- platformDistribution: Record<string, number>
-- topTopics: Array<{topic, count}>
-- topFormats: Array<{format, count}>
-- weeklyActivity: number
-- knowledgeGrowth: number
```

#### profile_db.conversation_logs — 对话日志

```sql
CREATE TABLE conversation_logs (
  id INTEGER PRIMARY KEY,
  session_id TEXT NOT NULL,
  user_input TEXT NOT NULL,
  agent_response TEXT NOT NULL,
  skill_used TEXT,
  knowledge_refs TEXT,          -- JSON array of referenced IDs
  user_rating INTEGER,
  created_at TEXT DEFAULT (datetime('now'))
);
```

### 3.3 搜索策略

MCP Server 提供两种 search 接口：

| 接口 | 搜索范围 | 使用场景 |
|------|---------|---------|
| `search_knowledge(query, type_filter, platform_filter)` | content_samples + my_articles + brand_profile + personal_notes | 创作时检索参考 |
| `search_analysis(query)` | competitor_analysis + hot_topics | 分析场景专用 |

---

## 四、Skills 定义

### 4.1 必选 Skills

#### Skill: 风格学习

| 项目 | 内容 |
|------|------|
| 触发词 | "学习这个账号的风格"、"帮我分析这个号" |
| 输入 | 目标账号URL或内容样本 |
| 工作流 | 抓取内容 → 提取风格特征 → 存入 content_samples → log_conversation |
| 特征维度 | 语气（严肃/幽默/亲切）、句式长度、emoji密度、开头方式、排版习惯 |

#### Skill: 文案创作

| 项目 | 内容 |
|------|------|
| 触发词 | "帮我写一篇……"、"生成一个文案" |
| 输入 | 主题、平台、参考风格 |
| 工作流 | search_knowledge → 风格匹配 → 生成 → store_knowledge(my_articles) → log_conversation |

#### Skill: 多平台适配

| 项目 | 内容 |
|------|------|
| 触发词 | "把这个改成小红书版"、"适配成抖音脚本" |
| 输入 | 源文案 + 目标平台 |
| 工作流 | 加载平台规则 → 格式转换 → 输出 → store_knowledge → log_conversation |

### 4.2 可选 Skills（MVP）

#### Skill: 热点追踪

| 项目 | 内容 |
|------|------|
| 触发词 | "今天有什么热点"、"追一下XX热点" |
| 工作流 | 联网搜索 → 过滤垂直行业关键词 → 输出热点榜单 → store_knowledge(hot_topics) → log_conversation |

#### Skill: 竞品账号分析

| 项目 | 内容 |
|------|------|
| 触发词 | "分析一下这个号"、"拆解XX账号" |
| 工作流 | 抓取内容 → 分析策略/频率/互动 → 生成报告 → store_knowledge(competitor_analysis) → log_conversation |

#### Skill: 视频生成提示词

| 项目 | 内容 |
|------|------|
| 触发词 | "把这个文案做成视频"、"生成视频提示词" |
| 工作流 | 读取文案 → 分镜拆分 → 生成提示词（镜头前口播 或 画面+旁白）→ log_conversation |

### 4.3 更后期添加的可选 Skills

| Skill | 说明 | 依赖 |
|-------|------|------|
| 数据分析 | 收录发布效果数据，生成复盘 | my_articles.performance 有数据 |
| 内容排期 | 生成发布日历 | my_articles 历史 + hot_topics |
| 评论助手 | 话术生成、情绪分析 | brand_profile（人设一致） |
| 品牌一致性检查 | 检查文案与品牌规范的匹配度 | brand_profile 已配置 |

---

## 五、知识自成长闭环

```
用户提问 → search_knowledge → 生成回答 → store_knowledge → log_conversation → 下次搜索能命中
```

### 归档策略

| 条件 | 是否存储 | 存储位置 |
|------|----------|---------|
| 用户要求分析对标账号 | ✅ 存储 | competitor_analysis |
| 用户完成一篇文案创作 | ✅ 存储 | my_articles |
| 用户标记某个内容为"好" | ✅ 存储 | content_samples（质量分高） |
| 用户仅口头咨询创作思路 | ❌ 不存储内容 | 仅 log_conversation |
| 闲聊/非营销问题 | ❌ 不存储 | 仅 log_conversation |

---

## 六、安装与分发

遵循 AGENT-CREATION-SPEC 的规范：

```
仓库结构
├── AGENTS.md
├── setup.mjs
├── .codex/
│   ├── config.toml
│   └── hooks.json
├── .agents/skills/
│   ├── 风格学习/SKILL.md
│   ├── 文案创作/SKILL.md
│   ├── 多平台适配/SKILL.md
│   └── （可选 Skills 目录）
├── mcp/marketing-server/
│   ├── src/
│   ├── data/
│   │   ├── seed.db         # 公共知识库（纳入 git）
│   │   └── knowledge.db    # 个人知识库（.gitignore）
│   │   └── profile.db      # 画像库（.gitignore）
│   └── scripts/
└── build-seed.mjs          # 种子数据构建脚本
```

---

## 七、MVP 路线图

| 阶段 | 内容 | 可交付 |
|------|------|--------|
| **P0** | 搭建框架 + 必选 Skills | 能跑通"风格学习→文案创作→归档"闭环 |
| **P1** | 热点追踪 + 多平台适配 | 能追热点并适配多平台格式 |
| **P2** | 竞品分析 + 视频提示词 | 能分析对手并生成视频 |
| **P3** | 数据分析 + 内容排期 + 评论助手 | 完整运营助手 |
| **P4** | 品牌一致性检查 + 素材库 | 品牌化管理 |

---

## 八、待验证问题

- [ ] 种子数据策略：seed.db 预先放哪些行业模板和术语？
- [ ] 第一版先覆盖哪个垂直行业做 demo？
- [ ] 多平台适配的"平台规则"是写死的模板还是可配置的？
- [ ] 热点追踪的联网搜索工具是哪个？（anysearch? web_search?）
- [ ] 是否需要对接真实发布 API（小程序/公众号等）？

---

## 九、设计决策（已确认）

| 问题 | 决策 |
|------|------|
| 第一版 demo 垂直行业 | **律师行业**，复用 AGENT-CREATION-SPEC 的行业知识 |
| 多平台适配规则 | **可配置**，规则从 seed.db 或独立配置文件中读取 |
| 真实发布 API | **不接入**，仅输出文案，由用户自行发布 |
