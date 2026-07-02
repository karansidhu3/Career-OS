from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AccountExportRead(BaseModel):
    id: int
    status: str
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class AccountDeletionStatus(BaseModel):
    scheduled_deletion_at: Optional[datetime] = None


class SessionRead(BaseModel):
    id: str
    status: str
    last_active_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    browser: Optional[str] = None
    device_type: Optional[str] = None
    ip_address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    is_current: bool = False
