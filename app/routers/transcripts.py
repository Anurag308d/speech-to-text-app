from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Transcript
from ..schemas import TranscriptCreate, TranscriptOut, TranscriptUpdate

router = APIRouter(prefix="/api/transcripts", tags=["transcripts"])


def _get_or_404(db: Session, transcript_id: int) -> Transcript:
    t = db.get(Transcript, transcript_id)
    if not t:
        raise HTTPException(404, "Transcript not found")
    return t


@router.get("", response_model=list[TranscriptOut])
def list_transcripts(q: str | None = Query(None), db: Session = Depends(get_db)):
    stmt = select(Transcript).order_by(Transcript.created_at.desc())
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Transcript.title.ilike(like), Transcript.text.ilike(like)))
    return db.scalars(stmt).all()


@router.post("", response_model=TranscriptOut, status_code=201)
def create_transcript(payload: TranscriptCreate, db: Session = Depends(get_db)):
    t = Transcript(**payload.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.get("/{transcript_id}", response_model=TranscriptOut)
def get_transcript(transcript_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, transcript_id)


@router.put("/{transcript_id}", response_model=TranscriptOut)
def update_transcript(transcript_id: int, payload: TranscriptUpdate, db: Session = Depends(get_db)):
    t = _get_or_404(db, transcript_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(t, field, value)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{transcript_id}", status_code=204)
def delete_transcript(transcript_id: int, db: Session = Depends(get_db)):
    t = _get_or_404(db, transcript_id)
    db.delete(t)
    db.commit()
