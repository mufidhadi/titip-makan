from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from titip_makan.core.database import Base

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("pool_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_name = Column(String(100), nullable=False, index=True)
    vendor = Column(String(100), nullable=False)
    item_name = Column(String(150), nullable=False)
    variant = Column(String(100), nullable=True, default="")
    notes = Column(Text, nullable=True, default="")
    price = Column(Integer, nullable=False, default=0)
    is_paid = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    session = relationship("PoolSession", back_populates="orders")
