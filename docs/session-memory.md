# 🧠 会话记忆 — 律师营销 Agent 完整上下文

> 记录时间：2026-07-06
> 会话目标：基于 AGENT-CREATION-SPEC.md 规范，构建律师营销 AI Agent

---

## 一、核心规范与架构

### 底层框架
- 遵循 **AGENT-CREATION-SPEC.md** 三层架构：AGENTS.md（宪法）→ Skills（能力）→ MCP Server（基础设施）
- 采用 **混合架构**（方案C）：核心 Agent + 可选 Skills，按需激活
- 定位：**个人创作者的垂直行业内容提效工具**，首版聚焦律师行业

### 三库分离
| 数据库 | 角色 | 版本管理 |
|--------|------|---------|
| seed.db | 公共行业知识（术语/模板/平台规则） | 纳入 git |
| knowledge.db | 个人知识（风格样本/文章/分析/热点/素材） | .gitignore |
| profile.db | 用户画像 + 对话日志 | .gitignore |

### 设计文档
- 设计文档：`docs/superpowers/specs/2026-07-06-marketing-agent-design.md`
- 实施计划：`docs/superpowers/plans/2026-07-06-marketing-agent-p0~p4.md`

---

## 二、项目结构

```
├── AGENTS.md                    # 营销宪法（律师版）
├── setup.mjs                    # 安装脚本
├── build-seed.py                # 种子知识库
├── requirements.txt             # Python 依赖
├── .codex/
│   ├── config.toml              # MCP Server 注册
│   └── hooks.json               # 生命周期钩子
├── mcp/marketing-server/src/
│   ├── server.py                # JSON-RPC 入口（22个方法）
│   ├── embedding.py             # bge-base-zh-v1.5 向量引擎（768d）
│   ├── database.py              # 三库 8 张表
│   ├── search.py                # 向量搜索
│   ├── style_analyzer.py        # [新] 四层风格分析（P0升级）
│   ├── hot_tracker.py           # 热点搜索策略（P1）
│   ├── platform_adapter.py      # 多平台转换（P1）
│   ├── competitor_analyzer.py   # 竞品分析（P2）
│   ├── video_prompt.py          # 视频提示词（P2）
│   ├── data_analyzer.py         # 数据统计（P3）
│   ├── scheduler.py             # 内容排期（P3）
│   ├── comment_assistant.py     # 评论助手（P3）
│   ├── brand_checker.py         # 品牌检查（P4）
│   └── asset_library.py         # 素材库（P4）
├── .agents/skills/              # 11 个 Skills
└── docs/
    ├── superpowers/specs/
    ├── superpowers/plans/
    └── session-memory.md        # ← 当前文件
```

---

## 三、MCP Server 22 个 RPC 方法

| 方法 | 来源 | 功能 |
|------|------|------|
| initialize | P0 | 启动 + 模型加载 |
| search_knowledge | P0 | 创作知识向量搜索 |
| search_analysis | P0 | 分析类知识搜索 |
| store_knowledge | P0 | 知识存储（7种表） |
| log_conversation | P0 | 对话记录 |
| get_user_profile | P0 | 用户画像获取 |
| get_platform_rule | P0 | 平台规则获取 |
| export_knowledge | P0 | 知识导出 |
| hot_track | P1 | 热点搜索策略 |
| adapt_platform | P1 | 多平台适配转换 |
| analyze_account | P2 | 竞品分析报告 |
| generate_video_prompt | P2 | 视频提示词生成 |
| get_video_templates | P2 | 视频模板获取 |
| get_content_stats | P3 | 数据统计 |
| analyze_performance | P3 | 效果分析 |
| generate_calendar | P3 | 内容排期生成 |
| get_schedule_templates | P3 | 排期模板获取 |
| suggest_reply | P3 | 评论回复建议 |
| analyze_sentiment | P3 | 评论情绪分析 |
| check_brand | P4 | 品牌一致性检查 |
| store_asset / search_assets / get_asset_stats | P4 | 素材库管理 |
| **analyze_style** | **P0升级** | **四层风格分析** |
| **compare_styles** | **P0升级** | **批量风格对比** |

---

## 四、11 个 Skills 清单

| Skill | 阶段 | 触发词 |
|-------|------|--------|
| 风格学习 | P0 | 学习这个账号的风格、分析这段文案 |
| 文案创作 | P0 | 帮我写一篇、生成文案 |
| 多平台适配 | P1 | 改成小红书版、适配成抖音 |
| 热点追踪 | P1 | 今天有什么热点、行业热点 |
| 竞品账号分析 | P2 | 分析这个账号、拆解XX |
| 视频生成提示词 | P2 | 做成视频、生成提示词 |
| 数据分析 | P3 | 看看数据、复盘报告 |
| 内容排期 | P3 | 做个排期、内容日历 |
| 评论助手 | P3 | 回复评论、评论情绪 |
| 品牌一致性检查 | P4 | 检查品牌一致性 |
| 素材库 | P4 | 存个素材、找素材 |

