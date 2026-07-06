# 营销创作 Agent — P4 实施计划

**Goal:** 品牌一致性检查 + 素材库管理

---

### Task 1: 品牌一致性检查模块

**Files:**
- Create: `mcp/marketing-server/src/brand_checker.py`
- Modify: `mcp/marketing-server/src/server.py`

- [ ] **Step 1: 创建 `brand_checker.py`**

```python
"""品牌一致性检查模块"""
from database import get_conn

def check_brand_consistency(content: str, platform: str = None) -> dict:
    """检查文案是否符合已配置的品牌规范"""
    conn = get_conn("knowledge")
    profiles = conn.execute("SELECT * FROM brand_profile WHERE is_active=1").fetchall()
    conn.close()
    
    if not profiles:
        return {
            "has_profile": False,
            "message": "尚未配置品牌规范，请先通过 store_knowledge(brand_profile) 设置",
            "checks": []
        }
    
    checks = []
    issues = []
    for p in profiles:
        dim = p["dimension"]
        rule = p["content"].lower()
        
        if dim == "tone":
            # 检查语气风格
            if "严肃" in rule and any(w in content for w in ["哈哈", "嘻嘻", "😂"]):
                issues.append(f"品牌设定为严肃语气，但文案包含轻佻表达")
                checks.append({"dimension": "语气", "status": "❌", "detail": "存在轻佻表达"})
            elif "亲切" in rule and not any(w in content for w in ["你", "我们", "~"]):
                issues.append(f"品牌设定为亲切语气，建议增加第二人称")
                checks.append({"dimension": "语气", "status": "⚠️", "detail": "亲切感不足"})
            else:
                checks.append({"dimension": "语气", "status": "✅", "detail": f"符合 {rule[:20]} 设定"})
        
        elif dim == "taboo":
            # 检查违禁词
            found = [w.strip() for w in rule.split(",") if w.strip() in content]
            if found:
                issues.append(f"包含违禁词：{', '.join(found)}")
                checks.append({"dimension": "违禁词", "status": "❌", "detail": f"发现：{', '.join(found)}"})
            else:
                checks.append({"dimension": "违禁词", "status": "✅", "detail": "未发现违禁词"})
        
        elif dim == "keywords":
            # 检查核心关键词覆盖
            keywords = [w.strip() for w in rule.split(",")]
            covered = [k for k in keywords if k in content]
            if len(covered) < len(keywords) * 0.5:
                issues.append(f"核心关键词覆盖率不足（{len(covered)}/{len(keywords)}）")
                checks.append({"dimension": "关键词覆盖", "status": "⚠️", "detail": f"覆盖 {len(covered)}/{len(keywords)}"})
            else:
                checks.append({"dimension": "关键词覆盖", "status": "✅", "detail": f"覆盖 {len(covered)}/{len(keywords)}"})
        
        elif dim == "target_audience":
            checks.append({"dimension": "受众匹配", "status": "✅", "detail": f"面向：{p['content'][:40]}..."})
        
        else:
            checks.append({"dimension": dim, "status": "✅", "detail": p['content'][:50]})
    
    return {
        "has_profile": True,
        "content_length": len(content),
        "platform": platform,
        "checks": checks,
        "issues": issues,
        "pass": len(issues) == 0,
        "summary": f"检查通过 ✅" if len(issues) == 0 else f"发现 {len(issues)} 个问题 ❌"
    }

def suggest_improvements(content: str, platform: str) -> list:
    """根据平台规则建议改进"""
    conn = get_conn("seed")
    cur = conn.execute("SELECT rules FROM platform_rules WHERE platform = ?", (platform,))
    row = cur.fetchone()
    conn.close()
    
    if not row:
        return ["未知平台，无法提供优化建议"]
    
    import json
    rules = json.loads(row["rules"])
    suggestions = []
    
    title_len = len(content.split("\n")[0]) if content else 0
    max_title = rules.get("title_max_length", 999)
    if title_len > max_title:
        suggestions.append(f"标题过长（{title_len}字），建议控制在{max_title}字以内")
    
    taboo = rules.get("taboo", [])
    for word in taboo:
        if word in content:
            suggestions.append(f"避免使用违禁词：{word}")
    
    if not suggestions:
        suggestions.append("文案基本符合平台规范")
    
    return suggestions
```

