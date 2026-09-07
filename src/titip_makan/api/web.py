from pathlib import Path
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from titip_makan.core.database import get_db
from titip_makan.services.session_service import SessionService

router = APIRouter(include_in_schema=False)

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/", response_class=HTMLResponse)
async def home_view(request: Request, db: AsyncSession = Depends(get_db)):
    service = SessionService(db)
    active_session = await service.get_active_session()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"session": active_session}
    )

@router.get("/coordinator", response_class=HTMLResponse)
async def coordinator_view(request: Request, db: AsyncSession = Depends(get_db)):
    service = SessionService(db)
    active_session = await service.get_active_session()
    return templates.TemplateResponse(
        request=request,
        name="coordinator.html",
        context={"session": active_session}
    )
