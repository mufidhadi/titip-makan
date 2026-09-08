# Laporan Akhir: Pengalihan Notifikasi Sesi ke WhatsApp Pribadi saat Test Lokal

## 1. Nama Tugas
Konfigurasi Pengalihan Notifikasi Broadcast Sesi Titip Makan ke Nomor WhatsApp Pribadi Mas Mufid Saat Pengujian Lingkungan Lokal/Development.

---

## 2. Informasi Repositori & Branch
- **Nama Repositori**: `titip-makan`
- **URL Repositori**: `git@github.com:mufidhadi/titip-makan.git` / `https://github.com/mufidhadi/titip-makan`
- **Branch**: `feature/local-test-personal-wa-notification`
- **Nomor Hash Commit**: `2f6a6f3`

---

## 3. Tech Stack
- **Backend**: Python 3.12, FastAPI, Pydantic v2 (BaseSettings, pydantic-settings), SQLAlchemy 2.0
- **External Integration**: WAHA (WhatsApp HTTP API)
- **Testing & Verification**: Pytest, Pytest-Asyncio, Playwright E2E Browser Testing
- **Package & Dependency Manager**: `uv`

---

## 4. Histori Aksi
1. **Analisis Kebutuhan**:
   - Membaca instruksi dari mas mufid: *"pada saat test lokal, jangan kirim wa ke group, kirim ke nomor wa pribadiku saja saat membuat sesi titip baru"*.
   - Mengidentifikasi nomor WhatsApp pribadi mas mufid melalui referensi repositori catatan pribadi (`6285740130359` -> `6285740130359@c.us`).
   - Menganalisis kebutuhan isolasi lingkungan: saat `ENVIRONMENT != "production"` (misal `development`, `local`, `test`), broadcast otomatis pengumuman sesi baru tidak boleh masuk ke grup MTN CORE (`120363409564046383@g.us`), melainkan harus dialihkan secara deterministik ke WhatsApp pribadi mas mufid (`6285740130359@c.us`).

2. **Penerapan TDD (Test-Driven Development)**:
   - Membuat pengujian unit baru di `tests/unit/test_notification_service.py`:
     - `test_notification_service_routes_to_personal_wa_in_development`: Memverifikasi payload request `chatId` yang dikirim ke WAHA adalah nomor pribadi mas mufid (`6285740130359@c.us`), bukan ID grup (`120363409564046383@g.us`), serta memiliki header penanda `[TEST LOKAL]`.
     - `test_notification_service_routes_to_group_in_production`: Memverifikasi saat `environment="production"`, target `chatId` tetap ke grup MTN CORE dan tidak memunculkan header test lokal.
   - Menjalankan `uv run pytest tests/unit/test_notification_service.py` untuk mengamati fase *RED* (gagal karena parameter belum diimplementasikan).

3. **Implementasi Kode**:
   - **Konfigurasi (`src/titip_makan/core/config.py`)**:
     - Menambahkan atribut konfigurasi `mufid_personal_chat_id: str = "6285740130359@c.us"` pada kelas `Settings`.
     - Memperbarui `.env` dan `.env.example` lokal dengan `MUFID_PERSONAL_CHAT_ID=6285740130359@c.us`.
   - **Service Notifikasi (`src/titip_makan/services/notification_service.py`)**:
     - Menambahkan method `get_target_chat_id(explicit_chat_id=None)` yang mengecek status `environment`. Jika non-production, otomatis memilih `self.mufid_chat_id`.
     - Menambahkan flag `is_test` pada `format_session_announcement()` yang menambahkan tag `🧪 *[TEST LOKAL - NOTIFIKASI KHUSUS MAS MUFID]*` agar pesan yang diterima mas mufid sangat jelas status pengujiannya.
   - **Integration Test (`tests/unit/test_session_cutoff_and_scheduler.py`)**:
     - Menambahkan `test_create_session_routes_wa_to_personal_in_development` untuk memvalidasi alur nyata saat `SessionService.create_session()` dipanggil pada environment lokal.

