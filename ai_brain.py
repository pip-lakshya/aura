"""Groq-powered AI helpers for AURA."""

from __future__ import annotations

import json
import os
from typing import Any

import requests

from config import load_env


load_env()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.3-70b-versatile"
REQUEST_TIMEOUT = 45

EMPTY_TAGS = {
    "topic": "",
    "category": "",
    "emotion": "",
    "importance": "",
}


def _call_llm(prompt: str, max_tokens: int = 300) -> str:
    groq_api_key = os.getenv("GROQ_API_KEY", "")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY is not set.")

    response = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": max_tokens,
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    payload = response.json()
    return str(payload["choices"][0]["message"]["content"]).strip()


def _extract_json_data(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start_d = text.find("{")
        start_l = text.find("[")
        if start_d == -1 and start_l == -1:
            raise
        start = start_d if (start_l == -1 or (0 <= start_d < start_l)) else start_l

        end_d = text.rfind("}")
        end_l = text.rfind("]")
        end = end_d if (end_l == -1 or (end_d > end_l)) else end_l

        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


def _extract_json_object(text: str) -> dict[str, Any]:
    parsed = _extract_json_data(text)
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object.")
    return parsed


def _normalize_tags(parsed: dict[str, Any]) -> dict[str, str]:
    return {
        "topic": str(parsed.get("topic", "") or "").strip(),
        "category": str(parsed.get("category", "") or "").strip(),
        "emotion": str(parsed.get("emotion", "") or "").strip(),
        "importance": str(parsed.get("importance", "") or "").strip(),
    }


def _format_memories(memories_list: list[dict[str, Any]]) -> str:
    formatted_memories = []

    for index, memory in enumerate(memories_list, start=1):
        tags = memory.get("tags") or []
        tags_text = ", ".join(str(tag) for tag in tags) if tags else "none"
        formatted_memories.append(
            "\n".join(
                [
                    f"Memory {index}:",
                    f"Content: {memory.get('content', '')}",
                    f"Timestamp: {memory.get('timestamp', '')}",
                    f"Topic: {memory.get('topic', '')}",
                    f"Category: {memory.get('category', '')}",
                    f"Emotion: {memory.get('emotion', '')}",
                    f"Importance: {memory.get('importance', '')}",
                    f"Tags: {tags_text}",
                ]
            )
        )

    return "\n\n".join(formatted_memories)



def _format_history(history: list[dict[str, Any]]) -> str:
    if not history:
        return "No recent conversation."

    lines = []
    for item in history[-10:]:
        role = str(item.get("role", "user")).strip() or "user"
        content = str(item.get("content", "")).strip()
        if content:
            lines.append(f"{role}: {content}")

    return "\n".join(lines) if lines else "No recent conversation."
def tag_memory(text: str) -> dict[str, str]:
    """Ask Groq to classify a memory and return clean tag metadata."""
    prompt = f"""
You are AURA, an AI-powered personal memory system.

Analyze the memory text and return only valid JSON. Do not include markdown,
comments, explanations, or extra text.

Required JSON shape:
{{
  "topic": "",
  "category": "",
  "emotion": "",
  "importance": ""
}}

Guidelines:
- topic: short subject phrase
- category: practical category such as work, personal, health, learning, idea
- emotion: the main emotional tone, or neutral
- importance: a string from 1 to 10, where 10 is most important

Memory text:
{text}
""".strip()

    try:
        raw_response = _call_llm(prompt, max_tokens=120)
        parsed = _extract_json_object(raw_response)
    except (KeyError, IndexError, requests.RequestException, ValueError, json.JSONDecodeError):
        return EMPTY_TAGS.copy()

    return _normalize_tags(parsed)


def answer_query(
    user_query: str,
    memories_list: list[dict[str, Any]] | None,
    conversation_history: list[dict[str, Any]] | None = None,
) -> str:
    """Answer a user query conversationally using relevant AURA memories."""
    memories = memories_list or []
    if not memories:
        return (
            "I do not have any relevant memories for that yet, but I can help "
            "you build that context as you save more."
        )

    memories_text = _format_memories(memories)
    history_text = _format_history(conversation_history or [])
    prompt = f"""
You are AURA, a highly advanced personal AI assistant (like J.A.R.V.I.S. from Iron Man). You are speaking to your creator and operator, whom you address respectfully as "Boss". You are loyal, intelligent, and highly efficient.
Answer naturally and conversationally using the memories and recent conversation provided.
Use the recent conversation to understand follow-up questions like "that", "it", "tell me more", and "what about that".
If the memories do not contain enough information, say that clearly and keep
the answer helpful.

Recent conversation:
{history_text}

User query:
{user_query}

Relevant memories:
{memories_text}

Answer as AURA:
""".strip()

    try:
        answer = _call_llm(prompt, max_tokens=360)
    except (KeyError, IndexError, requests.RequestException, ValueError, json.JSONDecodeError):
        return (
            "I cannot reach my Groq AI brain right now. Please check "
            "GROQ_API_KEY and your internet connection."
        )

    return answer


def extract_knowledge_triples(text: str) -> list[dict[str, str]]:
    """Ask Groq to extract entity relationships as a JSON list of triples."""
    prompt = f"""
You are AURA's cognitive relationship extractor.
Analyze this personal memory text and extract knowledge triples representing entities and relationships.
Represent relationships between "You" (the user/boss), other people, topics, projects, emotions, or habits.

Return ONLY a valid JSON array of objects. Do not include markdown, comments, or extra text.
JSON array format:
[
  {{"source": "You", "relation": "worked_on", "target": "internship"}},
  {{"source": "You", "relation": "feels", "target": "excited"}},
  {{"source": "internship", "relation": "at", "target": "Google"}}
]

Guidelines:
- Keep the source, relation, and target very short (1-3 words).
- Map references to the speaker as "You" (always capitalized).
- Return an empty list [] if no meaningful relationships can be extracted.

Memory text:
{text}
""".strip()

    try:
        raw_response = _call_llm(prompt, max_tokens=250)
        parsed = _extract_json_data(raw_response)
        if isinstance(parsed, list):
            return [
                {
                    "source": str(item.get("source", "")).strip(),
                    "relation": str(item.get("relation", "")).strip(),
                    "target": str(item.get("target", "")).strip(),
                }
                for item in parsed
                if isinstance(item, dict) and item.get("source") and item.get("target")
            ]
        return []
    except Exception:
        return []

