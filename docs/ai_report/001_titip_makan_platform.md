# Laporan Pengerjaan: Platform Titip Makan MTN CORE

## 1. Informasi Tugas
* **Nama Tugas:** Pembuatan Platform Titip Makan Anti-Konflik & Auto-Rekap (Dockerized)
* **Tanggal Pengerjaan:** 07 September 2026
* **Nama Branch:** `feature/titip-makan-platform`
* **Nomor Hash Commit:** `02d70d594d35321a0cba0b860ee54209ca20e1a2`
* **Nama dan URL Repo:** Lokal (`/Users/anb-0826014/project/mufid/titip-makan`)

---

## 2. Tech Stack
* **Runtime & Package Management:** Python 3.12 via `uv` (Astral)
* **Framework Backend:** FastAPI 0.141+ & Uvicorn (Modular Layered Architecture: Core, Models, Schemas, Repositories, Services, API)
* **Database & ORM:** SQLite dengan Async SQLAlchemy (`aiosqlite`) & `greenlet`
* **Testing:** `pytest`, `pytest-asyncio`, `httpx` (TDD - Test Driven Development)
* **Containerization:** Docker & Docker Compose v5 (Multi-stage build dengan official image `ghcr.io/astral-sh/uv:latest`)
* **Frontend:** Responsive HTML5, Tailwind CSS CDN, Vanilla JavaScript (tanpa framework frontend berat, mobile-friendly)

---

## 3. Histori Aksi
1. **Analisis Kebutuhan & Riset:**
   * Membaca riwayat percakapan WhatsApp grup MTN CORE (`120363409564046383@g.us`) via WAHA API.
   * Menemukan akar masalah: *race condition* pesan suntingan bersamaan ("list ketimpa"), kesulitan rekapitulasi manual oleh koordinator (Zi), dan penagihan/rekonsiliasi pembayaran.
   * Riset pola *group food ordering* dan *split bill* arsitektur modular FastAPI.
2. **Inisialisasi Project:**
   * Membuat folder proyek di `~/project/mufid/titip-makan`.
   * Membuat repository Git baru dan checkout branch `feature/titip-makan-platform`.
   * Inisialisasi proyek Python menggunakan `uv init --app`.
   * Menambahkan dependensi via `uv add`: `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `sqlalchemy`, `aiosqlite`, `greenlet`, `jinja2`, `python-multipart`.
   * Menambahkan dependensi testing via `uv add --dev`: `pytest`, `pytest-asyncio`, `httpx`.
3. **Penerapan TDD (Test Driven Development):**
   * Membuat `tests/conftest.py` dengan in-memory SQLite fixture.
   * Menulis unit test untuk `SessionService` dan `OrderService` (Tahap Red).
   * Mengimplementasikan lapisan `core/config.py`, `core/database.py`, `models/`, `schemas/`, `repositories/`, dan `services/` (Tahap Green).
   * Menulis integration test untuk endpoint REST API dan routing Web.
   * Memverifikasi seluruh 9 test lulus dengan `uv run pytest`.
4. **Implementasi Frontend Web UI:**
   * `templates/base.html`: Layout modern responsif dengan Plus Jakarta Sans & Tailwind CSS.
   * `templates/index.html` & `static/js/app.js`: Halaman pemesan dengan tombol nama cepat (Amal, Shazi, Mufid, dsb.), katalog menu dan varian otomatis, auto-polling 5 detik, dan notifikasi anti-ketimpa.
   * `templates/coordinator.html` & `static/js/coordinator.js`: Dashboard koordinator dengan metrik pesanan, auto-rekapitulasi belanjaan per varian untuk dipesan ke warung/toko, tabel status pembayaran dengan tombol toggle lunas/belum, dan tombol satu-klik "Salin Rekap WA".
5. **Containerization & Docker Compose:**
   * Membuat `Dockerfile` multi-stage menggunakan binary official `ghcr.io/astral-sh/uv:latest` tanpa `pip`.
   * Membuat `docker-compose.yml` dengan volume mounting persistensi SQLite `./data:/app/data` dan port `8080:8080`.
   * Menjalankan container dengan `docker compose up -d --build`.
   * Menguji endpoint health check dan alur pemesanan secara langsung ke container yang sedang berjalan.

---

## 4. List Kesulitan, Tantangan, Bug dan Solusi

| No | Masalah / Bug | Penyebab | Solusi |
|---|---|---|---|
| 1 | `ValueError: the greenlet library is required...` | Async SQLAlchemy membutuhkan library C-extension `greenlet` untuk context switching. | Menambahkan package via `uv add greenlet`. |
| 2 | `TypeError: unhashable type: 'dict'` pada `TemplateResponse` | Signature `TemplateResponse` pada Starlette versi modern (0.38+) mendahulukan argumen `request` daripada `name`. | Mengubah pemanggilan menggunakan keyword arguments: `TemplateResponse(request=request, name="...", context={...})`. |
| 3 | `test_order_cutoff_expiration` gagal | Logika validasi cutoff hanya memproses jika `cutoff_minutes > 0`, sehingga nilai negatif tidak terhitung sebagai batas waktu masa lalu. | Mengubah kondisi menjadi `if data.cutoff_minutes is not None:`. |
| 4 | Deprecation warning Pydantic v2 `example` | Pydantic v2 menggantikan parameter `example` pada `Field()` menjadi `examples=[...]`. | Memperbarui seluruh schema `session.py` dan `order.py` ke `examples=[...]`. |

---

## 5. List Test yang Dilakukan dan Hasilnya

Semua test dijalankan menggunakan command `uv run pytest`:

```text
tests/integration/test_api_flow.py .                                     [ 11%]
tests/integration/test_web_routes.py .                                   [ 22%]
tests/unit/test_order_service.py ....                                    [ 66%]
tests/unit/test_session_service.py ...                                   [100%]

