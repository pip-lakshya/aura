"""AURA application entry point."""

from __future__ import annotations

import sys
import threading
import time
from typing import Any

import requests
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from config import load_env

load_env()

import server
from database import init_db
from ui import AuraWindow
from voice import listen_and_transcribe, speak, start_wake_word_loop, stop_speaking


API_URL = "http://127.0.0.1:5000"
QUESTION_STARTS = (
    "what",
    "when",
    "where",
    "who",
    "how",
    "did",
    "show",
    "tell",
    "find",
    "search",
    "recall",
    "list",
    "give",
    "do",
    "can",
    "why",
    "which",
)
QUESTION_PHRASES = (
    "tell me",
    "show me",
    "find me",
    "search for",
    "what about",
    "anything about",
    "tell me more",
)

CONVERSATION_HISTORY: list[dict[str, str]] = []
HISTORY_LOCK = threading.Lock()


class UiBridge(QObject):
    add_message = pyqtSignal(str, str)
    set_input = pyqtSignal(str)
    set_status = pyqtSignal(str)
    process_text = pyqtSignal(str)


def is_question(text: str) -> bool:
    normalized = text.strip().lower()
    return (
        normalized.endswith("?")
        or normalized.startswith(QUESTION_STARTS)
        or any(phrase in normalized for phrase in QUESTION_PHRASES)
    )


def _history_snapshot() -> list[dict[str, str]]:
    with HISTORY_LOCK:
        return list(CONVERSATION_HISTORY[-10:])


def _remember_turn(role: str, content: str) -> None:
    if not content.strip():
        return
    with HISTORY_LOCK:
        CONVERSATION_HISTORY.append({"role": role, "content": content.strip()})
        del CONVERSATION_HISTORY[:-12]


def start_flask_server() -> threading.Thread:
    def run() -> None:
        server.app.run(
            host="127.0.0.1",
            port=5000,
            debug=False,
            use_reloader=False,
            threaded=True,
        )

    thread = threading.Thread(target=run, name="aura-flask-server", daemon=True)
    thread.start()
    return thread


def wait_for_server(timeout: float = 8.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = requests.get(f"{API_URL}/health", timeout=0.5)
            if response.ok:
                return True
        except requests.RequestException:
            time.sleep(0.2)
    return False


def post_to_aura(text: str) -> str:
    query = is_question(text)
    endpoint = "/query" if query else "/memory"
    payload: dict[str, Any] = {"query" if query else "text": text}
    if query:
        payload["history"] = _history_snapshot()

    response = requests.post(f"{API_URL}{endpoint}", json=payload, timeout=180)
    response.raise_for_status()
    data = response.json()

    if query:
        return str(data.get("answer", "")).strip() or "I could not form an answer."

    return "Memory saved."


def handle_text(text: str, bridge: UiBridge, speak_response: bool = True) -> None:
    input_text = text.strip()
    if not input_text:
        bridge.set_status.emit("IDLE")
        return

    bridge.add_message.emit("user", input_text)
    _remember_turn("user", input_text)
    bridge.set_status.emit("THINKING...")

    try:
        answer = post_to_aura(input_text)
    except requests.RequestException as exc:
        answer = f"I cannot reach the local AURA server right now: {exc}"

    bridge.add_message.emit("aura", answer)
    _remember_turn("assistant", answer)

    if speak_response:
        bridge.set_status.emit("SPEAKING")
        try:
            speak(
                answer,
                on_start=None,
                on_end=lambda: bridge.set_status.emit("IDLE"),
            )
        except Exception as exc:
            bridge.add_message.emit("aura", f"Speech output is unavailable: {exc}")
            bridge.set_status.emit("IDLE")
    else:
        bridge.set_status.emit("IDLE")


def start_text_worker(text: str, bridge: UiBridge, speak_response: bool = True) -> None:
    thread = threading.Thread(
        target=handle_text,
        args=(text, bridge, speak_response),
        name="aura-text-worker",
        daemon=True,
    )
    thread.start()


def handle_wake_activation(bridge: UiBridge) -> None:
    bridge.set_status.emit("LISTENING")

    try:
        input_text = listen_and_transcribe()
    except Exception as exc:
        bridge.add_message.emit("aura", f"Voice input failed: {exc}")
        bridge.set_status.emit("IDLE")
        return

    if not input_text:
        bridge.add_message.emit("aura", "I did not hear clear speech.")
        bridge.set_status.emit("IDLE")
        return

    bridge.set_input.emit(input_text)
    time.sleep(0.4)
    handle_text(input_text, bridge, speak_response=True)
    bridge.set_input.emit("")


def start_voice_input_worker(bridge: UiBridge) -> None:
    thread = threading.Thread(
        target=handle_wake_activation,
        args=(bridge,),
        name="aura-voice-worker",
        daemon=True,
    )
    thread.start()


def main() -> int:
    init_db()
    start_flask_server()

    app = QApplication(sys.argv)
    window = AuraWindow()
    bridge = UiBridge()

    bridge.add_message.connect(window.add_message)
    bridge.set_input.connect(window.set_input_text)
    bridge.set_status.connect(window.set_status)
    bridge.process_text.connect(lambda text: start_text_worker(text, bridge, True))
    window.message_submitted.connect(bridge.process_text.emit)
    window.mic_requested.connect(lambda: start_voice_input_worker(bridge))
    window.stop_requested.connect(lambda: (stop_speaking(), bridge.set_status.emit("IDLE")))

    window.add_message("AURA", "Systems online. I am ready.")

    if wait_for_server():
        window.add_message("AURA", "Local memory server connected.")
    else:
        window.add_message("AURA", "Local memory server is still starting.")

    try:
        start_wake_word_loop(
            lambda: start_voice_input_worker(bridge),
            on_error=lambda message: bridge.add_message.emit(
                "aura", f"Wake-word error: {message}"
            ),
        )
        window.add_message("AURA", "Wake-word listener started.")
    except Exception as exc:
        window.add_message("AURA", f"Wake-word listening is unavailable: {exc}")

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
