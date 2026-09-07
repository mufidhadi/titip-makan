from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class OrderPaymentUpdate(BaseModel):
    is_paid: bool

class AggregatedItem(BaseModel):
    vendor: str
    item_name: str
    variant: str
    quantity: int
    subtotal: int
    notes_list: List[str] = Field(default_factory=list)

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
    whatsapp_recap_text: str
