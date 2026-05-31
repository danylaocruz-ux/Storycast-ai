from pydantic import BaseModel
from typing import Optional


class AudioSegmentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    segment_index: int
    chapter: int
    text: str
    emotion: str
    audio_path: Optional[str] = None
    duration: float
    status: str
    character_id: Optional[int] = None


class BookmarkCreate(BaseModel):
    book_id: int
    segment_index: int
    position: float = 0.0
    label: Optional[str] = None


class BookmarkResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    book_id: int
    segment_index: int
    position: float
    label: Optional[str] = None