4. **Verifikasi Pengujian & Container Synchronization**:
   - Menjalankan rebuild container lokal: `docker compose build app && docker compose up -d app`.
   - Menjalankan seluruh test suite menggunakan `uv run pytest`. Seluruh **35 tests** lulus 100%.

---

## 5. List Kesulitan, Tantangan, Bug dan Solusi

| No | Masalah / Tantangan | Penyebab Utama | Solusi yang Diterapkan |
|---|---|---|---|
| 1 | Menentukan nomor WhatsApp pribadi mas mufid tanpa menebak | Aturan user melarang menebak nomor kontak atau membuat klaim tanpa bukti. | Menelusuri repositori catatan pribadi (`~/Documents/mufid/catatan_pribadi/00018_28_02_2026.md`) dan log percakapan terverifikasi yang mencatat nomor kontak mas mufid `6285740130359`. |
| 2 | Menghindari spam ke grup obrolan kantor saat testing lokal | Sesi baru yang dibuat di localhost sebelumnya otomatis mengirim broadcast ke grup MTN CORE jika WAHA API key aktif. | Menambahkan logika routing dinamis di `NotificationService.get_target_chat_id` berdasarkan variabel `ENVIRONMENT`. |
| 3 | Pengujian E2E browser sempat mendeteksi judul sesi lama sesaat setelah rebuild kontainer | Kontainer lokal uvicorn masih dalam inisialisasi awal database pada milidetik pertama setelah kontainer di-recreate. | Memberikan waktu readiness check sebelum suite E2E dijalankan, memastikan pengujian berjalan pada kontainer yang sudah siap dan stabil. |

---

## 6. List Test yang Dilakukan dan Hasilnya
Seluruh pengujian dijalankan dengan `uv run pytest`:

```
tests/e2e/test_browser_flow.py .                                         [  2%]
tests/integration/test_api_flow.py ..                                    [  8%]
tests/integration/test_e2e_scenarios.py .                                [ 11%]
tests/integration/test_web_routes.py .                                   [ 14%]
tests/unit/test_analytics_and_leaderboard.py ..                          [ 20%]
tests/unit/test_notification_service.py ......                           [ 37%]
tests/unit/test_order_edit_and_payment_status.py ....                    [ 48%]
tests/unit/test_order_service.py .........                               [ 74%]
tests/unit/test_session_cutoff_and_scheduler.py .....                    [ 88%]
tests/unit/test_session_service.py ....                                  [100%]

============================== 35 passed in 8.44s ==============================
```

Rincian tes terkait fitur ini:
1. `tests/unit/test_notification_service.py`:
   - `test_notification_service_routes_to_personal_wa_in_development`: Lulus (chatId = `6285740130359@c.us`, terdapat teks `TEST LOKAL`).
   - `test_notification_service_routes_to_group_in_production`: Lulus (chatId = `120363409564046383@g.us`, tanpa teks `TEST LOKAL`).
2. `tests/unit/test_session_cutoff_and_scheduler.py`:
   - `test_create_session_routes_wa_to_personal_in_development`: Lulus (pembuatan sesi di SessionService otomatis mengarah ke WA pribadi mas mufid).

---

## 7. Lesson Learned
1. **Safety Guarding pada Notifikasi Eksternal**:
   - Integrasi pesan pihak ketiga (seperti WhatsApp/SMS/Email) wajib memiliki safety-guard default berdasarkan environment aktif (`development` vs `production`) untuk mencegah kebocoran pesan uji coba atau notifikasi dummy ke ruang publik/grup kantor.
2. **Keterbacaan Pesan Uji Coba**:
   - Menambahkan header penanda eksplisit `[TEST LOKAL]` pada pesan yang dikirim ke nomor pribadi mempermudah verifikasi fungsional tanpa menimbulkan kebingungan bagi penerima.
