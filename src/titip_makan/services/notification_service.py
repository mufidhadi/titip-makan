import logging
from typing import Optional, Dict, Any
from datetime import timezone, timedelta
import httpx
from titip_makan.core.config import settings
from titip_makan.schemas.session import SessionOut

logger = logging.getLogger(__name__)

def format_session_announcement(
    session: SessionOut,
    public_url: Optional[str] = None,
    is_test: bool = False
) -> str:
    url = public_url or settings.app_public_url or "https://titip-irzi.masmuf.cloud"
    
    coordinator_str = session.coordinator_name
    if session.coordinator_phone:
        coordinator_str += f" ({session.coordinator_phone})"
        
    vendors_str = ", ".join(session.vendor_options) if session.vendor_options else "Bebas / Semua tenant"
    
    cutoff_str = "Tidak ditentukan"
    if session.cutoff_at:
        wib_time = (session.cutoff_at if session.cutoff_at.tzinfo else session.cutoff_at.replace(tzinfo=timezone.utc)).astimezone(timezone(timedelta(hours=7)))
        cutoff_str = wib_time.strftime("%H:%M WIB")
        
    payment_section = f"\n💳 *Info Pembayaran:*\n{session.payment_info}\n" if session.payment_info else ""
    test_header = "🧪 *[TEST LOKAL - NOTIFIKASI KHUSUS MAS MUFID]*\n\n" if is_test else ""

    return (
        f"{test_header}📢 *PENGUMUMAN TITIP MAKAN MTN CORE* 🍜\n\n"
        f"Halo rekan-rekan MTN CORE, ini asisten mas mufid menginfokan bahwa sesi titip makan baru saja dibuka!\n\n"
        f"📋 *Detail Sesi:*\n"
        f"• *Judul:* {session.title}\n"
        f"• *Koordinator:* {coordinator_str}\n"
        f"• *Pilihan Warung/Tenant:* {vendors_str}\n"
        f"• *Batas Waktu Pemesanan:* {cutoff_str}\n\n"
        f"👉 *Klik link berikut untuk titip pesanan:*\n"
        f"{url}\n"
        f"{payment_section}\n"
        f"Yuk segera pilih dan titip pesanan kalian sebelum batas waktu ya! Terima kasih 🙏"
    )

class NotificationService:
    def __init__(
        self,
        base_url: str = settings.waha_base_url,
        api_key: str = settings.waha_api_key,
        default_chat_id: str = settings.default_group_chat_id,
        mufid_chat_id: str = settings.mufid_personal_chat_id,
        environment: str = settings.environment,
        public_url: str = settings.app_public_url,
        enabled: bool = settings.waha_notify_group
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key or ""
        self.default_chat_id = default_chat_id or "120363409564046383@g.us"
        self.mufid_chat_id = mufid_chat_id or "6285740130359@c.us"
        self.environment = environment or "development"
        self.public_url = public_url or "https://titip-irzi.masmuf.cloud"
        self.enabled = enabled

    def get_target_chat_id(self, explicit_chat_id: Optional[str] = None) -> str:
        """
        Determines the target chat ID for session announcements.
        - If an explicit chat_id is provided, it is respected.
        - If environment is NOT production (e.g. 'development', 'local', 'test'):
          routes to mas mufid's personal WhatsApp number (self.mufid_chat_id).
        - If environment is 'production':
          routes to the main MTN CORE group chat (self.default_chat_id).
        """
        if explicit_chat_id:
            return explicit_chat_id
        if self.environment.lower() != "production":
            return self.mufid_chat_id
        return self.default_chat_id

    async def send_text(self, chat_id: str, text: str) -> Dict[str, Any]:
        if not self.enabled:
            logger.info("WhatsApp notifications are disabled by configuration.")
            return {"status": "skipped", "reason": "disabled"}
        if not self.api_key:
            logger.warning("WAHA_API_KEY is not set. Skipping WhatsApp notification.")
            return {"status": "skipped", "reason": "no_api_key"}

        url = f"{self.base_url}/api/sendText"
        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": self.api_key
        }
        payload = {
            "session": "default",
            "chatId": chat_id,
            "text": text
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()

    async def broadcast_session_opened(
        self,
        session: SessionOut,
        chat_id: Optional[str] = None
    ) -> Dict[str, Any]:
        target_chat_id = self.get_target_chat_id(chat_id)
        is_test = (self.environment.lower() != "production") and (target_chat_id == self.mufid_chat_id)
        message = format_session_announcement(session, self.public_url, is_test=is_test)
        try:
            res = await self.send_text(target_chat_id, message)
            if res.get("status") == "skipped":
                return res
            logger.info(f"WA announcement sent to {target_chat_id} (env={self.environment}, is_test={is_test}): {res}")
            return {"status": "success", "target_chat_id": target_chat_id, "data": res}
        except Exception as e:
            logger.error(f"Failed to send WA announcement to {target_chat_id}: {e}")
            return {"status": "error", "target_chat_id": target_chat_id, "error": str(e)}
