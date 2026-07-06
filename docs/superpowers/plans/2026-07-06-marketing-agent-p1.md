# 营销创作 Agent — P1 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现热点追踪（对接 agent-reach）和多平台适配的可配置化转换逻辑

**Architecture:** Python MCP Server 扩展 + SKILL.md 细化

---

### Task 1: 热点追踪 — 对接 agent-reach 实现联网搜索

**Files:**
- Modify: `mcp/marketing-server/src/server.py`
- Create: `mcp/marketing-server/src/hot_tracker.py`

- [ ] **Step 1: 创建 `hot_tracker.py`**

```python
"""热点追踪模块 — 定义搜索策略和热点分析逻辑"""

HOT_TOPIC_SEARCHES = {
    "lawyer": {
        "keywords": [
            "律师 热点 新闻",
            "法律 新规 最新",
            "律师行业 趋势",
            "律师事务所 营销",
            "法律科普 热门"
        ],
        "industry_terms": [
            "民法典", "诉讼法", "合同纠纷", "劳动争议",
            "知识产权", "婚姻法", "继承法", "侵权责任"
        ]
    }
}

# 未来可扩展其他行业
# "medical": { ... }
# "finance": { ... }

def get_search_queries(industry: str = "lawyer") -> list:
    """获取该行业的热点搜索关键词列表"""
    config = HOT_TOPIC_SEARCHES.get(industry, HOT_TOPIC_SEARCHES["lawyer"])
    return config["keywords"]

def filter_by_industry(topics: list, industry: str = "lawyer") -> list:
    """筛选与行业相关的热点"""
    config = HOT_TOPIC_SEARCHES.get(industry, HOT_TOPIC_SEARCHES["lawyer"])
    terms = config["industry_terms"]
    filtered = []
    for topic in topics:
        title = (topic.get("title", "") + topic.get("description", "")).lower()
        if any(term in title for term in terms):
            filtered.append(topic)
    return filtered
```

- [ ] **Step 2: 在 server.py 中添加 `hot_track` 方法**

```python
# 在 handle_request 中添加：
elif method == "hot_track":
    industry = params.get("industry", "lawyer")
    from hot_tracker import get_search_queries, filter_by_industry
    # 返回搜索策略，Codex agent 会用 agent-reach 执行搜索
    return {"jsonrpc": "2.0", "id": request_id, "result": {
        "search_queries": get_search_queries(industry),
        "industry_terms": HOT_TOPIC_SEARCHES.get(industry, {}).get("industry_terms", []),
        "instruction": "请使用 agent-reach 搜索以上关键词，然后调用 filter_by_industry 筛选结果"
    }}
```

### Task 2: 热点追踪 — 细化 SKILL.md

**Files:**
- Modify: `.agents/skills/热点追踪/SKILL.md`

- [ ] **Step 1: 更新 SKILL.md 加入 agent-reach 的详细调用格式**

在现有内容基础上，在"工作流"下方增加：
```
## agent-reach 调用示例

搜索命令示例：
```
agent-reach: 搜索「律师 热点 新闻」小红书/微博/知乎
agent-reach: 搜索「法律 新规 最新」全网
```

## 输出排序

按热度排序：🔥🔥🔥（高） > 🔥🔥（中） > 🔥（低）
热度判断标准：
- 高：多个平台同时出现 + 讨论量 > 1000
- 中：单平台热门 + 讨论量 100-1000
- 低：有讨论但量 < 100
```

### Task 3: 多平台适配 — 实现文案转换逻辑

**Files:**
- Create: `mcp/marketing-server/src/platform_adapter.py`
- Modify: `mcp/marketing-server/src/server.py`

- [ ] **Step 1: 创建 `platform_adapter.py`**

