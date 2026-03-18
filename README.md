# news_hotspot

将 [news-zhcn.txt](/Users/lishuyu/Codes/news_hotspot/news-zhcn.txt) 中的中文新闻摘要解析后导入 SQLite。

当前仓库包含：
- [news-zhcn.txt](/Users/lishuyu/Codes/news_hotspot/news-zhcn.txt)：原始文本数据。
- [import_news_zhcn_to_sqlite.py](/Users/lishuyu/Codes/news_hotspot/import_news_zhcn_to_sqlite.py)：导入脚本。
- [news_zhcn.sqlite](/Users/lishuyu/Codes/news_hotspot/news_zhcn.sqlite)：已生成的 SQLite 数据库。

## 数据说明

原始文件并不是完全规整的“每天固定 5 条”格式，实际存在这些情况：
- 同一天有多个生成批次。
- 部分早期批次超过 5 条。
- 少数日期不足 5 条。
- 区间内存在缺失日期。

因此数据库同时保留了：
- 原始批次数据
- 拆分后的新闻条目
- 每天的“首选批次”
- 最终便于消费的“每日新闻”视图

## 重新导入

```bash
python3 import_news_zhcn_to_sqlite.py
```

可选参数：

```bash
python3 import_news_zhcn_to_sqlite.py --input news-zhcn.txt --output news_zhcn.sqlite
```

## SQLite 结构

### `source_batches`

保存原始批次：
- `generated_at_utc`：批次时间戳
- `news_date`：按批次时间戳截出的日期
- `model`：生成模型
- `run_number`：批次编号
- `raw_header` / `raw_body`：原始文本
- `item_count`：该批次识别出的新闻条数

### `news_items`

保存拆分后的新闻项：
- `news_date`
- `item_index`
- `title`
- `summary`
- `raw_text`

### `date_coverage`

保存日期覆盖情况：
- `batch_count`：当天批次数
- `selected_batch_id`：当天首选批次
- `selected_item_count`：最终选中的条数
- `has_exact_five_batch`：是否存在恰好 5 条的批次
- `missing`：该日期是否缺失

### `preferred_batches`

每天选一个首选批次，规则为：
1. 优先选择恰好 5 条的批次
2. 若没有 5 条批次，选择当天最新批次

### `daily_news_selected`

面向直接查询的最终视图：
- 每天输出最多 5 条新闻
- 如果首选批次多于 5 条，只取前 5 条
- 如果首选批次少于 5 条，则保留实际条数

## 常用查询

查询某天的最终新闻：

```bash
sqlite3 news_zhcn.sqlite "SELECT news_date, rank, title, summary FROM daily_news_selected WHERE news_date='2025-08-03';"
```

查询缺失日期：

```bash
sqlite3 news_zhcn.sqlite "SELECT news_date FROM date_coverage WHERE missing=1 ORDER BY news_date;"
```

查询存在多个批次的日期：

```bash
sqlite3 news_zhcn.sqlite "SELECT news_date, batch_count FROM date_coverage WHERE batch_count > 1 ORDER BY news_date;"
```

查询原始批次：

```bash
sqlite3 news_zhcn.sqlite "SELECT batch_id, news_date, generated_at_utc, item_count FROM source_batches ORDER BY generated_at_utc LIMIT 20;"
```

## 当前导入结果

基于当前 [news-zhcn.txt](/Users/lishuyu/Codes/news_hotspot/news-zhcn.txt) 的导入结果：
- 217 个原始批次
- 1193 条拆分后的新闻
- 205 个有数据的日期
- 34 个缺失日期

时间范围：
- `2024-12-08` 到 `2025-08-03`
