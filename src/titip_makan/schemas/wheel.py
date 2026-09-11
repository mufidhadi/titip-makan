from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class WheelCandidate(BaseModel):
    label: str
    vendor: str
    price: Optional[int] = None


class WheelCandidates(BaseModel):
    mode: Literal["tenant", "item"]
    candidates: List[WheelCandidate] = Field(default_factory=list)
    vendors: List[str] = Field(default_factory=list)
    excluded_last_tenants: List[str] = Field(default_factory=list)
    avoid_last_applied: bool = False
