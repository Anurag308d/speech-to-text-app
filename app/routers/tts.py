from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from ..tts import TTSError, synthesize

router = APIRouter(prefix="/api", tags=["speech"])


class TTSRequest(BaseModel):
    text: str


@router.post("/tts")
def tts(req: TTSRequest):
    # A plain def runs in FastAPI's thread pool, so synthesis doesn't block other requests.
    try:
        wav = synthesize(req.text)
    except TTSError as e:
        raise HTTPException(503, str(e))
    return Response(content=wav, media_type="audio/wav")
