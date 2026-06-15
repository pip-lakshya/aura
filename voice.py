"""Voice input, output, and wake-word helpers for AURA."""

from __future__ import annotations

import asyncio
import math
import os
import tempfile
import threading
import time
from array import array
from typing import Callable

_SPEECH_STOP_EVENT = threading.Event()

import requests

from config import load_env


load_env()

SAMPLE_RATE = int(os.getenv("AURA_SAMPLE_RATE", "16000"))
CHANNELS = 1
WAKE_WORD_VARIANTS = (
    "aura",
    "hey aura",
    "hello aura",
    "aura listen",
    "aura listening",
    "aura wake up",
    "ok aura",
    "okay aura",
    "ora",
    "hey ora",
    "ora listen",
    "laura",
    "hey laura",
    "aurora",
)
GROQ_TRANSCRIPTION_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_WHISPER_MODEL = "whisper-large-v3-turbo"
EDGE_TTS_VOICE = os.getenv("AURA_TTS_VOICE", "en-US-AriaNeural")
AURA_INPUT_DEVICE = os.getenv("AURA_INPUT_DEVICE", "").strip()
MIN_AUDIO_PEAK = float(os.getenv("AURA_MIN_AUDIO_PEAK", "0.002"))
MAX_AUDIO_RMS = float(os.getenv("AURA_MAX_AUDIO_RMS", "0.40"))
MAX_AUDIO_PEAK = float(os.getenv("AURA_MAX_AUDIO_PEAK", "0.995"))
MIC_RECORD_SECONDS = float(os.getenv("AURA_MIC_RECORD_SECONDS", "10"))
AURA_LISTEN_TIMEOUT = float(os.getenv("AURA_LISTEN_TIMEOUT", "8"))
WAKE_CHUNK_SECONDS = float(os.getenv("AURA_WAKE_CHUNK_SECONDS", "1.4"))
WAKE_COOLDOWN_SECONDS = float(os.getenv("AURA_WAKE_COOLDOWN_SECONDS", "1.5"))
WAKE_PHRASE_SECONDS = float(os.getenv("AURA_WAKE_PHRASE_SECONDS", "1.35"))
WAKE_LISTEN_TIMEOUT = float(os.getenv("AURA_WAKE_LISTEN_TIMEOUT", "0.25"))
WAKE_RECOGNITION_TIMEOUT = float(os.getenv("AURA_WAKE_RECOGNITION_TIMEOUT", "1.2"))


def _rms_from_values(values: array) -> float:
    if not values:
        return 0.0
    total = sum(sample * sample for sample in values)
    return math.sqrt(total / len(values)) / 32768.0


def _audio_levels_from_raw(raw_data: bytes) -> dict[str, float]:
    if not raw_data:
        return {"rms": 0.0, "peak": 0.0}

    values = array("h")
    values.frombytes(raw_data)
    if not values:
        return {"rms": 0.0, "peak": 0.0}

    peak = max(abs(sample) for sample in values) / 32768.0
    return {"rms": _rms_from_values(values), "peak": peak}


def _get_sr_device_index() -> int | None:
    import speech_recognition as sr

    value = os.getenv("AURA_INPUT_DEVICE", "").strip()
    if value.isdigit():
        return int(value)

    names = sr.Microphone.list_microphone_names()
    for index, name in enumerate(names):
        lowered = name.lower()
        if "microphone array" in lowered or "microphone" in lowered:
            return index

    return None


def list_audio_devices() -> str:
    """Return input/output devices seen by sounddevice and SpeechRecognition."""
    lines = []

    try:
        import sounddevice as sd

        lines.append("sounddevice devices:")
        lines.append(str(sd.query_devices()))
    except Exception as exc:
        lines.append(f"sounddevice unavailable: {exc}")

    try:
        import speech_recognition as sr

        lines.append("SpeechRecognition microphones:")
        for index, name in enumerate(sr.Microphone.list_microphone_names()):
            marker = "*" if index == _get_sr_device_index() else " "
            lines.append(f"{marker} {index}: {name}")
    except Exception as exc:
        lines.append(f"SpeechRecognition unavailable: {exc}")

    return "\n".join(lines)


def measure_microphone_level(seconds: float = 3.0) -> dict[str, float | int | None]:
    """Record a fixed window through SpeechRecognition/PyAudio and measure it."""
    import speech_recognition as sr

    device_index = _get_sr_device_index()
    recognizer = sr.Recognizer()

    with sr.Microphone(device_index=device_index, sample_rate=SAMPLE_RATE) as source:
        audio = recognizer.record(source, duration=seconds)

    raw_data = audio.get_raw_data(convert_rate=SAMPLE_RATE, convert_width=2)
    levels = _audio_levels_from_raw(raw_data)
    return {
        "rms": levels["rms"],
        "peak": levels["peak"],
        "minimum_peak": MIN_AUDIO_PEAK,
        "maximum_rms": MAX_AUDIO_RMS,
        "maximum_peak": MAX_AUDIO_PEAK,
        "device_index": device_index,
        "sample_rate": SAMPLE_RATE,
    }


def _beep() -> None:
    try:
        import numpy as np
        import sounddevice as sd

        duration = 0.16
        frequency = 880
        samples = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
        tone = 0.25 * np.sin(2 * np.pi * frequency * samples)
        sd.play(tone, SAMPLE_RATE)
        sd.wait()
    except Exception:
        pass


