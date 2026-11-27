import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import models  # noqa: F401  (registers tables)
from .database import Base, engine
from . import tts as tts_engine
from .routers import transcribe, transcripts, tts

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Load the TTS voices in the background so startup and health checks aren't delayed.
    threading.Thread(target=tts_engine.preload, daemon=True).start()
    yield


app = FastAPI(title="Speech to Text", version="1.1.0", lifespan=lifespan)
app.include_router(transcribe.router)
app.include_router(transcripts.router)
app.include_router(tts.router)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.api_route("/api/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok", "database": engine.url.get_backend_name()}


# HEAD is allowed so uptime checks from hosting platforms get 200 instead of 405.
@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")
