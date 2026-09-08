from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from titip_makan.core.database import get_db
from titip_makan.core.config import settings
from titip_makan.schemas.session import SessionCreate, SessionOut
from titip_makan.schemas.order import SessionSummary, OrderCreate, OrderOut
from titip_makan.services.session_service import SessionService
from titip_makan.services.order_service import OrderService

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(data: SessionCreate, db: AsyncSession = Depends(get_db)):
    service = SessionService(db)
    return await service.create_session(data)

@router.get("/active", response_model=Optional[SessionOut])
async def get_active_session(db: AsyncSession = Depends(get_db)):
    service = SessionService(db)
    return await service.get_active_session()

@router.get("/latest", response_model=Optional[SessionOut])
async def get_latest_session(db: AsyncSession = Depends(get_db)):
    service = SessionService(db)
    return await service.get_latest_session()

@router.get("/suggestions")
async def get_general_suggestions(db: AsyncSession = Depends(get_db)):
    service = OrderService(db)
    return await service.get_suggestions(None)

@router.get("/{session_id}/suggestions")
async def get_session_suggestions(session_id: int, db: AsyncSession = Depends(get_db)):
    service = OrderService(db)
    return await service.get_suggestions(session_id)

@router.get("/{session_id}", response_model=SessionOut)
async def get_session(session_id: int, db: AsyncSession = Depends(get_db)):
    service = SessionService(db)
    session = await service.get_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.post("/{session_id}/close", response_model=SessionOut)
async def close_session(
    session_id: int,
    x_coordinator_pin: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    if settings.coordinator_pin and x_coordinator_pin != settings.coordinator_pin:
        raise HTTPException(status_code=403, detail="Invalid coordinator PIN")
    service = SessionService(db)
    try:
        return await service.close_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{session_id}/broadcast")
async def broadcast_session_announcement(
    session_id: int,
    x_coordinator_pin: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    if settings.coordinator_pin and x_coordinator_pin != settings.coordinator_pin:
        raise HTTPException(status_code=403, detail="Invalid coordinator PIN")
    service = SessionService(db)
    try:
        return await service.broadcast_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{session_id}/orders", response_model=List[OrderOut])
async def get_orders(session_id: int, db: AsyncSession = Depends(get_db)):
    service = OrderService(db)
    return await service.get_orders_by_session(session_id)

@router.post("/{session_id}/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def add_order(session_id: int, data: OrderCreate, db: AsyncSession = Depends(get_db)):
    service = OrderService(db)
    try:
        return await service.create_order(session_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{session_id}/summary", response_model=SessionSummary)
async def get_summary(session_id: int, db: AsyncSession = Depends(get_db)):
    service = OrderService(db)
    try:
        return await service.get_session_summary(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