def _transcribe_wav_bytes(wav_data: bytes) -> str:
    groq_api_key = os.getenv("GROQ_API_KEY", "")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY is not set.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        temp_file.write(wav_data)
        temp_path = temp_file.name

    try:
        with open(temp_path, "rb") as audio_file:
            response = requests.post(
                GROQ_TRANSCRIPTION_URL,
                headers={"Authorization": f"Bearer {groq_api_key}"},
                files={"file": ("speech.wav", audio_file, "audio/wav")},
                data={"model": GROQ_WHISPER_MODEL},
                timeout=45,
            )
        response.raise_for_status()
        return str(response.json().get("text", "")).strip()
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def listen_and_transcribe(on_recorded: Callable[[], None] | None = None) -> str:
    """Listen for a phrase, reject bad captures, then transcribe with Groq."""
    import speech_recognition as sr

    device_index = _get_sr_device_index()
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.9
    recognizer.non_speaking_duration = 0.4

    with sr.Microphone(device_index=device_index, sample_rate=SAMPLE_RATE) as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.8)
        audio = recognizer.listen(
            source,
            timeout=AURA_LISTEN_TIMEOUT,
            phrase_time_limit=MIC_RECORD_SECONDS,
        )

    raw_data = audio.get_raw_data(convert_rate=SAMPLE_RATE, convert_width=2)
    levels = _audio_levels_from_raw(raw_data)
    if levels["peak"] < MIN_AUDIO_PEAK:
        raise RuntimeError(
            f"Mic audio too quiet. Peak={levels['peak']:.6f}, "
            f"minimum={MIN_AUDIO_PEAK:.6f}, device={device_index}."
        )
    if levels["rms"] > MAX_AUDIO_RMS and levels["peak"] >= MAX_AUDIO_PEAK:
        raise RuntimeError(
            f"Mic audio is clipping/noisy. RMS={levels['rms']:.3f}, "
            f"peak={levels['peak']:.3f}, device={device_index}. "
            "Lower Windows input volume or try AURA_INPUT_DEVICE=1 or 9."
        )

    if on_recorded:
        on_recorded()

    text = _transcribe_wav_bytes(audio.get_wav_data(convert_rate=SAMPLE_RATE))
    if text.lower().strip() in {"", "you", "thank you", "thanks"}:
        return ""
    return text


def stop_speaking() -> None:
    """Stop current TTS playback as quickly as possible."""
    _SPEECH_STOP_EVENT.set()
    try:
        import pygame

        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
    except Exception:
        pass


def speak(
    text: str,
    on_start: Callable[[], None] | None = None,
    on_end: Callable[[], None] | None = None,
) -> None:
    """Speak text with edge-tts and embedded pygame playback."""
    _SPEECH_STOP_EVENT.clear()
    if on_start:
        on_start()

    try:
        asyncio.run(_speak_async(text))
        if not _SPEECH_STOP_EVENT.is_set():
            _play_audio("tts_out.mp3")
    finally:
        if on_end:
            on_end()


async def _speak_async(text: str) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice=EDGE_TTS_VOICE)
    await communicate.save("tts_out.mp3")


def _play_audio(path: str) -> None:
    import pygame

    pygame.mixer.init()
    pygame.mixer.music.load(path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy() and not _SPEECH_STOP_EVENT.is_set():
        time.sleep(0.03)
    if _SPEECH_STOP_EVENT.is_set():
        pygame.mixer.music.stop()
    pygame.mixer.music.unload()


def _has_wake_word(transcript: str) -> bool:
    normalized = transcript.lower()
    return any(variant in normalized for variant in WAKE_WORD_VARIANTS)


def start_wake_word_loop(
    on_activated: Callable[[], None],
    on_error: Callable[[str], None] | None = None,
) -> threading.Thread:
    """Start a fast non-blocking wake-word listener."""
    import speech_recognition as sr

    def loop() -> None:
        device_index = _get_sr_device_index()
        recognizer = sr.Recognizer()
        recognizer.dynamic_energy_threshold = True
        recognizer.operation_timeout = WAKE_RECOGNITION_TIMEOUT
        recognizer.pause_threshold = 0.25
        recognizer.non_speaking_duration = 0.2
        last_activation = 0.0
        last_error = 0.0

        try:
            mic = sr.Microphone(device_index=device_index, sample_rate=SAMPLE_RATE)
        except Exception as exc:
            if on_error:
                on_error(str(exc))
            return

        with mic as source:
            try:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
            except Exception:
                pass

            while True:
                try:
                    audio = recognizer.listen(
                        source,
                        timeout=WAKE_LISTEN_TIMEOUT,
                        phrase_time_limit=WAKE_PHRASE_SECONDS,
                    )
                    raw_data = audio.get_raw_data(convert_rate=SAMPLE_RATE, convert_width=2)
                    levels = _audio_levels_from_raw(raw_data)
                    if levels["peak"] < MIN_AUDIO_PEAK:
                        continue
                    if levels["rms"] > MAX_AUDIO_RMS and levels["peak"] >= MAX_AUDIO_PEAK:
                        continue

                    try:
                        text = recognizer.recognize_google(audio).lower()
                    except Exception:
                        continue

                    now = time.time()
                    if _has_wake_word(text) and now - last_activation >= WAKE_COOLDOWN_SECONDS:
                        last_activation = now
                        _beep()
                        on_activated()
                except sr.WaitTimeoutError:
                    continue
                except Exception as exc:
                    now = time.time()
                    if on_error and now - last_error > 10:
                        on_error(str(exc))
                        last_error = now
                    time.sleep(0.1)

    thread = threading.Thread(target=loop, name="aura-wake-word", daemon=True)
    thread.start()
    return thread
