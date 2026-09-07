from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from titip_makan.core.config import settings
from titip_makan.core.database import init_db
from titip_makan.api.v1.sessions import router as sessions_router
from titip_makan.api.v1.orders import router as orders_router
from titip_makan.api.web import router as web_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure database tables exist
    await init_db()
    yield
    # Shutdown

app = FastAPI(
    title=settings.app_name,
    description="Platform Titip Makan MTN CORE - Anti Konflik & Auto Rekap",
    version="0.1.0",
    lifespan=lifespan
)

BASE_DIR = Path(__file__).resolve().parent
static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# API routers
app.include_router(sessions_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")

# Web routers
app.include_router(web_router)

@app.get("/api/health", tags=["health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "environment": settings.environment
    }

def main():
    import uvicorn
    uvicorn.run("titip_makan.main:app", host=settings.host, port=settings.port, reload=settings.debug)

if __name__ == "__main__":
    main()