- [ ] **Step 2: 在 server.py 注册方法**

追加 import：
```python
from brand_checker import check_brand_consistency, suggest_improvements
```

追加方法：
```python
    elif method == "check_brand":
        content = params.get("content", "")
        platform = params.get("platform")
        result = check_brand_consistency(content, platform)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "suggest_improvements":
        content = params.get("content", "")
        platform = params.get("platform", "xiaohongshu")
        result = suggest_improvements(content, platform)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
```

### Task 2: 品牌检查 SKILL.md

**Files:**
- Create: `.agents/skills/品牌一致性检查/SKILL.md`

```markdown
---
name: 品牌一致性检查
description: 当用户说「帮我检查一下品牌一致性」「看看这段文案符合人设吗」「品牌规范检查」时执行
---

# 品牌一致性检查

## 工作流

```
Step 1: 用户提供待检查文案
Step 2: 调用 check_brand 检查品牌规范匹配度
Step 3: 调用 suggest_improvements 获取优化建议
Step 4: 输出检查报告 + 改进建议
Step 5: 调用 log_conversation
```

## 输出格式

```
════════════════════════════════
🏷️ 品牌一致性检查报告
════════════════════════════════

📌 文案长度：X 字
📌 目标平台：[平台]

检查项：
✅ 语气：[结果]
✅ 违禁词：[结果]
✅ 关键词覆盖：[结果]
✅ 受众匹配：[结果]

需要改进：
▸ [建议1]
▸ [建议2]

💡 总体：[通过/需要修改]
════════════════════════════════
```

## ⚠️ 自查清单
- [ ] 是否调用了 check_brand
- [ ] 是否调用了 suggest_improvements
- [ ] 是否给出了明确的可执行建议
- [ ] 是否调用了 log_conversation
```

### Task 3: 素材库管理模块

**Files:**
- Create: `mcp/marketing-server/src/asset_library.py`
- Modify: `mcp/marketing-server/src/server.py`

- [ ] **Step 1: 创建 `asset_library.py`**

```python
"""素材库管理模块"""
from datetime import datetime
from database import get_conn

ASSET_CATEGORIES = {
    "image_template": "图片模板",
    "video_clip": "视频片段",
    "brand_color": "品牌色板",
    "font_style": "字体风格",
    "icon_set": "图标集",
    "music_track": "背景音乐",
    "voice_sample": "语音样本",
    "other": "其他"
}

def store_asset(name: str, category: str, description: str, tags: list = None) -> dict:
    """存储素材到 personal_notes (素材作为特殊类型的笔记)"""
    conn = get_conn("knowledge")
    conn.execute(
        "INSERT INTO personal_notes (title, content, tags, source) VALUES (?, ?, ?, ?)",
        (name, description, 
         str(tags or []), 
         f"asset:{category}")
    )
    conn.commit()
    asset_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]
    conn.close()
    return {"status": "ok", "asset_id": asset_id, "message": f"素材「{name}」已存入"}

def search_assets(query: str = None, category: str = None) -> list:
    """搜索素材库"""
    conn = get_conn("knowledge")
    if category:
        rows = conn.execute(
            "SELECT id, title, content, tags, source, created_at FROM personal_notes WHERE source = ?",
            (f"asset:{category}",)
        ).fetchall()
    elif query:
        rows = conn.execute(
            "SELECT id, title, content, tags, source, created_at FROM personal_notes WHERE title LIKE ? OR content LIKE ?",
            (f"%{query}%", f"%{query}%")
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, title, content, tags, source, created_at FROM personal_notes WHERE source LIKE 'asset:%'"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_asset_stats() -> dict:
    """素材库统计"""
    conn = get_conn("knowledge")
    total = conn.execute("SELECT COUNT(*) as c FROM personal_notes WHERE source LIKE 'asset:%'").fetchone()["c"]
    
    by_category = {}
    cur = conn.execute("SELECT source, COUNT(*) as c FROM personal_notes WHERE source LIKE 'asset:%' GROUP BY source")
    for row in cur.fetchall():
        cat = row["source"].replace("asset:", "")
        by_category[ASSET_CATEGORIES.get(cat, cat)] = row["c"]
    
    conn.close()
    return {"total": total, "by_category": by_category}

def get_categories() -> dict:
    """获取可用分类"""
    return ASSET_CATEGORIES
```