```python
"""多平台文案适配器"""

def adapt_content(content: str, source_platform: str, target_platform: str, rules: dict) -> dict:
    """
    将文案从源平台格式转换为目标平台格式
    返回 {title, body, tips}
    """
    if target_platform == "xiaohongshu":
        return _to_xiaohongshu(content, rules)
    elif target_platform == "douyin":
        return _to_douyin(content, rules)
    elif target_platform == "wechat":
        return _to_wechat(content, rules)
    else:
        return {"title": "", "body": content, "tips": ["未知平台"]}

def _to_xiaohongshu(content: str, rules: dict) -> dict:
    max_title = rules.get("title_max_length", 20)
    lines = content.strip().split("\n")
    # 首行截断作为标题
    title = lines[0][:max_title] if lines else ""
    # 剩余内容分段
    body_lines = []
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        # 每段不超过 4 行，拆分为短段落
        body_lines.append(line)
    body = "\n\n".join(body_lines)
    return {
        "title": title,
        "body": body,
        "tips": [
            "建议每段 2-4 行",
            "结尾加上相关话题标签",
            "适当添加 emoji 增加可读性"
        ]
    }

def _to_douyin(content: str, rules: dict) -> dict:
    max_title = rules.get("title_max_length", 30)
    lines = content.strip().split("\n")
    title = lines[0][:max_title] if lines else ""
    body_parts = []
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        body_parts.append(line)
    body = "\n".join(body_parts)
    return {
        "title": title,
        "body": body,
        "tips": [
            "开场 3 秒必须抛出钩子",
            "控制在 15-60 秒口播量",
            "结尾加上引导互动的话术"
        ]
    }

def _to_wechat(content: str, rules: dict) -> dict:
    max_title = rules.get("title_max_length", 64)
    lines = content.strip().split("\n")
    title = lines[0][:max_title] if lines else ""
    body = "\n\n".join(lines[1:])
    return {
        "title": title,
        "body": body,
        "tips": [
            "建议插入小标题分段",
            "在结尾加金句总结",
            "可加入互动引导：'你怎么看？评论区告诉我'"
        ]
    }
```

### Task 4: 多平台适配 — 完善 SKILL.md 的转换步骤

**Files:**
- Modify: `.agents/skills/多平台适配/SKILL.md`

- [ ] **Step 1: 更新 SKILL.md 加入转换示例**

在现有内容基础上，在"平台规则摘要"下方增加：

```
## 转换示例

### 原文（通用格式）
```
今天给大家科普一下XX法律知识。
这个问题很多人都问过，今天一次性说清楚。
第一，什么是XX。
第二，XX怎么处理。
第三，XX的注意事项。
```

### → 小红书版
标题（20字内）：XX不知道这些亏大了
正文：
段落 1：引入问题（加 emoji）
段落 2：干货 1（加 emoji）
段落 3：干货 2（加 emoji）
段落 4：总结
#法律科普 #律师日常 #XX

### → 抖音口播版
开头 3秒：「XX万赔偿，他只做对了一件事！」
正文：口语化、节奏紧凑
结尾：「关注我，学法律不吃亏」

### → 公众号版
标题（64字内）：信息量大，兼顾吸引力和权威感
正文：分段加小标题，深度分析
结尾：金句总结 + 互动引导
```

## ⚠️ 自查清单（新增）
- [ ] 转换后是否符合目标平台的 title_max_length
- [ ] 转换后是否符合目标平台的结构要求
- [ ] 是否调用了 get_platform_rule 获取配置
- [ ] 是否输出了 tips 优化建议
- [ ] 是否调用了 store_knowledge

### Task 5: 验证 P1 闭环

- [ ] **Step 1: 测试 hot_track 返回搜索策略**
  输入：`{"jsonrpc":"2.0","method":"hot_track","params":{"industry":"lawyer"},"id":1}`
  预期：返回 search_queries 列表

- [ ] **Step 2: 测试平台适配转换**
  ```
  python3 -c "
  from platform_adapter import adapt_content
  from database import get_conn
  conn = get_conn('seed')
  import json
  cur = conn.execute('SELECT rules FROM platform_rules WHERE platform=\"xiaohongshu\"')
  rules = json.loads(cur.fetchone()['rules'])
  result = adapt_content('标题\n一段内容\n二段内容', 'general', 'xiaohongshu', rules)
  print(result)
  "
  ```
  预期：返回 title + body + tips

- [ ] **Step 3: 全链路测试**
  设备 → 获取平台规则 → 执行转换 → 存入 my_articles → 搜索能命中
