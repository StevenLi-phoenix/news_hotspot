#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


HEADER_RE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}T[^\s]+)\s+by\s+(?P<model>.+?)\s+#(?P<run_number>\d+)$"
)
HEADER_LINE_RE = re.compile(
    r"(?m)^(?P<header>\d{4}-\d{2}-\d{2}T[^\n]+?\s+by\s+.+?\s+#\d+)\s*$"
)
NUMBERED_ITEM_RE = re.compile(
    r"(?ms)^\s*(?P<index>\d+)\.\s+(?P<text>.*?)(?=^\s*\d+\.\s+|\Z)"
)
BULLET_ITEM_RE = re.compile(
    r"(?ms)^\s*[-*]\s+(?P<text>.*?)(?=^\s*[-*]\s+|\Z)"
)
TITLE_PATTERNS = (
    re.compile(r"^\*\*(?P<title>.+?)\*\*[：:]\s*(?P<summary>.+)$"),
    re.compile(r"^(?P<title>[^：:\n]{1,40})[：:]\s*(?P<summary>.+)$"),
)


@dataclass
class Item:
    item_index: int
    raw_text: str
    title: str | None
    summary: str


@dataclass
class Batch:
    source_line: int
    raw_header: str
    raw_body: str
    generated_at_utc: str
    news_date: str
    model: str
    run_number: int
    items: list[Item]