---

## 五、数据库 8 张表

### seed.db
- `industry_knowledge` — 行业知识（5条种子：小红书/抖音/公众号模板 + AIDA/FAB框架）
- `platform_rules` — 平台规则（小红书/抖音/公众号 各一份JSON配置）

### knowledge.db
- `content_samples` — 风格样本（含features结构化JSON）
- `brand_profile` — 品牌规范（tone/taboo/keywords 等维度）
- `competitor_analysis` — 竞品分析报告
- `my_articles` — 个人产出文章
- `hot_topics` — 热点追踪记录
- `personal_notes` — 创作灵感 + 素材库（通过source=asset:xxx区分）

### profile.db
- `user_profile` — 用户画像统计
- `conversation_logs` — 对话日志

---

## 六、关键设计决策

| 决策 | 结论 |
|------|------|
| 首版行业 | 律师行业 |
| 多平台适配规则 | 可配置 JSON，存 seed.db platform_rules 表 |
| 真实发布 API | 不接入，仅输出文案 |
| 硬件方案 | 语言=Python, 向量=bge-base-zh-v1.5, DB=SQLite |
| 风格学习方案 | 手动贴文案分析 |
| 文案创作流程 | 先出3个方向→用户选→展开写 |
| 热点追踪方案 | agent-reach, 主动触发 |
| 种子数据 | 5条行业知识 + 3平台规则 |

---

## 七、种子数据内容

### 行业知识（5条）
1. 律师小红书爆款标题公式（科普体/案例体/避坑体/对比体）
2. 律师抖音口播钩子模板（数字型/反问型/对比型/悬念型）
3. 律师公众号文章结构（科普类/热点评论类）
4. AIDA创作框架
5. FAB销售法则

### 平台规则（3份JSON）
- 小红书：title_max=20, emoji丰富, 图文分段, 话题标签
- 抖音：title_max=30, 3秒钩子, 口播格式, 15-60秒
- 公众号：title_max=64, 长文分段, 深度分析, 金句总结

---

## 八、风格分析器四层维度（最新升级）

详见 `style_analyzer.py`：

1. **定位与基调**：目标受众 / 核心目的 / 情感基调 / 语气立场
2. **语言与文字**：句式特征（句长分布/疑问比） / 用词风格 / 篇幅节奏 / 人称使用
3. **表达与修辞**：修辞手法 / 叙事逻辑 / 信息侧重 / 独特符号
4. **传播与适配**：适配平台 / 风格标签

分析结果以结构化 JSON 存入 `content_samples.features`，支持精确搜索匹配。

---

## 九、Git 提交历史

```
44ea338  feat: upgrade style analyzer to 4-dimension framework
e414eb8  docs: add README with install guide and feature overview
31c17c0  P4: add brand checker + asset library (project complete)
2f13383  P2: add competitor analyzer + video prompt generator
f3ef9e3  P1: add hot_tracker + platform_adapter modules
4f98b68  P3: add data analyzer + scheduler + comment assistant
6bf4332  P0: complete - fix vector search bug, add Skills, add design docs
5123edf  feat: add 4 core Skills
50f4ea9  feat: add MCP Server (Python) with vector search
9c6c5f7  feat: add project skeleton for lawyer marketing agent
```

---

## 十、仓库信息

- GitHub: `github.com/lebiai/lawyer-marketing-agent`
- 安装命令：`帮我安装 https://github.com/lebiai/lawyer-marketing-agent.git`

---

## 十一、竞品账号分析 V3 — blogger-distiller 集成（2026-07-06）

### 设计决策

| 决策 | 结论 |
|------|------|
| 分析引擎 | blogger-distiller（otter1101/blogger-distiller） |
| 安装方式 | setup.mjs 中 git clone --depth 1 到 mcp/blogger-distiller/ |
| 权限控制 | 首次使用时检查 TikHub Token → 无则引导加微信 iodun001 |
| 支持平台 | 小红书 + 抖音（distiller 原生支持） |
| 公众号 | 保留现有 keyword-based 分析 |
| 采集数量 | 30/50/80 三档，让用户选择 |
| 数据回流 | 全量存 competitor_analysis.raw_data + 风格特征存 content_samples |
| TikHub Token | 由管理员开通后配置，用户不自行注册 |

### 调用流程

```
用户"分析XX账号"
  → check_tikhub_status
  → 无 Token → "加微信 iodun001 开通"
  → 有 Token → crawl_blogger.py → analyze.py → 读 analysis.json
  → build_report_from_distiller() → 7维报告
  → store_knowledge(competitor_analysis) → store_knowledge(content_samples)
```

### 文件变更

- `setup.mjs` — 新增 blogger-distiller 克隆步骤
- `competitor_analyzer.py` — V3 重写，新增 check_tikhub_status/run_distiller
- `server.py` — 新增 check_tikhub_status RPC，更新 analyze_account 返回格式
- `SKILL.md` — 更新为权限门+7维框架
- `requirements.txt` — 新增 python-docx 依赖
