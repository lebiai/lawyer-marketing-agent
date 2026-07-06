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
