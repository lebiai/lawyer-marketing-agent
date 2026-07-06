# 营销创作 Agent — P3 实施计划

**Goal:** 数据分析、内容排期、评论助手三大能力

---

### Task 1: 数据分析模块

**Files:**
- Create: `mcp/marketing-server/src/data_analyzer.py`
- Modify: `mcp/marketing-server/src/server.py`
- Modify: `.agents/skills/文案创作/SKILL.md`

- [ ] **Step 1: 创建 `data_analyzer.py`**

```python
"""内容数据分析模块"""
from datetime import datetime, timedelta
from database import get_conn

def get_content_stats(days: int = 30) -> dict:
    """获取近期内容统计数据"""
    conn = get_conn("knowledge")
    since = (datetime.now() - timedelta(days=days)).isoformat()
    
    # 总发文数
    total = conn.execute("SELECT COUNT(*) as c FROM my_articles").fetchone()["c"]
    
    # 各平台分布
    platform_dist = {}
    cur = conn.execute("SELECT platform, COUNT(*) as c FROM my_articles GROUP BY platform")
    for row in cur.fetchall():
        platform_dist[row["platform"]] = row["c"]
    
    # 有效果数据的文章
    with_perf = conn.execute(
        "SELECT COUNT(*) as c FROM my_articles WHERE performance IS NOT NULL"
    ).fetchone()["c"]
    
    # 近期内容
    recent = conn.execute(
        "SELECT platform, title, created_at FROM my_articles ORDER BY created_at DESC LIMIT 10"
    ).fetchall()
    
    # 风格样本库统计
    samples = conn.execute("SELECT COUNT(*) as c FROM content_samples").fetchone()["c"]
    
    # 知识增长
    growth = conn.execute(
        "SELECT COUNT(*) as c FROM my_articles WHERE created_at >= ?", (since,)
    ).fetchone()["c"]
    
    # 对话统计
    conn2 = get_conn("profile")
    conversations = conn2.execute("SELECT COUNT(*) as c FROM conversation_logs").fetchone()["c"]
    conv_growth = conn2.execute(
        "SELECT COUNT(*) as c FROM conversation_logs WHERE created_at >= ?", (since,)
    ).fetchone()["c"]
    conn2.close()
    
    conn.close()
    
    return {
        "total_articles": total,
        "platform_distribution": platform_dist,
        "articles_with_performance_data": with_perf,
        "style_samples": samples,
        "recent_articles": [dict(r) for r in recent],
        "period_days": days,
        "growth": {
            "articles_grown": growth,
            "conversations_grown": conv_growth,
            "total_conversations": conversations
        }
    }

def analyze_performance(articles_data: list) -> dict:
    """分析文章效果数据（需用户提供）"""
    if not articles_data:
        return {"error": "请提供文章效果数据"}
    total_engagement = 0
    best = None
    for art in articles_data:
        eng = art.get("likes", 0) + art.get("favorites", 0) + art.get("comments", 0)
        if eng > total_engagement:
            total_engagement = eng
            best = art
    return {
        "total_articles_analyzed": len(articles_data),
        "total_engagement": total_engagement,
        "best_performing": best,
        "suggestion": (
            f"表现最好的内容是「{best['title']}」" if best else "暂无数据"
        )
    }
```

- [ ] **Step 2: 在 server.py 注册方法**

追加 import：
```python
from data_analyzer import get_content_stats, analyze_performance
```

追加方法：
```python
    elif method == "get_content_stats":
        days = params.get("days", 30)
        stats = get_content_stats(days)
        return {"jsonrpc": "2.0", "id": request_id, "result": stats}

    elif method == "analyze_performance":
        articles = params.get("articles", [])
        result = analyze_performance(articles)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
```

### Task 2: 数据分析 SKILL.md

**Files:**
- Create: `.agents/skills/数据分析/SKILL.md`

