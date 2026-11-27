import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_transcript_crud(client):
    r = client.post("/api/transcripts", json={"title": "Intro", "text": "मेरा नाम अनुराग है and I am an engineer"})
    assert r.status_code == 201
    tid = r.json()["id"]

    assert client.get(f"/api/transcripts/{tid}").json()["title"] == "Intro"

    r = client.put(f"/api/transcripts/{tid}", json={"title": "Edited"})
    assert r.json()["title"] == "Edited"
    assert r.json()["text"].startswith("मेरा")

    assert client.delete(f"/api/transcripts/{tid}").status_code == 204
    assert client.get(f"/api/transcripts/{tid}").status_code == 404


def test_search(client):
    client.post("/api/transcripts", json={"title": "Standup", "text": "deploy tomorrow"})
    client.post("/api/transcripts", json={"title": "Hindi", "text": "नमस्ते दोस्तों"})
    titles = [t["title"] for t in client.get("/api/transcripts", params={"q": "नमस्ते"}).json()]
    assert titles == ["Hindi"]
    assert len(client.get("/api/transcripts").json()) == 2


def test_transcribe_without_key_returns_clear_error(client):
    r = client.post("/api/transcribe", files={"audio": ("chunk.webm", b"\x1a\x45\xdf\xa3", "audio/webm")})
    assert r.status_code == 500
    assert "GROQ_API_KEY" in r.json()["detail"]


def test_transcribe_empty_audio_is_ignored(client):
    r = client.post("/api/transcribe", files={"audio": ("chunk.webm", b"", "audio/webm")})
    assert r.json() == {"text": "", "language": None}
