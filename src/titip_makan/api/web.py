from pathlib import Path
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from titip_makan.core.database import get_db
from titip_makan.services.session_service import SessionService
from titip_makan.services.order_service import OrderService

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

@router.get("/history", response_class=HTMLResponse)
async def history_view(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={}
    )

@router.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_view(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="leaderboard.html",
        context={}
    )

@router.get("/menu", response_class=HTMLResponse)
async def menu_catalog_view(request: Request, db: AsyncSession = Depends(get_db)):
    session_service = SessionService(db)
    order_service = OrderService(db)
    active_session = await session_service.get_active_session()
    suggestions = await order_service.get_suggestions(active_session.id if active_session else None)
    
    prices = suggestions.get("prices", {})
    menus = suggestions.get("menus", {})
    
    tenants_data = []
    for tenant in suggestions.get("tenants", []):
        tenant_items = []
        raw_items = menus.get(tenant, [])
        for item in raw_items:
            price = prices.get(item, 0)
            tenant_items.append({
                "name": item,
                "price": price,
                "formatted_price": f"Rp {price:,.0f}".replace(",", ".") if price > 0 else "Belum ada harga"
            })
        # Sort items by name
        tenant_items.sort(key=lambda x: x["name"])
        tenants_data.append({
            "name": tenant,
            "menu_items": tenant_items,
            "total_items": len(tenant_items)
        })

    total_items_count = sum(t["total_items"] for t in tenants_data)

    return templates.TemplateResponse(
        request=request,
        name="menu.html",
        context={
            "session": active_session,
            "tenants": suggestions.get("tenants", []),
            "tenants_data": tenants_data,
            "total_items_count": total_items_count,
            "raw_suggestions": suggestions,
        }
    )

