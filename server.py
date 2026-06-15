"""Flask backend for AURA."""

from __future__ import annotations

from typing import Any

from flask import Flask, jsonify, request

from ai_brain import answer_query, tag_memory
from database import (
    get_all_memories,
    get_stats,
    init_db,
    log_retrieval,
    save_memory,
    search_memories,
)


app = Flask(__name__)

try:
    from flask_cors import CORS

    CORS(app)
except ImportError:

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        return response


def _json_error(message: str, status_code: int = 400):
    response = jsonify({"error": message})
    response.status_code = status_code
    return response


def _get_json_body() -> dict[str, Any] | None:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def _tags_list(tags: dict[str, Any]) -> list[str]:
    return [
        str(value).strip()
        for key in ("topic", "category", "emotion")
        if (value := tags.get(key))
    ]


@app.route("/memory", methods=["POST", "OPTIONS"])
def create_memory():
    if request.method == "OPTIONS":
        return jsonify({})

    data = _get_json_body()
    if data is None:
        return _json_error("Request body must be valid JSON.")

    text = str(data.get("text", "")).strip()
    if not text:
        return _json_error("Missing required field: text.")

    tags = tag_memory(text)
    save_memory(
        content=text,
        topic=tags.get("topic", ""),
        category=tags.get("category", ""),
        emotion=tags.get("emotion", ""),
        importance=tags.get("importance", ""),
        tags_list=_tags_list(tags),
    )

    return jsonify({"status": "saved", "tags": tags})


@app.route("/query", methods=["POST", "OPTIONS"])
def query_memories():
    if request.method == "OPTIONS":
        return jsonify({})

    data = _get_json_body()
    if data is None:
        return _json_error("Request body must be valid JSON.")

    query = str(data.get("query", "")).strip()
    if not query:
        return _json_error("Missing required field: query.")

    history = data.get("history", [])
    if not isinstance(history, list):
        history = []

    search_text = query
    for item in history[-4:]:
        if isinstance(item, dict):
            search_text += " " + str(item.get("content", ""))

    results = search_memories(search_text)
    answer = answer_query(query, results, history)
    log_retrieval(query, {"results": results, "answer": answer})

    return jsonify({"answer": answer})


@app.route("/memories", methods=["GET"])
def memories():
    return jsonify(get_all_memories())


@app.route("/stats", methods=["GET"])
def stats():
    return jsonify(get_stats())


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)

