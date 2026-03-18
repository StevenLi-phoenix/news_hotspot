# 新闻热词

中文新闻词频可视化平台。从原始新闻文本提取热词，按时间轴展示累积词频变化。

## 核心功能

### 📊 词频时间轴可视化

**[word_freq_viz.html](word_freq_viz.html)** — 交互式 Canvas 词云

- **累积词频** — 每月从第一个月到当月的累积词频，词大小动态变化
- **自动播放** — 时间轴逐月动画，支持 3 档变速 (3s/2s/1.2s/0.8s)
- **手动导航** — 点击月份圆点跳转，方向键切换，空格播放/暂停
- **实时提示** — hover 词显示累积频次
- **设计** — 报纸编辑室风格，墨黑底+纸张质感，铁锈红配色

**快捷键：**
```
Space/K  — 播放/暂停
←/→      — 切换月份
1-9      — 跳到第 N 个月
Speed    — 循环变速
```

## 技术栈

### 前端
- **wordcloud2.js** — Canvas 像素级碰撞检测词云布局
- **Vanilla JS** — 无框架，动画 + 交互
- **Google Fonts** — Ma Shan Zheng (毛笔体标题) + Noto Serif SC (内文)

### 数据处理
- **jieba** — 中文分词
- **SQLite** — 新闻存储 (1024 条精选新闻)
- **Python** — 词频提取与累积统计

## 数据流

```
news-zhcn.txt
    ↓ (parse & import)
news_zhcn.sqlite (daily_news_selected)
    ↓ (jieba tokenize + stopwords filter)
word_freq_cumulative.json (9 months snapshots)
    ↓ (inject into HTML)
word_freq_viz.html (interactive canvas cloud)
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `word_freq_viz.html` | 交互式词云可视化（主页面） |
| `word_freq_cumulative.json` | 月度累积词频快照（数据源） |
| `news_zhcn.sqlite` | SQLite 数据库 (1024 条新闻) |
| `import_news_zhcn_to_sqlite.py` | 新闻导入脚本 |
| `news-zhcn.txt` | 原始新闻文本 |

## 数据统计

- **时间范围** — 2024-12-08 至 2025-08-03 (9 个月)
- **新闻总数** — 1024 条 (日均精选)
- **独立热词** — 150 个 (top 词)
- **最高词频** — 特朗普 (498 次)

### 词频 TOP 10

| 排名 | 词 | 累积频次 |
|------|-----|---------|
| 1 | 特朗普 | 498 |
| 2 | 美国 | 410 |
| 3 | 总统 | 226 |
| 4 | 关税 | 155 |
| 5 | 以色列 | 152 |
| 6 | 关于 | 150 |
| 7 | 乌克兰 | 147 |
| 8 | 政治 | 133 |
| 9 | 广泛 | 132 |
| 10 | 重大 | 128 |

## 快速开始

### 1. 查看可视化

```bash
open word_freq_viz.html
```

或用浏览器直接打开文件。

### 2. 重新生成词频数据

```bash
source .venv/bin/activate
python3 -c "
import sqlite3, jieba, json, re
from collections import Counter, defaultdict

# ... (词频提取脚本)
"
```

### 3. 查询新闻数据

```bash
sqlite3 news_zhcn.sqlite "SELECT news_date, title FROM daily_news_selected LIMIT 10;"
```

## 项目结构

```
.
├── word_freq_viz.html           # 词云可视化 (主文件)
├── word_freq_cumulative.json    # 数据源
├── news_zhcn.sqlite             # 新闻数据库
├── import_news_zhcn_to_sqlite.py # 导入脚本
├── news-zhcn.txt                # 原始文本
└── README.md                     # 本文件
```

## 设计说明

### 色彩方案
- **背景** — `#0e0e0c` (深黑墨水)
- **文字** — `#f0ebe2` (米色纸张)
- **强调** — `#c23616` (铁锈红/朱砂)
- **辅助** — `#b8860b` (古金) / `#2e6b62` (深青)

### 排版
- **标题** — Ma Shan Zheng (手写毛笔体，14-18号)
- **内文** — Noto Serif SC (衬线宋体)
- **数据** — Source Code Pro (等宽代码体)

### 动画
- 词云过渡 — 0.7s cubic-bezier 字体缩放
- 时间轴 — 0.35s ease 进度条
- Hover — 0.12s 提示框淡入

## 词频处理

### 分词
- **工具** — jieba 中文分词库
- **参数** — 精确模式，最小词长 2 字

### 停用词过滤
过滤常见虚词、动词、介词等 100+ 个停用词，保留核心名词与关键词。

### 累积统计
每个月份快照包含从第一月到当月的累积词频，展示热点话题的演变。

## 开发

### 环境
```bash
uv venv
source .venv/bin/activate
uv pip install jieba
```

### 更新词频数据
编辑 `word_freq_cumulative.json` 的生成脚本，重新运行：
```bash
python3 scripts/extract_words.py
```

### 修改样式
编辑 `word_freq_viz.html` 的 `<style>` 块，调整颜色、字体、布局。

---

**Last Update** — 2025-03-18
**Data Range** — 2024-12-08 to 2025-08-03
**Built with** — wordcloud2.js + Canvas + jieba
