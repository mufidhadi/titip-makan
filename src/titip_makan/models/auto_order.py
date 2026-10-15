from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from titip_makan.core.database import Base

class AutoOrderPreference(Base):
    """Per-user weekday auto order: one random pick from `candidates` per daily session."""
    __tablename__ = "weekday_auto_orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_name = Column(String(100), nullable=False, unique=True, index=True)
    enabled = Column(Boolean, nullable=False, default=False)
    candidates = Column(Text, nullable=False, default="[]")  # JSON list of {vendor, item_name, price}
    last_session_id = Column(Integer, nullable=True)  # session already handled, so cancels are not re-added
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
