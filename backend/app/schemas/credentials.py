from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CredentialStatus(BaseModel):
    provider: str
    has_key: bool
    key_hint: Optional[str] = None
    label: Optional[str] = None
    last_verified_at: Optional[datetime] = None


class CredentialCreate(BaseModel):
    api_key: str = Field(..., min_length=10, max_length=500)
    label: Optional[str] = Field(None, max_length=100)
