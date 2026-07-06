# 营销创作 Agent — P2 实施计划

**Goal:** 实现竞品账号分析和视频生成提示词两大能力

---

### Task 1: 竞品账号分析模块

**Files:**
- Create: `mcp/marketing-server/src/competitor_analyzer.py`
- Modify: `mcp/marketing-server/src/server.py`

- [ ] **Step 1: 创建 `competitor_analyzer.py`**

```python
"""竞品账号分析模块"""

ANALYSIS_DIMENSIONS = {
    "content_strategy": {
        "label": "内容策略",
        "questions": [
            "主要发布什么类型的内容？（科普/案例/观点/干货）",
            "更新频率如何？（日更/周更/不定时）",
            "内容长度偏好？（短图文/长文/视频）"
        ]
    },
    "style_features": {
        "label": "风格特征",
        "questions": [
            "语气风格？（严肃/幽默/亲切/犀利）",
            "排版特点？（emoji使用/分段方式/视觉风格）",
            "人设定位？（专家/朋友/吐槽/导师）"
        ]
    },
    "engagement": {
        "label": "互动表现",
        "questions": [
            "平均点赞/收藏/评论数据？",
            "哪类内容互动最高？",
            "评论区用户主要在问什么？"
        ]
    },
    "top_topics": {
        "label": "高频话题",
        "questions": [
            "最常讨论的3-5个话题是什么？",
            "这些话题的切入角度有何特点？",
            "有没有形成系列或专栏？"
        ]
    }
}

def generate_analysis_report(account_name: str, platform: str, raw_data: dict) -> str:
    """生成结构化的竞品分析报告"""
    lines = []
    lines.append(f"📊 竞品账号分析报告：{account_name}")
    lines.append(f"📌 平台：{platform}")
    lines.append("")

    for dim_key, dim_info in ANALYSIS_DIMENSIONS.items():
        lines.append(f"【{dim_info['label']}】")
        for q in dim_info["questions"]:
            lines.append(f"  ▸ {q}")
        lines.append("")

    return "\n".join(lines)

def extract_style_tags(report_text: str) -> list:
    """从分析报告中提取风格标签"""
    tags = []
    style_keywords = {
        "专业": ["专业", "权威", "严谨"],
        "幽默": ["幽默", "搞笑", "段子"],
        "亲切": ["亲切", "朋友", "接地气"],
        "犀利": ["犀利", "尖锐", "敢说"],
        "温和": ["温和", "耐心", "温柔"]
    }
    for tag, keywords in style_keywords.items():
        if any(kw in report_text for kw in keywords):
            tags.append(tag)
    return tags
```

- [ ] **Step 2: 在 server.py 中添加 `analyze_account` 方法**

在 server.py 顶部添加：
```python
from competitor_analyzer import generate_analysis_report, extract_style_tags
```

在 handle_request 的 error 返回前添加：
```python
    elif method == "analyze_account":
        account = params.get("account_name", "")
        platform = params.get("platform", "")
        raw_data = params.get("raw_data", {})
        report = generate_analysis_report(account, platform, raw_data)
        tags = extract_style_tags(report)
        return {"jsonrpc": "2.0", "id": request_id, "result": {
            "report": report,
            "suggested_tags": tags,
            "storage": {
                "table": "competitor_analysis",
                "data": {
                    "account_name": account,
                    "platform": platform,
                    "analysis_type": "full",
                    "report": report,
                    "raw_data": raw_data
                }
            }
        }}
```

### Task 2: 竞品分析 SKILL.md

**Files:**
- Create: `.agents/skills/竞品账号分析/SKILL.md`

- [ ] **Step 1: 创建 SKILL.md**

```markdown
---
name: 竞品账号分析
description: 当用户说「分析一下这个账号」「拆解XX账号」「看看这个号的内容策略」时执行
---

# 竞品账号分析

## 工作流

```
Step 1: 用户提供目标账号名称/链接
Step 2: 分析内容策略/风格特征/互动表现/高频话题
Step 3: 调用 analyze_account 生成报告
Step 4: 调用 store_knowledge(competitor_analysis)
Step 5: 调用 log_conversation
```

## 输出格式

```
════════════════════════════════
📊 竞品账号分析报告：[账号名]
════════════════════════════════

📌 平台：[平台]

【内容策略】
▸ 主要发布什么类型的内容？
▸ 更新频率如何？
▸ 内容长度偏好？

