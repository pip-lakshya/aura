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
from voice import (
    speak,
    stop_speaking,
    AuraAudioEngine,
    transcribe_audio,
    _get_sr_device_index,
)

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

    # HUD status and analytics signals
    update_mic_level = pyqtSignal(float, float)  # (rms, peak)
    update_spk_level = pyqtSignal(float, float)  # (rms, peak)
    update_graph = pyqtSignal(list)              # list of triples
    set_caption = pyqtSignal(str)


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


def refresh_graph(bridge: UiBridge) -> None:
    """Fetch all triples from server and update UI graph."""
    try:
        response = requests.get(f"{API_URL}/graph", timeout=5)
        if response.ok:
            bridge.update_graph.emit(response.json())
    except Exception:
        pass


def handle_text(
    text: str,
    bridge: UiBridge,
    window: AuraWindow,
    audio_engine: AuraAudioEngine,
    speak_response: bool = True,
) -> None:
    input_text = text.strip()
    if not input_text:
        bridge.set_status.emit("IDLE")
        audio_engine.set_state("wake_word")
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

    # Always refresh knowledge graph nodes after updates
    refresh_graph(bridge)

    # Only speak if not muted in the UI
    if speak_response and not window.is_muted():
        bridge.set_status.emit("SPEAKING")
        bridge.set_caption.emit(answer)
        try:
            speak(
                answer,
                on_start=None,
                on_end=lambda: (
                    bridge.set_status.emit("IDLE"),
                    bridge.update_spk_level.emit(0.0, 0.0),
                    audio_engine.set_state("wake_word") # resume wake word listening
                ),
                on_level=lambda rms, peak: bridge.update_spk_level.emit(rms, peak),
            )
        except Exception as exc:
            bridge.add_message.emit("aura", f"Speech output is unavailable: {exc}")
            bridge.set_status.emit("IDLE")
            bridge.update_spk_level.emit(0.0, 0.0)
            audio_engine.set_state("wake_word")
    else:
        bridge.set_status.emit("IDLE")
        bridge.update_spk_level.emit(0.0, 0.0)
        audio_engine.set_state("wake_word") # resume wake word listening


def start_text_worker(
    text: str,
    bridge: UiBridge,
    window: AuraWindow,
    audio_engine: AuraAudioEngine,
    speak_response: bool = True,
) -> None:
    thread = threading.Thread(
        target=handle_text,
        args=(text, bridge, window, audio_engine, speak_response),
        name="aura-text-worker",
        daemon=True,
    )
    thread.start()


def main() -> int:
    init_db()
    start_flask_server()

    app = QApplication(sys.argv)
    window = AuraWindow()
    bridge = UiBridge()

    # Bridge signal wiring
    bridge.add_message.connect(window.add_message)
    bridge.set_input.connect(window.set_input_text)
    bridge.set_status.connect(window.set_status)
    bridge.set_caption.connect(window.set_caption)
    bridge.update_mic_level.connect(window.update_mic_level)
    bridge.update_spk_level.connect(window.update_spk_level)
    bridge.update_graph.connect(window.graph_widget.set_triples)

    # Single persistent audio engine setup
    device_index = _get_sr_device_index()
    audio_engine = AuraAudioEngine(device_index=device_index, sample_rate=48000)

    # Wire text submission
    bridge.process_text.connect(lambda text: start_text_worker(text, bridge, window, audio_engine, True))
    window.message_submitted.connect(bridge.process_text.emit)

    # Wire wake word callback
    def on_wake():
        # Stop any active speaking before starting transcription
        stop_speaking()
        bridge.set_status.emit("LISTENING")
        audio_engine.set_state("recording")

    # Wire voice transcription callback
    def on_record_done(audio):
        bridge.set_status.emit("TRANSCRIBING")
        try:
            text = transcribe_audio(audio)
            if text:
                bridge.set_input.emit(text)
                time.sleep(0.4)
                start_text_worker(text, bridge, window, audio_engine, True)
                bridge.set_input.emit("")
            else:
                bridge.add_message.emit("aura", "I did not hear clear speech.")
                bridge.set_status.emit("IDLE")
                audio_engine.set_state("wake_word")
        except Exception as exc:
            bridge.add_message.emit("aura", f"Voice input failed: {exc}")
            bridge.set_status.emit("IDLE")
            audio_engine.set_state("wake_word")

    # Start the single persistent audio engine
    audio_engine.start(
        on_level=lambda rms, peak: bridge.update_mic_level.emit(rms, peak),
        on_wake=on_wake,
        on_record_done=on_record_done
    )

    # Set state initially to listen for the wake word
    audio_engine.set_state("wake_word")

    # Wire MIC button to toggle recording state
    window.mic_requested.connect(lambda: (
        stop_speaking(),
        bridge.set_status.emit("LISTENING"),
        audio_engine.set_state("recording")
    ))

    # Wire STOP button to halt speech and go back to wake word monitoring
    window.stop_requested.connect(lambda: (
        stop_speaking(),
        bridge.set_status.emit("IDLE"),
        audio_engine.set_state("wake_word")
    ))

    window.add_message("AURA", "Systems online. I am ready, Boss.")

    # Clean shutdown hook for audio engine on close
    original_close = window.closeEvent
    def new_close_event(event):
        audio_engine.stop()
        stop_speaking()
        original_close(event)
    window.closeEvent = new_close_event

    if wait_for_server():
        window.add_message("AURA", "Local memory server connected.")
        # Load initial graph state
        refresh_graph(bridge)
    else:
        window.add_message("AURA", "Local memory server is still starting.")

    window.add_message("AURA", "Wake-word listener started.")

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
