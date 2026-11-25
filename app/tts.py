"""Text to speech with Piper, an open-source neural TTS engine that runs on the CPU.

Mixed Hindi and English text is split into runs by script. Devanagari runs are spoken with a
Hindi voice and Latin runs with an English voice, and the audio is joined into one WAV file.
Voice models are downloaded from Hugging Face on first use and cached in ./voices.
"""
import io
import logging
import re
import threading
import wave
from pathlib import Path

from .config import settings

log = logging.getLogger(__name__)

VOICE_DIR = Path(__file__).resolve().parent.parent / "voices"
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
# A run is a stretch of Devanagari words or a stretch of everything else.
RUN = re.compile(r"[ऀ-ॿ][ऀ-ॿ\s\d.,!?;:'\"()\-]*|[^ऀ-ॿ]+")
MAX_CHARS = 3000

_voices: dict[str, object] = {}
_lock = threading.Lock()


class TTSError(Exception):
    pass


def _load(voice_name: str):
    with _lock:
        if voice_name in _voices:
            return _voices[voice_name]
        from piper import PiperVoice
        from piper.download_voices import download_voice

        VOICE_DIR.mkdir(exist_ok=True)
        model = VOICE_DIR / f"{voice_name}.onnx"
        if not model.exists():
            log.info("Downloading Piper voice %s", voice_name)
            download_voice(voice_name, VOICE_DIR)
        voice = PiperVoice.load(model)
        _voices[voice_name] = voice
        return voice


def preload() -> None:
    """Download and load both voices so the first Play click is fast."""
    for name in (settings.tts_voice_en, settings.tts_voice_hi):
        try:
            _load(name)
        except Exception:  # noqa: BLE001
            log.exception("Could not preload voice %s", name)


def split_runs(text: str) -> list[tuple[str, str]]:
    """Return [(lang, chunk)] where lang is 'hi' or 'en'."""
    runs = []
    for m in RUN.finditer(text):
        chunk = m.group(0)
        if not chunk.strip() or not re.search(r"\w", chunk):
            continue
        lang = "hi" if DEVANAGARI.search(chunk) else "en"
        if runs and runs[-1][0] == lang:
            runs[-1] = (lang, runs[-1][1] + chunk)
        else:
            runs.append((lang, chunk))
    return [(lang, c.strip()) for lang, c in runs]


def synthesize(text: str) -> bytes:
    text = text.strip()[:MAX_CHARS]
    if not text:
        raise TTSError("Nothing to speak.")
    try:
        voices = {"en": _load(settings.tts_voice_en), "hi": _load(settings.tts_voice_hi)}
    except Exception as e:  # noqa: BLE001
        raise TTSError(f"TTS voices unavailable: {e}") from e

    frames = bytearray()
    fmt = None
    for lang, chunk in split_runs(text):
        for audio in voices[lang].synthesize(chunk):
            this_fmt = (audio.sample_rate, audio.sample_width, audio.sample_channels)
            if fmt is None:
                fmt = this_fmt
            if this_fmt != fmt:
                continue  # both default voices are 22.05 kHz mono, so this should not happen
            frames += audio.audio_int16_bytes
        if fmt:
            frames += b"\x00" * int(fmt[0] * fmt[1] * 0.15)  # short pause between runs

    if fmt is None:
        raise TTSError("Nothing to speak.")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setframerate(fmt[0])
        w.setsampwidth(fmt[1])
        w.setnchannels(fmt[2])
        w.writeframes(bytes(frames))
    return buf.getvalue()
