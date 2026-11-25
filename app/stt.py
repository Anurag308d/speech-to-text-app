"""Speech to text through Groq's hosted Whisper model (free tier)."""
import re

import httpx

from .config import settings

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

# Common Whisper outputs on silence or noise; dropped so they don't pollute the transcript.
HALLUCINATIONS = {
    "thank you.", "thank you", "thanks for watching!", "thanks for watching.",
    "you", ".", "bye.", "धन्यवाद", "धन्यवाद।",
}


# The app expects Hindi, English or a mix. Whisper often mislabels short Hindi phrases as Urdu,
# Japanese and so on and writes them in that script. When the detected language is anything
# other than Hindi or English, or the text has characters outside Latin and Devanagari, the
# chunk is transcribed again with the language fixed to Hindi.
EXPECTED_LANGUAGES = {"english", "hindi"}
FOREIGN_SCRIPT = re.compile(r"[^\u0000-\u024F\u0900-\u097F\u2000-\u206F\s]")


MIXED_PROMPT = "हाँ, ठीक है. Okay, यह transcript Hindi और English दोनों में है."


class STTError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


async def transcribe_chunk(audio: bytes, filename: str, content_type: str, prompt: str = "") -> dict:
    if not settings.groq_api_key:
        raise STTError("GROQ_API_KEY is not set on the server.", 500)

    # The earlier transcript is not used as the prompt: an all-English context makes Whisper
    # translate Hindi speech into English. A fixed code-mixed prompt instead tells Whisper to
    # write Hindi in Devanagari and English in Latin script, exactly as spoken.
    prompt = MIXED_PROMPT
    result = await _call_groq(audio, filename, content_type, prompt)
    detected = (result["language"] or "").lower()
    if (detected and detected not in EXPECTED_LANGUAGES) or FOREIGN_SCRIPT.search(result["text"]):
        result = await _call_groq(audio, filename, content_type, prompt, language="hi")
        result["language"] = "hindi"
    result["language"] = (result["language"] or "").lower() or None
    # On near-silent audio Whisper sometimes just repeats the prompt back. Drop that.
    if _norm(result["text"]) and _norm(result["text"]) in _norm(MIXED_PROMPT):
        result["text"] = ""
    return result


def _norm(text: str) -> str:
    return re.sub(r"[\W_]+", " ", text).strip().lower()


async def _call_groq(audio: bytes, filename: str, content_type: str, prompt: str,
                     language: str | None = None) -> dict:

    data = {
        "model": settings.groq_stt_model,
        "response_format": "verbose_json",
        "temperature": "0",
    }
    if language:
        data["language"] = language
    if prompt:
        # The tail of the earlier text keeps spelling and script consistent between chunks.
        data["prompt"] = prompt[-200:]

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            data=data,
            files={"file": (filename, audio, content_type)},
        )

    if resp.status_code == 401:
        raise STTError("Groq rejected the API key. Check GROQ_API_KEY.", 500)
    if resp.status_code == 429:
        raise STTError("Groq rate limit reached. Wait a moment and try again.", 429)
    if resp.status_code >= 400:
        raise STTError(f"Groq error {resp.status_code}: {resp.text[:200]}", 502)

    body = resp.json()
    text = (body.get("text") or "").strip()
    if text.lower() in HALLUCINATIONS:
        text = ""
    return {"text": text, "language": body.get("language")}
