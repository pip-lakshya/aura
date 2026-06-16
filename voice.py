"""Voice input, output, and wake-word helpers for AURA using a single persistent audio stream."""

from __future__ import annotations

import asyncio
import math
import os
import tempfile
import threading
import time
from typing import Callable, Any

import requests
import pyaudio
import numpy as np
import speech_recognition as sr
import pygame

from config import load_env

load_env()

SAMPLE_RATE = int(os.getenv("AURA_SAMPLE_RATE", "48000"))
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
WAKE_COOLDOWN_SECONDS = float(os.getenv("AURA_WAKE_COOLDOWN_SECONDS", "1.5"))

_SPEECH_STOP_EVENT = threading.Event()


def _get_sr_device_index() -> int | None:
    value = os.getenv("AURA_INPUT_DEVICE", "").strip()
    if value.isdigit():
        return int(value)

    try:
        p = pyaudio.PyAudio()
        names = [p.get_device_info_by_index(i).get("name", "").lower() for i in range(p.get_device_count())]
        p.terminate()
        for index, name in enumerate(names):
            if "microphone array" in name or "microphone" in name:
                return index
    except Exception:
        pass

    return None


def list_audio_devices() -> str:
    """Return input/output devices seen by sounddevice and PyAudio."""
    lines = []
    try:
        import sounddevice as sd
        lines.append("sounddevice devices:")
        lines.append(str(sd.query_devices()))
    except Exception as exc:
        lines.append(f"sounddevice unavailable: {exc}")

    try:
        p = pyaudio.PyAudio()
        lines.append("PyAudio input devices:")
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info.get("maxInputChannels", 0) > 0:
                marker = "*" if i == _get_sr_device_index() else " "
                lines.append(f"{marker} {i}: {info.get('name')}")
        p.terminate()
    except Exception as exc:
        lines.append(f"PyAudio unavailable: {exc}")

    return "\n".join(lines)


def _beep() -> None:
    try:
        duration = 0.16
        frequency = 880
        samples = np.linspace(0, duration, int(16000 * duration), False)
        tone = 0.25 * np.sin(2 * np.pi * frequency * samples)
        # Play tone via sounddevice
        import sounddevice as sd
        sd.play(tone, 16000)
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


def transcribe_audio(audio: sr.AudioData) -> str:
    """Transcribe standard AudioData using Groq Whisper (downsampled to 16000Hz)."""
    text = _transcribe_wav_bytes(audio.get_wav_data(convert_rate=16000))
    if text.lower().strip() in {"", "you", "thank you", "thanks"}:
        return ""
    return text


def stop_speaking() -> None:
    """Stop current TTS playback as quickly as possible."""
    _SPEECH_STOP_EVENT.set()
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
    except Exception:
        pass


def speak(
    text: str,
    on_start: Callable[[], None] | None = None,
    on_end: Callable[[], None] | None = None,
    on_level: Callable[[float, float], None] | None = None,
) -> None:
    """Speak text with edge-tts and embedded pygame playback."""
    _SPEECH_STOP_EVENT.clear()
    if on_start:
        on_start()

    try:
        asyncio.run(_speak_async(text))
        if not _SPEECH_STOP_EVENT.is_set():
            _play_audio("tts_out.mp3", on_level)
    finally:
        if on_end:
            on_end()


async def _speak_async(text: str) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice=EDGE_TTS_VOICE)
    await communicate.save("tts_out.mp3")


def _play_audio(path: str, on_level: Callable[[float, float], None] | None = None) -> None:
    pygame.mixer.init()

    samples = None
    try:
        sound = pygame.mixer.Sound(path)
        samples = pygame.sndarray.array(sound)
        if len(samples.shape) > 1:
            samples = samples.mean(axis=1)
    except Exception:
        pass

    pygame.mixer.music.load(path)
    pygame.mixer.music.play()

    start_time = time.time()
    mixer_init = pygame.mixer.get_init()
    actual_rate = mixer_init[0] if mixer_init else 44100

    while pygame.mixer.music.get_busy() and not _SPEECH_STOP_EVENT.is_set():
        if samples is not None and on_level:
            elapsed = time.time() - start_time
            idx = int(elapsed * actual_rate)
            if idx < len(samples):
                window = samples[idx : idx + 1024]
                if len(window) > 0:
                    peak = float(np.max(np.abs(window))) / 32768.0
                    rms = float(np.sqrt(np.mean(window.astype(float) ** 2))) / 32768.0
                    on_level(rms, peak)
            else:
                on_level(0.0, 0.0)
        time.sleep(0.03)

    if _SPEECH_STOP_EVENT.is_set():
        pygame.mixer.music.stop()
    pygame.mixer.music.unload()
    if on_level:
        on_level(0.0, 0.0)


def _has_wake_word(transcript: str) -> bool:
    normalized = transcript.lower()
    return any(variant in normalized for variant in WAKE_WORD_VARIANTS)


