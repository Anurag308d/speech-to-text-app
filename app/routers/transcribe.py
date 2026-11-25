from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..stt import STTError, transcribe_chunk

router = APIRouter(prefix="/api", tags=["speech"])

MAX_CHUNK_BYTES = 5 * 1024 * 1024


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...), prompt: str = Form("")):
    data = await audio.read()
    if not data:
        return {"text": "", "language": None}
    if len(data) > MAX_CHUNK_BYTES:
        raise HTTPException(413, "Audio chunk too large.")
    try:
        return await transcribe_chunk(
            data, audio.filename or "chunk.webm", audio.content_type or "audio/webm", prompt
        )
    except STTError as e:
        raise HTTPException(e.status_code, str(e))