```markdown
---
name: 数据分析
description: 当用户说「看看我的数据」「最近表现怎么样」「生成复盘报告」时执行
---

# 数据分析

## 工作流

```
Step 1: 调用 get_content_stats 获取统计数据
Step 2: 整理成复盘报告输出
Step 3: 调用 log_conversation
```

## 输出格式

```
════════════════════════════════
📊 内容数据报告
════════════════════════════════

📌 总发文数：XX 篇
📌 平台分布：
  - 小红书：X 篇
  - 抖音：X 篇
  - 公众号：X 篇

📌 风格样本库：X 条
📌 近 30 天增长：
  - 新发文：X 篇
  - 新对话：X 次

📌 近期内容：
  1. [标题] — [平台] — [日期]
  2. ...

💡 建议：[基于数据的优化建议]
════════════════════════════════
```

## ⚠️ 自查清单
- [ ] 是否调用了 get_content_stats
- [ ] 是否给出了基于数据的建议
- [ ] 是否调用了 log_conversation
```

### Task 3: 内容排期模块

**Files:**
- Create: `mcp/marketing-server/src/scheduler.py`
- Modify: `mcp/marketing-server/src/server.py`

- [ ] **Step 1: 创建 `scheduler.py`**

```python
"""内容排期模块"""
from datetime import datetime, timedelta
import json

WEEKLY_TEMPLATES = {
    "balanced": {
        "name": "均衡型（每周3篇）",
        "schedule": [
            {"day": "周一", "platform": "公众号", "content_type": "深度长文/案例解读"},
            {"day": "周三", "platform": "抖音", "content_type": "口播科普/热点点评"},
            {"day": "周五", "platform": "小红书", "content_type": "图文干货/避坑指南"}
        ]
    },
    "intensive": {
        "name": "高频型（每周5篇）",
        "schedule": [
            {"day": "周一", "platform": "公众号", "content_type": "深度长文"},
            {"day": "周二", "platform": "小红书", "content_type": "知识卡片"},
            {"day": "周三", "platform": "抖音", "content_type": "口播"},
            {"day": "周四", "platform": "小红书", "content_type": "案例分享"},
            {"day": "周五", "platform": "抖音", "content_type": "热点点评"}
        ]
    },
    "focused": {
        "name": "聚焦型（每周2篇）",
        "schedule": [
            {"day": "周三", "platform": "抖音", "content_type": "口播科普"},
            {"day": "周六", "platform": "公众号", "content_type": "深度分析"}
        ]
    }
}

def generate_calendar(template_name: str = "balanced", start_date: str = None) -> dict:
    """根据模板生成排期日历"""
    template = WEEKLY_TEMPLATES.get(template_name, WEEKLY_TEMPLATES["balanced"])
    if not start_date:
        start_date = datetime.now().strftime("%Y-%m-%d")
    start = datetime.strptime(start_date, "%Y-%m-%d")
    
    day_map = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6}
    weeks = []
    for w in range(4):  # 生成4周
        week = []
        for item in template["schedule"]:
            target = day_map[item["day"]]
            date = start + timedelta(days=w * 7 + target)
            week.append({
                "date": date.strftime("%Y-%m-%d"),
                "day": item["day"],
                "platform": item["platform"],
                "content_type": item["content_type"],
                "status": "待创作"
            })
        weeks.append({"week": w + 1, "items": week})
    
    return {
        "template": template["name"],
        "start_date": start_date,
        "weeks": weeks,
        "total_items": len(template["schedule"]) * 4
    }

def get_templates() -> dict:
    """获取可用排期模板"""
    return {k: {"name": v["name"], "count": len(v["schedule"])} 
            for k, v in WEEKLY_TEMPLATES.items()}
```

- [ ] **Step 2: 在 server.py 注册方法**

追加 import：
```python
from scheduler import generate_calendar, get_templates
```

