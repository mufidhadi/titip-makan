from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from titip_makan.core.database import get_db
from titip_makan.schemas.analytics import AnalyticsOverview, LeaderboardOut
from titip_makan.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/overview", response_model=AnalyticsOverview)
async def get_overview(db: AsyncSession = Depends(get_db)):
    service = AnalyticsService(db)
    return await service.get_overview()

@router.get("/leaderboard", response_model=LeaderboardOut)
async def get_leaderboard(db: AsyncSession = Depends(get_db)):
    service = AnalyticsService(db)
    return await service.get_leaderboard()