- [ ] **Step 2: 在 server.py 注册方法**

追加 import：
```python
from asset_library import store_asset, search_assets, get_asset_stats, get_categories
```

追加方法：
```python
    elif method == "store_asset":
        result = store_asset(
            params.get("name", ""),
            params.get("category", "other"),
            params.get("description", ""),
            params.get("tags")
        )
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "search_assets":
        result = search_assets(params.get("query"), params.get("category"))
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "get_asset_stats":
        result = get_asset_stats()
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "get_asset_categories":
        result = get_categories()
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
```

### Task 4: 素材库 SKILL.md

**Files:**
- Create: `.agents/skills/素材库/SKILL.md`

```markdown
---
name: 素材库
description: 当用户说「帮我存个素材」「找一下之前的素材」「看看素材库」时执行
---

# 素材库管理

## 工作流

### 存储素材
```
Step 1: 用户提供素材名称、分类、描述、标签
Step 2: 调用 store_asset 存入 personal_notes
Step 3: 确认存储结果
Step 4: 调用 log_conversation
```

### 搜索素材
```
Step 1: 用户提供关键词或分类
Step 2: 调用 search_assets 搜索
Step 3: 输出匹配的素材列表
Step 4: 调用 log_conversation
```

## 可用分类

| 分类 | 说明 |
|------|------|
| image_template | 图片模板 |
| video_clip | 视频片段 |
| brand_color | 品牌色板 |
| font_style | 字体风格 |
| icon_set | 图标集 |
| music_track | 背景音乐 |
| voice_sample | 语音样本 |

## 输出格式

存储时：
```
════════════════════════════════
📦 素材已存储
════════════════════════════════

📌 名称：[素材名]
📌 分类：[分类]
📌 ID：[编号]
📌 状态：✅ 已存入素材库
════════════════════════════════
```

搜索时：
```
════════════════════════════════
🔍 素材搜索结果
════════════════════════════════

📌 共找到 X 个匹配素材

1. [名称] — [分类]
   [描述]
   🏷️ [标签]

2. [名称] — [分类]
   ...
════════════════════════════════
```

## ⚠️ 自查清单
- [ ] 存储时是否要求了名称和分类
- [ ] 搜索时是否提供了关键词或分类
- [ ] 是否调用了对应的 MCP 方法
- [ ] 是否调用了 log_conversation
```

### Task 5: 验证 P4 闭环

- [ ] **Step 1: 测试 brand check（无品牌配置时）**
  输入：`{"jsonrpc":"2.0","method":"check_brand","params":{"content":"这是一段测试文案","platform":"xiaohongshu"},"id":1}`
  预期：返回 has_profile=false

- [ ] **Step 2: 设置品牌规范 + 再次检查**
  先设置：`{"jsonrpc":"2.0","method":"store_knowledge","params":{"table":"brand_profile","data":{"dimension":"tone","content":"专业严谨，避免轻佻表达"}},"id":2}`
  再检查：`{"jsonrpc":"2.0","method":"check_brand","params":{"content":"哈哈这个太搞笑了😂","platform":"xiaohongshu"},"id":3}`
  预期：发现语气问题

- [ ] **Step 3: 测试 suggest_improvements**
  输入：`{"jsonrpc":"2.0","method":"suggest_improvements","params":{"content":"这是一个标题太长的内容超过二十个字了","platform":"xiaohongshu"},"id":4}`
  预期：提示标题过长

- [ ] **Step 4: 测试素材库存储与搜索**
  存储：`{"jsonrpc":"2.0","method":"store_asset","params":{"name":"小红书封面模板1","category":"image_template","description":"法律科普类封面模板","tags":["封面","小红书","法律"]},"id":5}`
  搜索：`{"jsonrpc":"2.0","method":"search_assets","params":{"query":"封面"},"id":6}`
  预期：搜索能命中

- [ ] **Step 5: 测试素材统计**
  输入：`{"jsonrpc":"2.0","method":"get_asset_stats","id":7}`
  预期：返回总数和分类分布