追加方法：
```python
    elif method == "generate_calendar":
        template = params.get("template", "balanced")
        start = params.get("start_date")
        calendar = generate_calendar(template, start)
        return {"jsonrpc": "2.0", "id": request_id, "result": calendar}

    elif method == "get_schedule_templates":
        templates = get_templates()
        return {"jsonrpc": "2.0", "id": request_id, "result": templates}
```

### Task 4: 内容排期 SKILL.md

**Files:**
- Create: `.agents/skills/内容排期/SKILL.md`

```markdown
---
name: 内容排期
description: 当用户说「帮我做个排期」「生成内容日历」「安排一下下周的内容」时执行
---

# 内容排期

## 工作流

```
Step 1: 询问用户创作节奏（均衡/高频/聚焦）
Step 2: 调用 generate_calendar 生成排期
Step 3: 输出日历 + 可选结合热点追踪优化
Step 4: 调用 log_conversation
```

## 可用模板

| 模板 | 频率 | 适合场景 |
|------|------|---------|
| 均衡型 | 每周3篇 | 大部分创作者 |
| 高频型 | 每周5篇 | 全职创作者 |
| 聚焦型 | 每周2篇 | 兼职/新手 |

## 输出格式

```
════════════════════════════════
📅 内容排期日历
════════════════════════════════

📌 模板：[均衡型/高频型/聚焦型]
📌 周期：4 周
📌 总计：X 篇内容

第 1 周
  [日期] [平台] [内容类型] — ⏳ 待创作
  [日期] [平台] [内容类型] — ⏳ 待创作
  ...

第 2 周
  ...

💡 提示：可结合热点追踪优化选题
════════════════════════════════
```

## ⚠️ 自查清单
- [ ] 是否先询问了用户想要的节奏
- [ ] 是否调用了 generate_calendar
- [ ] 是否给出了 4 周的完整排期
- [ ] 是否提示了可结合热点优化
- [ ] 是否调用了 log_conversation
```

### Task 5: 评论助手模块

**Files:**
- Create: `mcp/marketing-server/src/comment_assistant.py`
- Modify: `mcp/marketing-server/src/server.py`

- [ ] **Step 1: 创建 `comment_assistant.py`**

```python
"""评论助手模块"""

REPLY_TEMPLATES = {
    "thanks": {
        "label": "感谢互动",
        "templates": [
            "谢谢支持！有法律问题随时问我 🙌",
            "感谢关注，后续会分享更多法律干货 📚",
            "谢谢！觉得有用的话可以转发给需要的朋友 🤝"
        ]
    },
    "question": {
        "label": "回答法律问题",
        "templates": [
            "这个问题比较常见，简单来说：{answer}。建议具体案情咨询专业律师。",
            "根据法律规定，{answer}。建议收集好相关证据。",
            "好的，我简单解释一下：{answer}。如果情况复杂建议当面咨询。"
        ]
    },
    "disagree": {
        "label": "处理不同意见",
        "templates": [
            "理解你的观点，这个问题在实践中确实有不同看法，我的分析是基于{reason}。",
            "谢谢补充！这也是一个角度，在实践中需要根据具体情况判断。",
            "好的，你说得有道理。法律问题往往不是非黑即白的。"
        ]
    },
    "promote": {
        "label": "引导关注",
        "templates": [
            "觉得有用的话点个❤️，让更多人看到！",
            "关注我，每天学点法律知识 🔔",
            "还有什么法律问题想了解的？评论区告诉我 💬"
        ]
    }
}

def suggest_reply(comment: str, category: str = None) -> dict:
    """根据评论内容建议回复"""
    if not category:
        # 自动分类
        if any(w in comment for w in ["谢谢", "感谢", "赞", "棒"]):
            category = "thanks"
        elif "?" in comment or "吗" in comment or "怎么" in comment:
            category = "question"
        elif any(w in comment for w in ["不对", "不同意", "错了", "不是"]):
            category = "disagree"
        else:
            category = "thanks"
    
    templates = REPLY_TEMPLATES.get(category, REPLY_TEMPLATES["thanks"])
    return {
        "category": templates["label"],
        "original_comment": comment,
        "suggestions": templates["templates"],
        "tip": "建议根据具体情况微调后回复，保持人设一致性"
    }

def analyze_sentiment(comments: list) -> dict:
    """分析评论区情绪"""
    total = len(comments)
    if total == 0:
        return {"total": 0, "error": "无评论数据"}
    
    positive = sum(1 for c in comments if any(w in c for w in ["谢谢", "赞", "好", "棒", "有用"]))
    questioning = sum(1 for c in comments if "?" in c or "吗" in c)
    negative = sum(1 for c in comments if any(w in c for w in ["不对", "错了", "差", "不好"]))
    other = total - positive - questioning - negative
    
    return {
        "total": total,
        "sentiment": {
            "正面": positive,
            "提问": questioning,
            "负面": negative,
            "其他": other
        },
        "positive_rate": round(positive / total * 100, 1) if total > 0 else 0,
        "suggestion": "评论区总体积极，建议重点回复提问类评论" if questioning > 0 else "评论区互动良好"
    }
```

