---
name: 竞品账号分析
description: 当用户说「分析一下这个账号」「拆解XX账号」「看看这个号的内容策略」时执行
---

# 竞品账号分析

使用 blogger-distiller 数据分析引擎，通过 TikHub API 采集公开数据进行深度分析。

## ⚠️ 权限前置

首次分析前，必须调用 `check_tikhub_status` 检查是否已开通分析权限：
- **已开通** → 继续分析流程
- **未开通** → 回复："🔒 竞品/对标账号分析需要开通权限，请联系微信 iodun001 开通"

## 工作流

```
Step 1: 检查权限 → check_tikhub_status
Step 2: 未开通 → 回复加微信引导
Step 3: 确认平台（小红书/抖音）+ 采集数量（30/50/80）
Step 4: 调用 search_blogger_candidates(keyword, platform) 搜索候选人
Step 5: 有多个同名博主 → 展示列表让用户选择
Step 6: 用户选定后 → 调用 analyze_account(account_name, platform, user_id=xxx)
        → 爬取内容 → 数据分析 → 构建报告
Step 7: 展示完整 7维分析报告 + 自动将风格特征入库
Step 8: 调用 store_knowledge(competitor_analysis) + store_knowledge(content_samples)
Step 9: 调用 log_conversation
```

## 候选人搜索（Step 4-5）

`search_blogger_candidates(keyword, platform)` 通过 TikHub API 搜索，返回：

```json
{
  "found": true,
  "candidates": [
    { "uid": "xxx", "nickname": "张三律师", "fans": 123000, "desc": "深圳执业律师...", "display": "张三律师 | 12.3万粉丝 | 深圳执业律师" },
    { "uid": "yyy", "nickname": "张三律师", "fans": 52000, "desc": "北京婚姻律师...", "display": "张三律师 | 5.2万粉丝 | 北京婚姻律师" }
  ]
}
```

**有多个同名时**，展示给用户选择：

```
🔍 找到 2 个「张三律师」：
  ① 张三律师 · 12.3万粉丝 · 深圳执业律师
  ② 张三律师 · 5.2万粉丝 · 北京婚姻律师
请问分析哪一个？
```

用户选择后，将选中的 `uid` 传给 `analyze_account`。

**只有一个匹配时**，直接继续。

## 7维分析框架

| 维度 | 数据来源 |
|------|---------|
| ① 定位与基调 | distiller cognitive analysis |
| ② 语言与文字 | 标题模式 / 标题长度 |
| ③ 内容策略 | category_stats（内容类型分布+均赞） |
| ④ 互动表现 | stats（均赞/藏/评） |
| ⑤ 高频话题 | tag_freq（标签频率排名） |
| ⑥ 高互动内容 | top10（爆款笔记详情） |
| ⑦ 认知层 | opinion_candidates / value_words |

## 用户交互示例

```
用户：分析一下张三律师
Agent：🔍 正在搜索「张三律师」...
       ✅ 找到 2 个匹配：
         ① 张三律师 · 12.3万粉丝 · 深圳执业律师
         ② 张三律师 · 5.2万粉丝 · 北京婚姻律师
       请问分析哪一个？（或提供更精确的博主名）
用户：第一个
Agent：选择平台：小红书 / 抖音？采集数量：30/50/80？
用户：小红书，50条
Agent：📡 正在采集（约30分钟）→ 📊 分析 → 📋 报告
```

## 输出格式

```
╔══ 竞品账号分析报告：[账号名]
║ 📌 平台：[平台]
║ 📊 样本：N 篇内容
║ 🔬 来源：blogger-distiller

【📌 定位与基调】
  ▸ 目标受众：[受众]
  ▸ 情感基调：[基调]
  ▸ 语气立场：[立场]

【✏️ 语言与文字】
  ▸ 标题平均长度：[N]字
  ▸ 标题模式：[模式1, 模式2, ...]

【📋 内容策略】
  ▸ [类型1]: N篇 (X%) · 均赞N
  ▸ [类型2]: N篇 (X%) · 均赞N

【💬 互动表现】
  ▸ 均赞N · 均评N · 均藏N
  ▸ 藏赞比 N（越高越实用）

【🔥 高频话题】
  ▸ #[话题1] (N次)
  ▸ #[话题2] (N次)

【🏆 高互动内容 TOP5】
  ▸ [N赞] [标题]

【🧠 认知层】
  ▸ "观点句..."

🏷️ 风格标签：[基调] · [立场] · [主要类型]
```

## ⚠️ 自查清单
- [ ] 是否先调用 check_tikhub_status 检查了权限
- [ ] 未开通时是否正确引导加微信
- [ ] 是否先调用 search_blogger_candidates 搜索候选人
- [ ] 多个同名时是否展示给用户选择
- [ ] 是否让用户选择了平台和采集数量
- [ ] 分析完成后是否调用了 store_knowledge 存报告
- [ ] 是否提取了风格特征并存入 content_samples
- [ ] 是否调用了 log_conversation
