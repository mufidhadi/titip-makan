from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from titip_makan.core.config import settings

Base = declarative_base()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True
)

async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session

from sqlalchemy import text

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            await conn.execute(text("ALTER TABLE pool_sessions ADD COLUMN coordinator_phone VARCHAR(50)"))
        except Exception:
            pass
        try:
            await conn.execute(text("ALTER TABLE order_items ADD COLUMN payment_status VARCHAR(50) DEFAULT 'UNPAID'"))
            await conn.execute(text("UPDATE order_items SET payment_status = 'PAID' WHERE is_paid = 1"))
        except Exception:
            pass

