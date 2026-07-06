"""视频生成提示词模块"""

def generate_video_prompt(script: str, mode: str = "live") -> dict:
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
    total_dur = sum(s["duration_seconds"] for s in segments)
    return {
        "mode": "镜头前口播",
        "hook": hook,
        "style_guide": "自然亲切，眼神交流，适当手势",
        "segments": segments,
        "total_duration_seconds": total_dur,
        "prompt_for_ai_video": (
            f"一位律师面对镜头口播，背景为书架/律师事务所。\n"
            f"开场：{hook}\n"
            f"语气：专业自然，略带亲切\n"
            f"镜头：中景，眼神交流\n"
            f"时长：约{total_dur}秒"
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
    total_dur = sum(s["duration_seconds"] for s in scenes)
    return {
        "mode": "资料画面+旁白",
        "scenes": scenes,
        "total_duration_seconds": total_dur,
        "prompt_for_ai_video": (
            f"法律科普视频，旁白解说配合资料画面。\n"
            f"共{len(scenes)}个场景，约{total_dur}秒。\n"
            f"画面风格：简洁专业，法律元素（法槌、法典、法庭场景插画）"
        )
    }

def _suggest_expression(line: str) -> str:
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
