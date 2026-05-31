from pydantic import BaseModel
from typing import Optional


class CharacterResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    description: Optional[str] = None
    gender: str
    age_group: str
    personality: Optional[str] = None
    is_narrator: bool
    voice_id: Optional[str] = None
    voice_name: Optional[str] = None
    color: str
    appearance_order: int


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    gender: Optional[str] = None
    age_group: Optional[str] = None
    voice_id: Optional[str] = None
    voice_name: Optional[str] = None
    