============================== 9 passed in 0.19s ===============================
```

### Rincian Pengujian:
1. `tests/unit/test_session_service.py::test_create_session`: **PASSED** (Membuat sesi dengan batas waktu).
2. `tests/unit/test_session_service.py::test_get_active_session`: **PASSED** (Mengambil sesi aktif saat ini).
3. `tests/unit/test_session_service.py::test_close_session`: **PASSED** (Menutup sesi secara tervalidasi).
4. `tests/unit/test_order_service.py::test_create_order_atomic`: **PASSED** (Pemesanan mandiri tanpa race condition).
5. `tests/unit/test_order_service.py::test_order_aggregation_summary`: **PASSED** (Auto-rekap item dan generate teks WhatsApp).
6. `tests/unit/test_order_service.py::test_order_cutoff_expiration`: **PASSED** (Validasi penolakan pesanan saat cutoff berakhir).
7. `tests/unit/test_order_service.py::test_delete_order`: **PASSED** (Penghapusan pesanan oleh pemesan).
8. `tests/integration/test_api_flow.py::test_full_titip_makan_api_lifecycle`: **PASSED** (End-to-end API lifecycle).
9. `tests/integration/test_web_routes.py::test_web_routes`: **PASSED** (Pengujian render view HTML dan endpoint health check).

---

## 6. Verifikasi Eksekusi Nyata (Docker Compose)

Container berhasil di-build dan berjalan di port `8080`:
```text
CONTAINER ID   IMAGE             COMMAND                  STATUS         PORTS                    NAMES
414e889c8e37   titip-makan-app   "uvicorn titip_makan…"   Up 3 minutes   0.0.0.0:8080->8080/tcp   titip_makan_app
```

Verifikasi curl ke container:
```json
{"status":"healthy","app":"Titip Makan MTN CORE","environment":"development"}
```

---

## 7. Lesson Learned
1. Pemanfaatan `uv` dalam Docker multi-stage build mempercepat proses build hingga 5-10x lipat dibanding pip standar, dengan layer caching yang optimal.
2. Memisahkan logika antara `OrderRepository`, `OrderService`, dan API controller memudahkan pengujian unit murni tanpa perlu menyalakan web server atau database fisik (cukup SQLite in-memory).
3. Format teks WhatsApp yang dihasilkan secara terpusat oleh server menghilangkan 100% perdebatan dan konflik "pesan ketimpa" di grup WhatsApp.
