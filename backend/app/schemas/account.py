from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AccountDeletionStatus(BaseModel):
    scheduled_deletion_at: Optional[datetime] = None
