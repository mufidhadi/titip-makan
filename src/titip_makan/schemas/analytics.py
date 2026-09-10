from typing import List, Optional
from pydantic import BaseModel

class BadgeInfo(BaseModel):
    code: str
    title: str
    icon: str
    description: str
    holder: Optional[str] = None
    metric_value: Optional[str] = None

class LeaderboardEntry(BaseModel):
    rank: int
    user_name: str
    total_spend: int
    order_count: int
    custom_notes_count: int
    unique_menus_count: int
    badges: List[str] = []

class LeaderboardOut(BaseModel):
    badges_summary: List[BadgeInfo]
    rankings: List[LeaderboardEntry]

class TopItem(BaseModel):
    name: str
    vendor: Optional[str] = None
    count: int
    total_amount: int

class PeriodStat(BaseModel):
    period: str  # e.g. "2026-09-08" or "2026-W37" or "2026-09"
    label: str   # formatted label
    order_count: int
    total_spend: int
    top_menu: Optional[str] = None
    top_spender: Optional[str] = None

class AnalyticsOverview(BaseModel):
    total_sessions: int
    total_orders: int
    total_spend: int
    unique_users: int
    average_order_price: float
    daily_stats: List[PeriodStat]
    weekly_stats: List[PeriodStat]
    monthly_stats: List[PeriodStat]
    top_menus: List[TopItem]
    top_vendors: List[TopItem]
    top_spenders: List[LeaderboardEntry]