【风格特征】
▸ 语气风格？
▸ 排版特点？
▸ 人设定位？

【互动表现】
▸ 平均数据？
▸ 哪类内容互动最高？
▸ 评论区关注点？

【高频话题】
▸ 最常讨论的话题？
▸ 切入角度特点？
▸ 系列或专栏？

🏷️ 风格标签：[标签1, 标签2, ...]
════════════════════════════════
```

## ⚠️ 自查清单
- [ ] 是否覆盖了 4 个分析维度
- [ ] 是否输出了风格标签
- [ ] 是否调用了 store_knowledge
- [ ] 是否调用了 log_conversation
```

### Task 3: 视频生成提示词模块

**Files:**
- Create: `mcp/marketing-server/src/video_prompt.py`
- Modify: `mcp/marketing-server/src/server.py`

- [ ] **Step 1: 创建 `video_prompt.py`**

```python
"""视频生成提示词模块"""

def generate_video_prompt(script: str, mode: str = "live") -> dict:
    """
    将口播文案转为 AI 视频模型的提示词
    mode: 'live' = 镜头前口播, 'voiceover' = 画面+旁白
    """
    if mode == "live":
        return _to_live_prompt(script)
    else:
        return _to_voiceover_prompt(script)

def _to_live_prompt(script: str) -> dict:
    lines = [l.strip() for l in script.split("\n") if l.strip()]
    hook = lines[0] if lines else ""
    segments = []
    for i, line in enumerate(lines):
        segments.append({
            "segment": i + 1,
            "text": line,
            "expression_guide": _suggest_expression(line),
            "duration_seconds": _estimate_duration(line)
        })
    return {
        "mode": "镜头前口播",
        "hook": hook,
        "style_guide": "自然亲切，眼神交流，适当手势",
        "segments": segments,
        "total_duration_seconds": sum(s["duration_seconds"] for s in segments),
        "prompt_for_ai_video": (
            f"一位律师面对镜头口播，背景为书架/律师事务所。\n"
            f"开场：{hook}\n"
            f"语气：专业自然，略带亲切\n"
            f"镜头：中景，眼神交流\n"
            f"时长：约{sum(s['duration_seconds'] for s in segments)}秒"
        )
    }

def _to_voiceover_prompt(script: str) -> dict:
    lines = [l.strip() for l in script.split("\n") if l.strip()]
    scenes = []
    for i, line in enumerate(lines):
        scenes.append({
            "scene": i + 1,
            "narration": line,
            "suggested_visual": _suggest_visual(i, line),
            "duration_seconds": _estimate_duration(line)
        })
    return {
        "mode": "资料画面+旁白",
        "scenes": scenes,
        "total_duration_seconds": sum(s["duration_seconds"] for s in scenes),
        "prompt_for_ai_video": (
            f"法律科普视频，旁白解说配合资料画面。\n"
            f"共{len(scenes)}个场景，约{sum(s['duration_seconds'] for s in scenes)}秒。\n"
            f"画面风格：简洁专业，法律元素（法槌、法典、法庭场景插画）"
        )
    }

def _suggest_expression(line: str) -> str:
    """根据文案内容建议表情管理"""
    if any(w in line for w in ["注意", "警惕", "千万别", "小心"]):
        return "表情严肃，眼神坚定"
    elif any(w in line for w in ["你知道吗", "其实", "没想到"]):
        return "微微惊讶，引起好奇"
    elif any(w in line for w in ["好消息", "恭喜", "终于"]):
        return "微笑，积极"
    elif any(w in line for w in ["？", "吗"]):
        return "挑眉，疑问表情"
    return "自然认真"

def _suggest_visual(scene_idx: int, line: str) -> str:
    """建议旁白模式下的画面"""
    visuals = [
        "律师在办公室翻阅文件的画面",
        "法庭外景或法庭内景插画",
        "法律条文特写效果",
        "数据图表或统计动画",
        "律师与客户对话场景",
        "新闻标题或报道截图风格",
        "天平/法槌/法典等法律符号动画",
        "日常场景插画（家庭、公司、街道）"
    ]
    return visuals[scene_idx % len(visuals)]

def _estimate_duration(line: str) -> int:
    """估算口播时长（秒）"""
    char_count = len(line)
    if char_count < 15:
        return 3
    elif char_count < 30:
        return 5
    elif char_count < 50:
        return 8
    else:
        return 12


def generate_templates() -> dict:
    """返回常用视频模板"""
    return {
        "法律科普": {
            "structure": [
                "热点/案例引入（3-5秒）",
                "法律知识点讲解（15-20秒）",
                "实操建议（10-15秒）",
                "总结金句+互动引导（5-8秒）"
            ],
            "total_duration": "35-50秒",
            "style": "专业科普"
        },
        "案件解读": {
            "structure": [
                "案件概述（5-8秒）",
                "法律争议焦点（15-20秒）",
                "法院判决/法律依据（10-15秒）",
                "对普通人的启示（5-10秒）"
            ],
            "total_duration": "40-55秒",
            "style": "深度分析"
        },
        "避坑指南": {
            "structure": [
                "抛出问题/痛点（3-5秒）",
                "常见误区（10-15秒）",
                "正确做法（10-12秒）",
                "提醒+互动（5-8秒）"
            ],
            "total_duration": "30-40秒",
            "style": "警示建议"
        }
    }
```