class AuraAudioEngine:
    """Single persistent float32 WASAPI microphone capture and routing engine."""

    def __init__(self, device_index: int | None, sample_rate: int = 48000) -> None:
        self.device_index = device_index
        self.sample_rate = sample_rate
        self.running = False
        self.thread: threading.Thread | None = None

        # Callbacks
        self.on_level_callback: Callable[[float, float], None] | None = None
        self.on_wake_word_callback: Callable[[], None] | None = None
        self.on_recording_complete_callback: Callable[[sr.AudioData], None] | None = None

        # States: 'idle', 'wake_word', 'recording'
        self.state = "idle"
        self.state_lock = threading.Lock()

        # VAD Parameters
        self.threshold = 0.002
        self.recorded_chunks: list[np.ndarray] = []
        self.silence_timer = 0.0
        self.max_record_seconds = 10.0
        self.pause_threshold = 0.9

    def start(
        self,
        on_level: Callable[[float, float], None],
        on_wake: Callable[[], None],
        on_record_done: Callable[[sr.AudioData], None],
    ) -> None:
        self.on_level_callback = on_level
        self.on_wake_word_callback = on_wake
        self.on_recording_complete_callback = on_record_done
        self.running = True
        self.thread = threading.Thread(target=self._run, name="aura-audio-engine", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None

    def set_state(self, new_state: str) -> None:
        with self.state_lock:
            if new_state == "recording":
                self.recorded_chunks = []
                self.silence_timer = 0.0
            self.state = new_state

    def _run(self) -> None:
        p = pyaudio.PyAudio()
        while self.running:
            stream = None
            try:
                try:
                    dev_info = p.get_device_info_by_index(self.device_index) if self.device_index is not None else p.get_default_input_device_info()
                    channels = int(dev_info.get("maxInputChannels", 2))
                except Exception:
                    channels = 2

                stream = p.open(
                    format=pyaudio.paFloat32,
                    channels=channels,
                    rate=self.sample_rate,
                    input=True,
                    input_device_index=self.device_index,
                    frames_per_buffer=1024,
                )

                # Estimate ambient noise
                ambient_frames = []
                for _ in range(int(self.sample_rate / 1024 * 0.4)):
                    data = stream.read(1024, exception_on_overflow=False)
                    samples = np.frombuffer(data, dtype=np.float32)
                    if channels > 1:
                        samples = samples.reshape(-1, channels).mean(axis=1)
                    ambient_frames.append(samples)

                if ambient_frames:
                    all_amb = np.concatenate(ambient_frames)
                    ambient_rms = float(np.sqrt(np.mean(all_amb ** 2)))
                else:
                    ambient_rms = 0.001
                self.threshold = max(0.0025, ambient_rms * 2.2)

                # Sliding history for wake word (pre-roll)
                history = []
                history_len = int(self.sample_rate / 1024 * 1.35)
                chunk_dur = 1024 / self.sample_rate

                recognizer = sr.Recognizer()
                last_activation = 0.0

                while self.running:
                    try:
                        data = stream.read(1024, exception_on_overflow=False)
                        if not data:
                            continue
                        samples = np.frombuffer(data, dtype=np.float32)
                        if channels > 1:
                            samples = samples.reshape(-1, channels).mean(axis=1)

                        rms = float(np.sqrt(np.mean(samples ** 2))) if len(samples) > 0 else 0.0
                        peak = float(np.max(np.abs(samples))) if len(samples) > 0 else 0.0

                        # Emit live level to UI
                        if self.on_level_callback:
                            self.on_level_callback(rms, peak)

                        with self.state_lock:
                            current_state = self.state

                        if current_state == "wake_word":
                            history.append(samples)
                            if len(history) > history_len:
                                history.pop(0)

                            if rms > self.threshold:
                                # Capture audio block for wake word check
                                phrase_frames = list(history)
                                for _ in range(int(self.sample_rate / 1024 * 1.1)):
                                    d = stream.read(1024, exception_on_overflow=False)
                                    s = np.frombuffer(d, dtype=np.float32)
                                    if channels > 1:
                                        s = s.reshape(-1, channels).mean(axis=1)
                                    phrase_frames.append(s)

                                all_s = np.concatenate(phrase_frames)
                                all_s = np.clip(all_s, -1.0, 1.0)
                                pcm = (all_s * 32767.0).astype(np.int16).tobytes()
                                audio = sr.AudioData(pcm, self.sample_rate, 2)

                                try:
                                    text = recognizer.recognize_google(audio).lower()
                                    now = time.time()
                                    if _has_wake_word(text) and now - last_activation >= WAKE_COOLDOWN_SECONDS:
                                        last_activation = now
                                        _beep()
                                        if self.on_wake_word_callback:
                                            self.on_wake_word_callback()
                                except Exception:
                                    pass
                                history.clear()
                                time.sleep(0.3)

                        elif current_state == "recording":
                            self.recorded_chunks.append(samples)
                            if rms > self.threshold:
                                self.silence_timer = 0.0
                            else:
                                self.silence_timer += chunk_dur

                            total_dur = len(self.recorded_chunks) * chunk_dur
                            if self.silence_timer > self.pause_threshold or total_dur > self.max_record_seconds:
                                # Convert to AudioData
                                all_samples = np.concatenate(self.recorded_chunks)
                                all_samples = np.clip(all_samples, -1.0, 1.0)
                                pcm_data = (all_samples * 32767.0).astype(np.int16).tobytes()
                                audio = sr.AudioData(pcm_data, self.sample_rate, 2)

                                # Revert back to wake word monitoring
                                self.state = "wake_word"

                                if self.on_recording_complete_callback:
                                    threading.Thread(
                                        target=self.on_recording_complete_callback,
                                        args=(audio,),
                                        daemon=True,
                                    ).start()

                        time.sleep(0.01)
                    except Exception:
                        pass
            except Exception:
                time.sleep(2.0)
            finally:
                if stream:
                    try:
                        stream.stop_stream()
                        stream.close()
                    except Exception:
                        pass
        p.terminate()
