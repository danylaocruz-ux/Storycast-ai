from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class BookResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    title: str
    author: Optional[str] = None
    format: str
    cover_path: Optional[str] = None
    file_size: int
    total_segments: int
    total_duration: float
    language: str
    status: str
    status_message: Optional[str] = None
    progress: int
    is_favorite: bool
    created_at: datetime
    updated_at: datetime


class BookListResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    title: str
    author: Optional[str] = None
    format: str
    cover_path: Optional[str] = None
    total_duration: float
    status: str
    progress: int
    is_favorite: bool
    created_at: datetime


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    is_favorite: Optional[bool] = None


class BookStatusResponse(BaseModel):
    id: int
    status: str
    progress: int
    status_message: Optional[str] = None
    total_segments: int
    total_duration: float


class PlayerStateResponse(BaseModel):
    model_config = {"from_attributes": True}

    current_segment: int
    current_position: float
    playback_speed: float
    total_listened: float


class PlayerStateUpdate(BaseModel):
    current_segment: int
    current_position: float
    playback_speed: float = 1.0
