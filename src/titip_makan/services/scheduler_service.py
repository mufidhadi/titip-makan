import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable
from titip_makan.core.database import async_session_factory
from titip_makan.services.session_service import SessionService
from titip_makan.services.notification_service import NotificationService
from titip_makan.schemas.session import SessionCreate, SessionOut

logger = logging.getLogger(__name__)

WIB = timezone(timedelta(hours=7))

HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BULAN = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

class SchedulerService:
    def __init__(
        self,
        db_session_factory: Optional[Callable] = None,
        notifier: Optional[NotificationService] = None
    ):
        self.session_factory = db_session_factory or async_session_factory
        self.notifier = notifier
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def check_and_create_daily_session(self, now_wib: Optional[datetime] = None) -> Optional[SessionOut]:
        now = now_wib or datetime.now(WIB)
        if now.tzinfo is None:
            now = now.replace(tzinfo=WIB)
        else:
            now = now.astimezone(WIB)

        # 1. Only run on weekdays (Monday=0 ... Friday=4)
        if now.weekday() > 4:
            return None

        # 2. Only run during morning window (10:00 to 10:29 WIB)
        if not (now.hour == 10 and 0 <= now.minute < 30):
            return None

        # 3. Check if session was already created today
        session_generator = self.session_factory()
        if hasattr(session_generator, "__aenter__"):
            async with session_generator as db:
                return await self._process_creation(db, now)
        else:
            # Bare session provided (e.g. in test fixture)
            return await self._process_creation(session_generator, now)

    async def _process_creation(self, db, now: datetime) -> Optional[SessionOut]:
        service = SessionService(db, notifier=self.notifier)
        latest = await service.get_latest_session()

        title = f"Titip Makan Siang - {HARI[now.weekday()]}, {now.day} {BULAN[now.month]} {now.year}"

        if latest:
            created_wib = (latest.created_at if latest.created_at.tzinfo else latest.created_at.replace(tzinfo=timezone.utc)).astimezone(WIB)
            if latest.title == title or (created_wib.date() == now.date() and created_wib.hour == 10):
                logger.info("Daily session already created for today. Skipping.")
                return None

        # Calculate cutoff time: 10:30 WIB today
        cutoff_dt = now.replace(hour=10, minute=30, second=0, microsecond=0)
        remaining_seconds = max(60, int((cutoff_dt - now).total_seconds()))
        cutoff_minutes = max(1, remaining_seconds // 60)
        
        session_data = SessionCreate(
            title=title,
            coordinator_name="Irzi",
            coordinator_phone="+62 815-1382-5480",
            vendor_options=["Babun", "Mie Ayam", "Buah Potong", "Kantin"],
            payment_info="gopay ke +62 815-1382-5480",
            cutoff_minutes=cutoff_minutes,
            cutoff_at=cutoff_dt
        )

        logger.info(f"Creating automated daily session: {title}")
        new_session = await service.create_session(session_data)
        return new_session

    async def run_loop(self):
        self._running = True
        logger.info("Starting automated weekday session scheduler...")
        while self._running:
            try:
                await self.check_and_create_daily_session()
            except Exception as e:
                logger.error(f"Error in automated session scheduler loop: {e}")
            await asyncio.sleep(30)

    async def start(self):
        if not self._task or self._task.done():
            self._task = asyncio.create_task(self.run_loop())

    async def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
