# Speech to Text

**Live demo:** https://speech-to-text-app-0pos.onrender.com (free hosting, so the first load after a quiet spell can take about a minute)

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

## Deploy (Render + Neon)

1. Create a free PostgreSQL database on [Neon](https://neon.tech) and copy its connection string.
2. On [Render](https://render.com), create a **Web Service** from this repo with runtime **Python 3**:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Add the environment variables `GROQ_API_KEY`, `DATABASE_URL` (the Neon string) and
   `PYTHON_VERSION=3.12.8`.

A `Dockerfile` is also included for Docker hosts.

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