- [ ] **Step 2: 在 server.py 中添加 `generate_video_prompt` 方法**

在 server.py 顶部添加：
```python
from video_prompt import generate_video_prompt, generate_templates
```

在 handle_request 的 error 返回前添加：
```python
    elif method == "generate_video_prompt":
        script = params.get("script", "")
        mode = params.get("mode", "live")
        result = generate_video_prompt(script, mode)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    elif method == "get_video_templates":
        templates = generate_templates()
        return {"jsonrpc": "2.0", "id": request_id, "result": templates}
```

### Task 4: 视频生成提示词 SKILL.md

**Files:**
- Create: `.agents/skills/视频生成提示词/SKILL.md`

- [ ] **Step 1: 创建 SKILL.md**

```markdown
---
name: 视频生成提示词
description: 当用户说「把这个文案做成视频」「生成视频提示词」「做成口播视频」时执行
---

# 视频生成提示词

## 工作流

```
Step 1: 用户提供文案或引用已有 my_articles
Step 2: 调用 generate_video_prompt 生成提示词
Step 3: 输出分镜 + 提示词 + 可用模板参考
Step 4: 调用 log_conversation
```

## 双模式说明

### 模式一：镜头前口播（推荐）
适合：律师本人出镜，面对镜头讲述
生成内容：文案分段 + 表情管理建议 + AI 视频模型提示词

### 模式二：资料画面+旁白
适合：不想出镜，用画面配合旁白
生成内容：分镜表 + 每个场景的画面建议 + AI 视频模型提示词

## 输出格式

```
════════════════════════════════
🎬 视频生成方案
════════════════════════════════

📌 模式：[镜头前口播 / 资料画面+旁白]

一、分镜表 ✔
  [分段内容]

二、时长预估 ✔
  总计：XX 秒

三、AI 视频模型提示词 ✔
  [可直接复制的提示词]

四、可选模板参考 ✔
  - 法律科普：35-50秒
  - 案件解读：40-55秒
  - 避坑指南：30-40秒
════════════════════════════════
```

## ⚠️ 自查清单
- [ ] 是否选择了正确的模式
- [ ] 是否输出了完整的 AI 模型提示词
- [ ] 是否输出了分镜/分段
- [ ] 是否输出了时长预估
- [ ] 是否调用了 log_conversation
```

### Task 5: 验证 P2 闭环

- [ ] **Step 1: 测试竞品分析**
  输入：`{"jsonrpc":"2.0","method":"analyze_account","params":{"account_name":"XX律师","platform":"xiaohongshu"},"id":1}`
  预期：返回报告 + 风格标签 + 存储建议

- [ ] **Step 2: 测试视频提示词（口播模式）**
  输入：`{"jsonrpc":"2.0","method":"generate_video_prompt","params":{"script":"警惕！这种情况下你需要请律师。\\n很多人以为打官司很简单，\\n其实里面有很多陷阱。","mode":"live"},"id":2}`
  预期：返回分镜 + 表情建议 + AI 模型提示词

- [ ] **Step 3: 测试视频模板**
  输入：`{"jsonrpc":"2.0","method":"get_video_templates","id":3}`
  预期：返回三个模板

- [ ] **Step 4: 测试全链路**
  分析账号 → 生成报告 → 存储 → 搜索能命中
