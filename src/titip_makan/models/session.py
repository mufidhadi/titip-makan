from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from titip_makan.core.database import Base

class PoolSession(Base):
    __tablename__ = "pool_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    coordinator_name = Column(String(100), nullable=False, default="Zi")
    coordinator_phone = Column(String(50), nullable=True)
    vendor_options = Column(Text, nullable=False, default="[]")  # JSON string of vendor list
    payment_info = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="OPEN")  # OPEN, CLOSED
    cutoff_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    orders = relationship("OrderItem", back_populates="session", cascade="all, delete-orphan")
