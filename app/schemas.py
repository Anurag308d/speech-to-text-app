from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TranscriptBase(BaseModel):
    title: str = Field(default="Untitled", max_length=200)
    text: str = ""
    language: str | None = None
    duration_seconds: float | None = None


class TranscriptCreate(TranscriptBase):
    pass


class TranscriptUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    text: str | None = None
    language: str | None = None


class TranscriptOut(TranscriptBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
