# 🧬 律师营销 AI Agent

> 个人创作者的垂直行业内容提效工具。基于 Codex Agent 创造规范构建。

一键安装后，通过自然语言对话即可完成：**风格学习 → 文案创作 → 多平台适配 → 视频生成 → 数据分析** 的完整工作流。

---

## 🚀 快速安装

在 Codex 桌面端新建 Thread，输入：

```
帮我安装 https://github.com/lebiai/lawyer-marketing-agent.git
```

`setup.mjs` 会自动完成：Python 依赖安装 → 向量模型下载 → 种子知识库构建。

---

## 🎯 核心能力

### 📝 风格学习
提供文案样本，自动提取语气、句式、emoji 密度等风格特征，存入知识库。

### ✍️ 文案创作
- 输入主题 → 生成 3 个方向供用户选择 → 展开写全文
- 支持小红书、抖音口播、公众号三种平台格式

### 🌐 多平台适配
同一篇内容自动适配不同平台格式，规则可配置。

### 🔥 热点追踪
基于 agent-reach 搜索律师行业热点，输出热点榜单 + 选题建议。

### 📊 竞品账号分析
从内容策略、风格特征、互动表现、高频话题四个维度分析对标账号。

### 🎬 视频生成提示词
将口播文案转为 AI 视频模型的提示词，支持：
- **镜头前口播模式**：自动分镜 + 表情管理建议
- **资料画面模式**：每个场景的画面建议

### 📈 数据分析
统计发文总数、平台分布、增长趋势。

### 🗓️ 内容排期
三种创作节奏模板（均衡/高频/聚焦），自动生成 4 周日历。

### 💬 评论助手
自动分类评论情绪，生成回复建议。

### 🏷️ 品牌一致性检查
检查文案是否符合品牌规范（语气、违禁词、关键词覆盖）。

### 📦 素材库
管理图片模板、视频片段、品牌色板等创作素材。

---

## 📂 项目结构

```
├── AGENTS.md                          # Agent 宪法
├── setup.mjs                          # 安装脚本
├── build-seed.py                      # 种子知识库构建
├── requirements.txt                   # Python 依赖
├── .codex/
│   ├── config.toml                    # MCP Server 注册
│   └── hooks.json                     # 生命周期钩子
├── mcp/marketing-server/
│   ├── src/
│   │   ├── server.py                  # JSON-RPC 入口（20个方法）
│   │   ├── embedding.py               # bge-base-zh-v1.5 向量引擎
│   │   ├── database.py                # 三库 8 张表
│   │   ├── search.py                  # 向量搜索
│   │   ├── hot_tracker.py             # 热点搜索策略
│   │   ├── platform_adapter.py        # 多平台转换
│   │   ├── competitor_analyzer.py     # 竞品分析
│   │   ├── video_prompt.py            # 视频提示词
│   │   ├── data_analyzer.py           # 数据统计
│   │   ├── scheduler.py               # 内容排期
│   │   ├── comment_assistant.py       # 评论助手
│   │   ├── brand_checker.py           # 品牌一致性检查
│   │   └── asset_library.py           # 素材库管理
│   └── data/seed.db                   # 种子知识库
├── .agents/skills/                    # 11 个技能定义
└── docs/
    ├── specs/                         # 设计文档
    └── plans/                         # 实施计划
```

---

## 🛠 技术栈

| 组件 | 技术 |
|------|------|
| Agent 框架 | Codex (AGENTS.md + Skills) |
| MCP Server | Python |
| 向量模型 | BAAI/bge-base-zh-v1.5 (768d) |
| 数据库 | SQLite (三库分离) |
| 热点搜索 | agent-reach |
| 平台规则 | JSON 可配置 |

---

## 📖 使用示例

```
用户：学习这个账号的风格，我发一段文案给你
Agent：已分析这段文案的风格特征：
       - 语气：专业严谨
       - 句式：短句为主
       - emoji密度：低
       - 开头方式：案例引入
       已存入知识库。

用户：帮我写一篇小红书笔记，主题是劳动仲裁流程
Agent：我准备了 3 个方向，你选一个：
       方向 A：「劳动仲裁不知道这些，你可能白跑一趟」
       方向 B：「被公司辞退？三步教你拿赔偿」
       方向 C：「劳动仲裁 vs 劳动监察，别搞混了」
       选好后我展开写全文。
```

---

## 📄 License

MIT
