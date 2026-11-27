---
title: Speech to Text
emoji: 🎙️
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 5.9.1
python_version: "3.12"
app_file: space_app.py
pinned: false
---

# Speech to Text

A web app that transcribes speech in real time, including mixed Hindi and English, saves each
transcript to PostgreSQL, and lets you view, edit, delete and replay transcripts from a dashboard.

Built for the Procucev AI Tech Hiring Assignment.

## Tech stack

- **Backend:** Python, FastAPI, SQLAlchemy
- **Database:** PostgreSQL (SQLite fallback for quick local testing)
- **Speech to text:** Whisper large-v3 via the free Groq API
- **Text to speech:** Piper (open source, runs on the server CPU), with a Hindi voice and an English voice
- **Frontend:** Plain HTML, CSS and JavaScript

## Run locally (Windows)

```powershell
cd procucev-speech-app
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # then open .env and paste your GROQ_API_KEY
uvicorn app.main:app
```

Open http://localhost:8000.

If `DATABASE_URL` is empty the app uses a local `speechapp.db` SQLite file, so you can test
without installing PostgreSQL. In production it uses PostgreSQL.

The first time the app starts it downloads the two Piper voices (about 120 MB) into `voices/`.

## How it works

1. The browser records the microphone in short segments. A segment ends at a pause in speech
   (or after 6 seconds), so words are rarely cut in half. Silent segments are skipped.
2. Each segment is sent to `POST /api/transcribe`, which forwards it to Whisper on Groq. Whisper
   detects the language per segment, so mixed Hindi and English works. The tail of the earlier
   text is passed as a prompt to keep spelling consistent.
3. Text appears on screen as each segment returns. On **Stop**, the full transcript is saved.
4. The **History** tab lists transcripts with search, edit, delete and **Play**. Play sends the
   text to `POST /api/tts`, which splits it into Devanagari and Latin runs, speaks each with the
   matching Piper voice and returns one WAV file. If the server can't speak, the browser's
   built-in voice is used instead.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/transcribe` | Transcribe one audio segment |
| GET | `/api/transcripts?q=` | List transcripts, optional search |
| POST | `/api/transcripts` | Create a transcript |
| GET | `/api/transcripts/{id}` | Get one transcript |
| PUT | `/api/transcripts/{id}` | Update title or text |
| DELETE | `/api/transcripts/{id}` | Delete a transcript |
| POST | `/api/tts` | Text to speech (returns WAV) |
| GET | `/api/health` | Health check |

Interactive API docs are at `/docs`.

## Deploy (Hugging Face Spaces + Neon)

1. Create a free PostgreSQL database on [Neon](https://neon.tech) and copy its connection string.
2. Create a new Space on Hugging Face with the **Gradio** SDK (blank template, free CPU).
   `space_app.py` runs the FastAPI app on port 7860; no Gradio UI is used.
3. In the Space's **Settings → Variables and secrets**, add the secrets `GROQ_API_KEY` and
   `DATABASE_URL` (the Neon connection string).
4. Push this repository to the Space. It installs `requirements.txt`, downloads the Piper
   voices on first start and serves the app. A `Dockerfile` is also included for any
   Docker host.

## Project structure

```
app/
  main.py        FastAPI app, static files, routes
  config.py      Settings read from .env
  database.py    SQLAlchemy engine and session
  models.py      Transcript table
  schemas.py     Request and response models
  stt.py         Groq Whisper client
  tts.py         Piper text to speech
  routers/       API routes
static/          Frontend (HTML, CSS, JS)
```
