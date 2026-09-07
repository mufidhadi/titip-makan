from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_serializer

def serialize_utc(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

class SessionCreate(BaseModel):
    title: str = Field(..., examples=["Titip Makan 7/09/2026"])
    coordinator_name: str = Field(default="Irzi", examples=["Irzi"])
    coordinator_phone: Optional[str] = Field(default="+62 815-1382-5480", examples=["+62 815-1382-5480"])
    vendor_options: List[str] = Field(default_factory=lambda: ["Mie Ayam", "Babun"])
    payment_info: Optional[str] = Field(default="gopay ke +62 815-1382-5480", examples=["gopay ke +62 815-1382-5480"])
    cutoff_minutes: Optional[int] = Field(default=30, description="Cutoff duration in minutes from now")

class SessionOut(BaseModel):
    id: int
    title: str
    coordinator_name: str
    coordinator_phone: Optional[str] = None
    vendor_options: List[str]
    payment_info: Optional[str] = None
    status: str
    cutoff_at: Optional[datetime] = None
    created_at: datetime
    closed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("cutoff_at", "created_at", "closed_at")
    def serialize_dt(self, dt: Optional[datetime]) -> Optional[str]:
        return serialize_utc(dt)
