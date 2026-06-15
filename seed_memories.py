"""Seed AURA with realistic demo memories."""

from __future__ import annotations

from datetime import datetime, timedelta

import sqlite3

from database import DB_PATH, init_db, save_memory


DEMO_MEMORIES = [
    (
        "Prepared internship standup notes about the authentication API refactor.",
        "internship",
        "work",
        "focused",
        8,
        ["internship", "api", "standup"],
        1,
    ),
    (
        "Reviewed Flask routing and learned how request validation should be handled.",
        "backend learning",
        "study",
        "curious",
        7,
        ["flask", "backend", "study"],
        3,
    ),
    (
        "College database systems lecture covered normalization and foreign keys.",
        "database systems",
        "college",
        "neutral",
        6,
        ["college", "database", "normalization"],
        5,
    ),
    (
        "Idea: make AURA summarize the day every night and suggest tomorrow priorities.",
        "AURA idea",
        "idea",
        "excited",
        9,
        ["aura", "planning", "idea"],
        7,
    ),
    (
        "Finished a lab assignment on operating system process scheduling.",
        "operating systems",
        "college",
        "relieved",
        6,
        ["college", "os", "assignment"],
        8,
    ),
    (
        "Internship mentor suggested writing smaller pull requests with clearer descriptions.",
        "internship feedback",
        "work",
        "motivated",
        8,
        ["internship", "feedback", "pull-request"],
        10,
    ),
    (
        "Studied PyQt signals and slots for keeping UI updates thread safe.",
        "PyQt",
        "study",
        "focused",
        8,
        ["pyqt", "signals", "ui"],
        11,
    ),
    (
        "Had a college group discussion about final year project ideas.",
        "project ideas",
        "college",
        "thoughtful",
        7,
        ["college", "project", "ideas"],
        13,
    ),
    (
        "Idea: add voice mood detection so AURA can tag memories with emotional context.",
        "voice emotion idea",
        "idea",
        "excited",
        8,
        ["voice", "emotion", "aura"],
        15,
    ),
    (
        "Practiced SQL joins using memories and tags as a sample schema.",
        "SQL joins",
        "study",
        "confident",
        7,
        ["sql", "database", "practice"],
        17,
    ),
    (
        "Internship task involved debugging a timeout between frontend and backend services.",
        "service timeout",
        "work",
        "challenged",
        9,
        ["internship", "debugging", "backend"],
        19,
    ),
    (
        "Read about local LLMs and why Ollama is useful for private assistant workflows.",
        "local LLMs",
        "study",
        "curious",
        7,
        ["ollama", "llm", "privacy"],
        21,
    ),
    (
        "College exam prep focused on computer networks, especially TCP and DNS.",
        "computer networks",
        "college",
        "determined",
        8,
        ["college", "networks", "exam"],
        23,
    ),
    (
        "Idea: create a memory importance dashboard that highlights high-value patterns.",
        "memory dashboard",
        "idea",
        "creative",
        7,
        ["dashboard", "aura", "analytics"],
        26,
    ),
    (
        "Updated internship notes after learning a cleaner way to structure API errors.",
        "API errors",
        "work",
        "satisfied",
        8,
        ["internship", "api", "errors"],
        29,
    ),
]


def seed() -> None:
    init_db()

    for content, topic, category, emotion, importance, tags, days_ago in DEMO_MEMORIES:
        memory = save_memory(
            content=content,
            topic=topic,
            category=category,
            emotion=emotion,
            importance=importance,
            tags_list=tags,
        )
        timestamp = (datetime.now() - timedelta(days=days_ago)).isoformat(
            timespec="seconds"
        )

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "UPDATE memories SET timestamp = ? WHERE memory_id = ?",
                (timestamp, memory["memory_id"]),
            )

    print(f"Seeded {len(DEMO_MEMORIES)} demo memories into {DB_PATH}.")


if __name__ == "__main__":
    seed()