- [ ] **Step 2: 在 server.py 注册方法**

追加 import：
```python
from comment_assistant import suggest_reply, analyze_sentiment
```

追加方法：
```python
    elif method == "suggest_reply":
        comment = params.get("comment", "")
        category = params.get("category")
        result = suggest_reply(comment, category)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "analyze_sentiment":
        comments = params.get("comments", [])
        result = analyze_sentiment(comments)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
```

### Task 6: 评论助手 SKILL.md

**Files:**
- Create: `.agents/skills/评论助手/SKILL.md`

```markdown
---
name: 评论助手
description: 当用户说「帮我回复这条评论」「看看评论区情绪」「生成回复话术」时执行
---

# 评论助手

## 工作流

```
Step 1: 用户提供评论内容
Step 2: 调用 suggest_reply 生成回复建议
Step 3: 输出多个回复选项供用户选择
Step 4: 调用 log_conversation
```

## 回复分类

| 类别 | 适用场景 |
|------|---------|
| 感谢互动 | 正面评论、点赞、支持 |
| 回答法律问题 | 用户提出法律疑问 |
| 处理不同意见 | 有争议的评论 |
| 引导关注 | 互动后引导关注 |

## 输出格式

```
════════════════════════════════
💬 回复建议
════════════════════════════════

📌 分类：[感谢互动/回答法律问题/...]
📌 原文：「[用户评论]」

建议回复：
1. [选项1]
2. [选项2]
3. [选项3]

💡 建议根据具体情况微调，保持人设一致性
════════════════════════════════
```

## ⚠️ 自查清单
- [ ] 是否分析了评论的类别
- [ ] 是否提供了 3 个回复选项
- [ ] 是否提示了微调建议
- [ ] 是否调用了 log_conversation
```

### Task 7: 验证 P3 闭环

- [ ] **Step 1: 测试 get_content_stats**
  输入：`{"jsonrpc":"2.0","method":"get_content_stats","params":{"days":30},"id":1}`
  预期：返回统计数据

- [ ] **Step 2: 测试 generate_calendar**
  输入：`{"jsonrpc":"2.0","method":"generate_calendar","params":{"template":"balanced"},"id":2}`
  预期：返回 4 周排期

- [ ] **Step 3: 测试 suggest_reply**
  输入：`{"jsonrpc":"2.0","method":"suggest_reply","params":{"comment":"谢谢律师分享，非常有用！"},"id":3}`
  预期：返回 3 个回复建议

- [ ] **Step 4: 测试 analyze_sentiment**
  输入：`{"jsonrpc":"2.0","method":"analyze_sentiment","params":{"comments":["谢谢！","这个不对吧","请问怎么维权？","太棒了"]},"id":4}`
  预期：返回情绪分布
