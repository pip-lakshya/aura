"""SQLite storage layer for AURA, an AI-powered personal memory system."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any
import os
import sys
from pathlib import Path

def get_base_path():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent

BASE_DIR = get_base_path()

DB_PATH = BASE_DIR / "aura_memory.db"

SEARCH_STOPWORDS = {
    "a",
    "about",
    "all",
    "an",
    "and",
    "anything",
    "can",
    "did",
    "do",
    "for",
    "give",
    "how",
    "i",
    "list",
    "me",
    "of",
    "on",
    "recall",
    "search",
    "show",
    "tell",
    "the",
    "to",
    "what",
    "when",
    "where",
    "who",
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def _memory_from_row(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    memory = _row_to_dict(row)
    memory["tags"] = [
        tag_row["tag_name"]
        for tag_row in conn.execute(
            """
            SELECT t.tag_name
            FROM tags AS t
            JOIN memory_tags AS mt ON mt.tag_id = t.tag_id
            WHERE mt.memory_id = ?
            ORDER BY t.tag_name
            """,
            (memory["memory_id"],),
        )
    ]
    return memory


def init_db() -> dict[str, Any]:
    """Create all AURA database tables if they do not already exist."""
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS memories (
                memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                topic TEXT,
                category TEXT,
                emotion TEXT,
                importance INTEGER
            );

            CREATE TABLE IF NOT EXISTS tags (
                tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS memory_tags (
                memory_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (memory_id, tag_id),
                FOREIGN KEY (memory_id) REFERENCES memories(memory_id)
                    ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(tag_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS retrieval_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                results TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS knowledge_triples (
                triple_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                relation TEXT NOT NULL,
                target TEXT NOT NULL,
                memory_id INTEGER,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (memory_id) REFERENCES memories(memory_id) ON DELETE CASCADE
            );
            """
        )
    return {"success": True, "database": str(DB_PATH)}


def save_memory(
    content: str,
    topic: str | None,
    category: str | None,
    emotion: str | None,
    importance: int | None,
    tags_list: list[str] | tuple[str, ...] | None,
) -> dict[str, Any]:
    """Insert a memory and attach any provided tags."""
    timestamp = _now()
    normalized_tags = sorted(
        {
            str(tag).strip()
            for tag in (tags_list or [])
            if str(tag).strip()
        }
    )

    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO memories (
                content, timestamp, topic, category, emotion, importance
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (content, timestamp, topic, category, emotion, importance),
        )
        memory_id = cursor.lastrowid

        for tag_name in normalized_tags:
            conn.execute(
                "INSERT OR IGNORE INTO tags (tag_name) VALUES (?)",
                (tag_name,),
            )
            tag_row = conn.execute(
                "SELECT tag_id FROM tags WHERE tag_name = ?",
                (tag_name,),
            ).fetchone()
            conn.execute(
                """
                INSERT OR IGNORE INTO memory_tags (memory_id, tag_id)
                VALUES (?, ?)
                """,
                (memory_id, tag_row["tag_id"]),
            )

        row = conn.execute(
            "SELECT * FROM memories WHERE memory_id = ?",
            (memory_id,),
        ).fetchone()
        return _memory_from_row(conn, row)


def get_all_memories() -> list[dict[str, Any]]:
    """Return every saved memory as a clean dictionary."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM memories ORDER BY timestamp DESC, memory_id DESC"
        ).fetchall()
        return [_memory_from_row(conn, row) for row in rows]


def search_memories(query: str) -> list[dict[str, Any]]:
    """Search memory content, topic, and category columns using LIKE."""
    terms = [
        term
        for term in re.findall(r"[A-Za-z0-9_]+", query.lower())
        if len(term) > 1 and term not in SEARCH_STOPWORDS
    ]
    if not terms:
        terms = [query.strip()]

    with _connect() as conn:
        where_parts = []
        params = []
        for term in terms:
            like_query = f"%{term}%"
            where_parts.append(
                "(LOWER(content) LIKE ? OR LOWER(topic) LIKE ? OR LOWER(category) LIKE ?)"
            )
            params.extend([like_query, like_query, like_query])

        rows = conn.execute(
            f"""
            SELECT *
            FROM memories
            WHERE {" OR ".join(where_parts)}
            ORDER BY timestamp DESC, memory_id DESC
            """,
            params,
        ).fetchall()
        results = [_memory_from_row(conn, row) for row in rows]

    return results


def get_stats() -> dict[str, Any]:
    """Return total memory count, top topic, and most active day."""
    with _connect() as conn:
        total_count = conn.execute(
            "SELECT COUNT(*) AS count FROM memories"
        ).fetchone()["count"]

        top_topic_row = conn.execute(
            """
            SELECT topic, COUNT(*) AS count
            FROM memories
            WHERE topic IS NOT NULL AND TRIM(topic) != ''
            GROUP BY topic
            ORDER BY count DESC, topic ASC
            LIMIT 1
            """
        ).fetchone()

        most_active_day_row = conn.execute(
            """
            SELECT DATE(timestamp) AS day, COUNT(*) AS count
            FROM memories
            GROUP BY day
            ORDER BY count DESC, day DESC
            LIMIT 1
            """
        ).fetchone()

    return {
        "total_count": total_count,
        "top_topic": top_topic_row["topic"] if top_topic_row else None,
        "top_topic_count": top_topic_row["count"] if top_topic_row else 0,
        "most_active_day": most_active_day_row["day"] if most_active_day_row else None,
        "most_active_day_count": (
            most_active_day_row["count"] if most_active_day_row else 0
        ),
    }


def log_retrieval(query: str, results: Any) -> dict[str, Any]:
    """Log a retrieval query and its results as JSON."""
    timestamp = _now()
    serialized_results = json.dumps(results, ensure_ascii=True, default=str)

    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO retrieval_logs (query, timestamp, results)
            VALUES (?, ?, ?)
            """,
            (query, timestamp, serialized_results),
        )
        log_id = cursor.lastrowid

    return {
        "log_id": log_id,
        "query": query,
        "timestamp": timestamp,
        "results": results,
    }


def save_triple(
    source: str,
    relation: str,
    target: str,
    memory_id: int | None = None,
) -> dict[str, Any]:
    """Insert a knowledge triple relationship into the database."""
    timestamp = _now()
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO knowledge_triples (source, relation, target, memory_id, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (source.strip(), relation.strip(), target.strip(), memory_id, timestamp),
        )
        triple_id = cursor.lastrowid
    return {
        "triple_id": triple_id,
        "source": source,
        "relation": relation,
        "target": target,
        "memory_id": memory_id,
        "timestamp": timestamp,
    }


def get_all_triples() -> list[dict[str, Any]]:
    """Return all saved knowledge triples."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM knowledge_triples ORDER BY timestamp DESC, triple_id DESC"
        ).fetchall()
        return [_row_to_dict(row) for row in rows]

