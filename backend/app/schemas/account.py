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