def normalize_text(text: str) -> str:
    lines = [line.strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return "\n".join(line for line in lines if line).strip()


def extract_title_and_summary(raw_text: str) -> tuple[str | None, str]:
    text = normalize_text(raw_text)
    for pattern in TITLE_PATTERNS:
        match = pattern.match(text)
        if not match:
            continue
        title = match.group("title").strip()
        summary = match.group("summary").strip()
        if any(mark in title for mark in "。！？.!?"):
            continue
        return title, summary
    return None, text


def parse_items(body: str) -> list[Item]:
    numbered_matches = list(NUMBERED_ITEM_RE.finditer(body))
    items: list[Item] = []
    if numbered_matches:
        for match in numbered_matches:
            item_index = int(match.group("index"))
            raw_text = normalize_text(match.group("text"))
            if not raw_text:
                continue
            title, summary = extract_title_and_summary(raw_text)
            items.append(Item(item_index=item_index, raw_text=raw_text, title=title, summary=summary))
        return items

    bullet_matches = list(BULLET_ITEM_RE.finditer(body))
    for offset, match in enumerate(bullet_matches, start=1):
        raw_text = normalize_text(match.group("text"))
        if not raw_text:
            continue
        title, summary = extract_title_and_summary(raw_text)
        items.append(Item(item_index=offset, raw_text=raw_text, title=title, summary=summary))
    return items


def parse_batches(input_path: Path) -> list[Batch]:
    text = input_path.read_text(encoding="utf-8-sig")
    header_matches = list(HEADER_LINE_RE.finditer(text))
    batches: list[Batch] = []

    for idx, match in enumerate(header_matches):
        raw_header = match.group("header").strip()
        header_meta = HEADER_RE.match(raw_header)
        if not header_meta:
            raise ValueError(f"Unrecognized header format: {raw_header}")

        start = match.end()
        end = header_matches[idx + 1].start() if idx + 1 < len(header_matches) else len(text)
        raw_body = text[start:end].strip()
        items = parse_items(raw_body)
        generated_at_utc = header_meta.group("timestamp")
        news_date = generated_at_utc[:10]
        source_line = text.count("\n", 0, match.start()) + 1

        batches.append(
            Batch(
                source_line=source_line,
                raw_header=raw_header,
                raw_body=raw_body,
                generated_at_utc=generated_at_utc,
                news_date=news_date,
                model=header_meta.group("model").strip(),
                run_number=int(header_meta.group("run_number")),
                items=items,
            )
        )

    return batches


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        DROP VIEW IF EXISTS daily_news_selected;
        DROP VIEW IF EXISTS preferred_batches;
        DROP TABLE IF EXISTS date_coverage;
        DROP TABLE IF EXISTS news_items;
        DROP TABLE IF EXISTS source_batches;

        CREATE TABLE source_batches (
            batch_id INTEGER PRIMARY KEY,
            source_file TEXT NOT NULL,
            source_line INTEGER NOT NULL,
            raw_header TEXT NOT NULL,
            raw_body TEXT NOT NULL,
            generated_at_utc TEXT NOT NULL,
            news_date TEXT NOT NULL,
            model TEXT NOT NULL,
            run_number INTEGER NOT NULL,
            item_count INTEGER NOT NULL
        );

        CREATE UNIQUE INDEX idx_source_batches_generated_run
            ON source_batches (generated_at_utc, run_number);
        CREATE INDEX idx_source_batches_news_date
            ON source_batches (news_date, generated_at_utc DESC);

        CREATE TABLE news_items (
            item_id INTEGER PRIMARY KEY,
            batch_id INTEGER NOT NULL REFERENCES source_batches (batch_id) ON DELETE CASCADE,
            news_date TEXT NOT NULL,
            item_index INTEGER NOT NULL,
            title TEXT,
            summary TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            UNIQUE (batch_id, item_index)
        );

        CREATE INDEX idx_news_items_news_date
            ON news_items (news_date, item_index);
        CREATE INDEX idx_news_items_batch
            ON news_items (batch_id, item_index);

        CREATE TABLE date_coverage (
            news_date TEXT PRIMARY KEY,
            batch_count INTEGER NOT NULL,
            selected_batch_id INTEGER REFERENCES source_batches (batch_id),
            selected_item_count INTEGER NOT NULL,
            has_exact_five_batch INTEGER NOT NULL,
            missing INTEGER NOT NULL
        );

        CREATE VIEW preferred_batches AS
        WITH ranked AS (
            SELECT
                sb.*,
                ROW_NUMBER() OVER (
                    PARTITION BY sb.news_date
                    ORDER BY
                        CASE WHEN sb.item_count = 5 THEN 0 ELSE 1 END,
                        sb.generated_at_utc DESC,
                        sb.run_number DESC,
                        sb.batch_id DESC
                ) AS preference_rank
            FROM source_batches AS sb
        )
        SELECT
            batch_id,
            source_file,
            source_line,
            raw_header,
            raw_body,
            generated_at_utc,
            news_date,
            model,
            run_number,
            item_count,
            preference_rank
        FROM ranked
        WHERE preference_rank = 1;

        CREATE VIEW daily_news_selected AS
        SELECT
            pb.news_date,
            ni.item_index AS rank,
            ni.title,
            ni.summary,
            ni.raw_text,
            ni.item_id,
            pb.batch_id,
            pb.generated_at_utc,
            pb.model,
            pb.run_number,
            pb.item_count AS source_item_count,
            CASE
                WHEN pb.item_count = 5 THEN 'exact_5_batch'
                ELSE 'truncated_to_5'
            END AS selection_strategy
        FROM preferred_batches AS pb
        JOIN news_items AS ni
            ON ni.batch_id = pb.batch_id
        WHERE ni.item_index <= 5
        ORDER BY pb.news_date, ni.item_index;
        """
    )


def populate_db(conn: sqlite3.Connection, input_path: Path, batches: list[Batch]) -> dict[str, int]:
    batch_ids_by_date: defaultdict[str, list[tuple[int, Batch]]] = defaultdict(list)
    total_items = 0

    for batch in batches:
        cursor = conn.execute(
            """
            INSERT INTO source_batches (
                source_file,
                source_line,
                raw_header,
                raw_body,
                generated_at_utc,
                news_date,
                model,
                run_number,
                item_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                input_path.name,
                batch.source_line,
                batch.raw_header,
                batch.raw_body,
                batch.generated_at_utc,
                batch.news_date,
                batch.model,
                batch.run_number,
                len(batch.items),
            ),
        )
        batch_id = cursor.lastrowid
        batch_ids_by_date[batch.news_date].append((batch_id, batch))

        for item in batch.items:
            conn.execute(
                """
                INSERT INTO news_items (
                    batch_id,
                    news_date,
                    item_index,
                    title,
                    summary,
                    raw_text
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    batch_id,
                    batch.news_date,
                    item.item_index,
                    item.title,
                    item.summary,
                    item.raw_text,
                ),
            )
            total_items += 1

    all_dates = sorted(batch_ids_by_date)
    start_date = date.fromisoformat(all_dates[0])
    end_date = date.fromisoformat(all_dates[-1])
    current_date = start_date

    while current_date <= end_date:
        news_date = current_date.isoformat()
        batches_for_day = batch_ids_by_date.get(news_date, [])
        if batches_for_day:
            preferred_batch_id, preferred_batch = max(
                batches_for_day,
                key=lambda pair: (
                    1 if len(pair[1].items) == 5 else 0,
                    pair[1].generated_at_utc,
                    pair[1].run_number,
                    pair[0],
                ),
            )
            conn.execute(
                """
                INSERT INTO date_coverage (
                    news_date,
                    batch_count,
                    selected_batch_id,
                    selected_item_count,
                    has_exact_five_batch,
                    missing
                )
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                (
                    news_date,
                    len(batches_for_day),
                    preferred_batch_id,
                    min(len(preferred_batch.items), 5),
                    1 if any(len(batch.items) == 5 for _, batch in batches_for_day) else 0,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO date_coverage (
                    news_date,
                    batch_count,
                    selected_batch_id,
                    selected_item_count,
                    has_exact_five_batch,
                    missing
                )
                VALUES (?, 0, NULL, 0, 0, 1)
                """,
                (news_date,),
            )
        current_date += timedelta(days=1)

    return {
        "batch_count": len(batches),
        "distinct_date_count": len(all_dates),
        "item_count": total_items,
        "start_date": all_dates[0],
        "end_date": all_dates[-1],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse news-zhcn.txt and import it into SQLite.")
    parser.add_argument(
        "--input",
        default="news-zhcn.txt",
        help="Path to the source text file. Default: news-zhcn.txt",
    )
    parser.add_argument(
        "--output",
        default="news_zhcn.sqlite",
        help="Path to the SQLite database file. Default: news_zhcn.sqlite",
    )
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    batches = parse_batches(input_path)

    with sqlite3.connect(output_path) as conn:
        create_schema(conn)
        stats = populate_db(conn, input_path, batches)
        conn.commit()

        missing_date_count = conn.execute(
            "SELECT COUNT(*) FROM date_coverage WHERE missing = 1"
        ).fetchone()[0]
        selected_rows = conn.execute(
            "SELECT COUNT(*) FROM daily_news_selected"
        ).fetchone()[0]

    print(f"Imported {stats['batch_count']} batches and {stats['item_count']} news items.")
    print(
        f"Coverage range: {stats['start_date']} to {stats['end_date']} "
        f"across {stats['distinct_date_count']} dates."
    )
    print(f"Missing dates in range: {missing_date_count}")
    print(f"Rows available in daily_news_selected: {selected_rows}")
    print(f"SQLite database written to: {output_path}")


if __name__ == "__main__":
    main()
