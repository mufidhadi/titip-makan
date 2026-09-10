from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_serializer

def serialize_utc(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

class OrderCreate(BaseModel):
    user_name: str = Field(..., min_length=1, examples=["Amal"])
    vendor: str = Field(..., min_length=1, examples=["Mie Ayam"])
    item_name: str = Field(..., min_length=1, examples=["Mie Ayam"])
    variant: Optional[str] = Field(default="", examples=["Pangsit Rebus"])
    notes: Optional[str] = Field(default="", examples=["Tanpa daun bawang"])
    price: Optional[int] = Field(default=0, ge=0, examples=[15000])

class OrderOut(BaseModel):
    id: int
    session_id: int
    user_name: str
    vendor: str
    item_name: str
    variant: Optional[str] = ""
    notes: Optional[str] = ""
    price: int
    is_paid: bool
    payment_status: str = "UNPAID"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_dt(self, dt: Optional[datetime]) -> Optional[str]:
        return serialize_utc(dt)

class OrderPaymentUpdate(BaseModel):
    is_paid: Optional[bool] = None
    payment_status: Optional[str] = None

class OrderPriceUpdate(BaseModel):
    price: int = Field(..., ge=0, description="Harga yang diisi/diperbarui oleh koordinator")

class OrderUpdate(BaseModel):
    vendor: Optional[str] = None
    item_name: Optional[str] = None
    notes: Optional[str] = None
    price: Optional[int] = Field(default=None, ge=0)

class AggregatedItem(BaseModel):
    vendor: str
    item_name: str
    variant: str
    quantity: int
    subtotal: int
    notes_list: List[str] = Field(default_factory=list)

class UnpaidUserItem(BaseModel):
    order_id: int
    user_name: str
    item_name: str
    vendor: str
    price: int
    payment_status: str

class SessionSummary(BaseModel):
    session_id: int
    title: str
    status: str
    total_orders: int
    total_amount: int
    total_paid_count: int
    total_unpaid_count: int
    aggregated_items: List[AggregatedItem]
    orders: List[OrderOut]
    unpaid_orders_users: List[UnpaidUserItem] = Field(default_factory=list)
    whatsapp_recap_text: str
