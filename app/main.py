from pathlib import Path
import threading

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import models  # noqa: F401  (registers tables)
from .database import Base, engine
from . import tts as tts_engine
from .routers import transcribe, transcripts, tts

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Speech to Text", version="1.0.0")
app.include_router(transcribe.router)
app.include_router(transcripts.router)
app.include_router(tts.router)

@app.on_event("startup")
def warm_up_tts():
    threading.Thread(target=tts_engine.preload, daemon=True).start()


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/api/health")
def health():
    return {"status": "ok", "database": engine.url.get_backend_name()}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")
