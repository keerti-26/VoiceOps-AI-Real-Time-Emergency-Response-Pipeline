from pydantic import BaseModel
from typing import List, Optional


class IncidentExtraction(BaseModel):
    emergency_type: Optional[str]
    severity: Optional[str]
    location: Optional[str]
    injuries: Optional[bool]
    symptoms: List[str] = []
    callback_number: Optional[str]
    summary: Optional[str]
    missing_fields: List[str] = []