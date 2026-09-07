# Laporan Pengerjaan: Pengujian End-to-End (E2E) & Penyelesaian Bug Platform Titip Makan

## 1. Informasi Tugas
* **Nama Tugas:** Pengujian End-to-End (E2E) Menyeluruh, Investigasi & Penyelesaian Bug (Timezone Cutoff, Persistensi Sesi Koordinator, Notifikasi UI, & Playwright Browser Automation)
* **Tanggal Pengerjaan:** 07 September 2026
* **Nama Branch:** `fix/e2e-bugs-and-improvements`
* **Nomor Hash Commit:** `0d3def453e6a1cbe484bbcfab6d430609d62870e`
* **Nama dan URL Repo:** Lokal (`/Users/anb-0826014/project/mufid/titip-makan`)

---

## 2. Tech Stack
* **Runtime & Package Management:** Python 3.12 via `uv` (Astral)
* **Backend Framework:** FastAPI 0.141+ & SQLAlchemy Async (`aiosqlite`)
* **Data Validation & Serialization:** Pydantic v2 (dengan kustom `@field_serializer` UTC ISO 8601 `Z`)
* **Testing:**
  * Unit & Integrasi: `pytest`, `pytest-asyncio`, `httpx` (ASGITransport)
  * End-to-End Browser Automation: `playwright` (Chromium headless)
* **Containerization:** Docker & Docker Compose
* **Frontend:** HTML5, Tailwind CSS, Vanilla JavaScript (Komponen Toast Non-blocking)

---

## 3. Histori Aksi
1. **Pemeriksaan Komprehensif Alur Kerja Aplikasi (E2E Audit):**
   * Meninjau perjalanan pengguna (user journey) mulai dari pembuatan sesi oleh koordinator, pemilihan menu standar & kustom oleh anggota, pembatalan mandiri, rekonsiliasi pembayaran, penutupan sesi, hingga penyalinan rekap pesanan ke WhatsApp.
2. **Identifikasi Kumpulan Bug Kritis:**
   * Menemukan 4 masalah utama:
     1. **Timezone Parsing Bug:** Cutoff sesi langsung dianggap kadaluarsa/ditutup saat dibuka di browser WIB (UTC+7) karena SQLite menyimpan datetime naive tanpa penanda zona waktu `Z`.
     2. **Hilangnya Dashboard Koordinator Pasca-Penutupan:** Endpoint `/api/v1/sessions/active` mengembalikan `null` begitu status berubah menjadi `CLOSED`, menyebabkan tampilan koordinator seketika hilang dan kembali ke form "Buka Sesi Baru", sehingga koordinator kehilangan akses ke rekap WA dan checklist pembayaran.
     3. **FastAPI Path Collision:** Route `/api/v1/sessions/latest` jika ditaruh setelah `/{session_id}` menimbulkan error validasi integer `422 Unprocessable Entity`.
     4. **Dialog `window.alert()` Memblokir Otomasi & UX Buruk:** Pemanggilan native `alert()` membekukan thread browser dan menyebabkan timeout saat integrasi pengujian E2E headless.
3. **Penerapan TDD (Test-Driven Development):**
   * Membuat skenario integrasi E2E di `tests/integration/test_e2e_scenarios.py` untuk memverifikasi seluruh siklus hidup sesi dan pesanan.
   * Menulis browser E2E test otomatis menggunakan Playwright di `tests/e2e/test_browser_flow.py`.
4. **Perbaikan Backend & Skema Data:**
   * Menambahkan Pydantic serializer `@field_serializer("cutoff_at", "created_at")` di `schemas/session.py` dan `schemas/order.py` agar selalu mengekspor format UTC ISO 8601 dengan akhiran `Z`.
   * Menambahkan query `get_latest_session()` di `SessionRepository` dan endpoint `GET /api/v1/sessions/latest` yang dideklarasikan sebelum parameter dinamis `/{session_id}`.
   * Menambahkan auto-close sesi lama di `SessionRepository.create()` agar sesi yang masih `OPEN` sebelumnya otomatis ditutup saat sesi baru dibuat.
5. **Perbaikan Frontend (`base.html`, `app.js`, `coordinator.js`):**
   * Mengganti semua dialog native `alert()` dengan komponen notifikasi non-blocking modern `showToast(message, type)` pada `base.html`.
   * Memperbaiki parsing tanggal di `app.js` dan `coordinator.js` menggunakan fungsi `parseUtcDate()` yang mengenali string berakhiran `Z`.
   * Memperbarui antarmuka koordinator agar tetap menampilkan kartu manajemen sesi aktif/terakhir meskipun statusnya sudah `CLOSED`, lengkap dengan banner status dan tombol salin rekap.
6. **Eksekusi Pengujian & Verifikasi Nyata:**
   * Menjalankan seluruh test suite dengan `uv run pytest`. Seluruh 12 test (E2E browser, integrasi API, web routes, unit service) berhasil lulus 100%.
   * Membangun ulang (rebuild) image Docker dan memverifikasi container `titip_makan_app` berjalan sehat (`healthy`).
   * Menghasilkan bukti tangkapan layar otomatis (screenshot) di `docs/screenshots/`.

---

## 4. List Kesulitan, Tantangan, Bug dan Solusi

| No | Masalah / Bug | Penyebab Teknis | Solusi Komprehensif |
|---|---|---|---|
| 1 | Sesi baru langsung berstatus "DITUTUP" di browser | SQLite menyimpan kolom datetime tanpa metadata timezone. Saat diserialisasi default oleh Pydantic, string tidak memiliki suffix `Z`. Browser pengguna di zona waktu Asia/Jakarta (UTC+7) menganggapnya waktu lokal atau terjadi pergeseran 7 jam ke masa lampau. | Menerapkan `@field_serializer` di Pydantic schemas untuk memaksa output format ISO 8601 UTC berakhiran `Z` (`YYYY-MM-DDTHH:MM:SSZ`), serta menyertakan helper JavaScript `parseUtcDate()` untuk parsing deterministik. |
| 2 | Dashboard koordinator hilang saat sesi ditutup | Frontend koordinator hanya memanggil `/api/v1/sessions/active`. Saat koordinator mengklik "Tutup Sesi Sekarang", status berubah menjadi `CLOSED` sehingga endpoint mengembalikan `null` dan halaman me-reset ke form pembuatan sesi kosong. | Membuat endpoint `GET /api/v1/sessions/latest` di backend. Frontend koordinator dan pengguna memanggil endpoint ini sehingga sesi yang baru saja ditutup tetap tampil dengan badge `SESI SUDAH DITUTUP` serta ringkasan order dan tombol WhatsApp tetap dapat diakses. |
| 3 | Route collision `GET /api/v1/sessions/latest` menghasilkan 422 | Urutan registrasi route FastAPI menempatkan `/{session_id}` sebelum `/latest`, sehingga string `"latest"` dipaksa diparsing menjadi tipe data `int`. | Memindahkan deklarasi route `/sessions/latest` mendahului route dengan parameter dinamis `/{session_id}` di router FastAPI. |
| 4 | Sesi lama tetap berstatus `OPEN` saat sesi baru dibuat | Operasi create session sebelumnya tidak membatasi jumlah sesi `OPEN`, sehingga sesi-sesi usang dapat menyebabkan kebingungan endpoint `active`. | Menambahkan logika di repository yang secara otomatis memperbarui semua sesi sebelumnya yang berstatus `OPEN` menjadi `CLOSED` sebelum sesi baru disimpan. |
| 5 | Native `alert()` memblokir interaksi & Playwright crash | Penggunaan `window.alert()` bersifat modal sinkron dan membekukan thread eksekusi browser, memicu error `Protocol error: Not attached to an active page` pada automation. | Mengimplementasikan Toast UI berbasis Tailwind di `base.html` (`showToast(msg, type)`) dengan transisi animasi CSS non-blocking dan auto-dismiss 3 detik. |

---

## 5. List Test yang Dilakukan dan Hasil dari Test

Pengujian dijalankan melalui command:
```bash
uv run pytest
```

### Hasil Eksekusi Output Asli:
```text
============================= test session starts ==============================
platform darwin -- Python 3.12.14, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/anb-0826014/project/mufid/titip-makan
configfile: pyproject.toml
testpaths: tests
plugins: asyncio-1.4.0, anyio-4.15.1
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 12 items

tests/e2e/test_browser_flow.py .                                         [  8%]
tests/integration/test_api_flow.py .                                     [ 16%]
tests/integration/test_e2e_scenarios.py .                                [ 25%]
tests/integration/test_web_routes.py .                                   [ 33%]
tests/unit/test_order_service.py .....                                   [ 75%]
tests/unit/test_session_service.py ...                                   [100%]

============================== 12 passed in 7.41s ==============================
```

### Rincian Cakupan Test:
1. `tests/e2e/test_browser_flow.py`: Pengujian otomatis browser Chromium headless (Playwright) meniru skenario pengguna nyata:
   - Koordinator membuat sesi via form UI.
   - Anggota memilih Quick Name "Amal", memilih vendor default "Mie Ayam", varian, catatan, dan submit order.
   - Anggota lain memilih custom vendor "Soto Betawi Bang Mamat", menu kustom, dan harga manual.
   - Koordinator memverifikasi total pesanan & nominal, mengubah status pembayaran menjadi lunas, menghapus pesanan uji coba, dan menutup sesi.
   - Memvalidasi tampilan home dan koordinator beralih ke status `DITUTUP` dan tombol submit di-disable.
2. `tests/integration/test_e2e_scenarios.py`: Validasi backend penuh untuk lifecycle sesi, format ISO 8601 UTC dengan `Z`, persistensi `/sessions/latest` pasca `CLOSED`, pemformatan rupiah rekapitulasi, dan auto-close sesi usang.
3. `tests/integration/test_api_flow.py`: Validasi REST API endpoints sesi dan order.
4. `tests/integration/test_web_routes.py`: Validasi render halaman web frontend (`/`, `/coordinator`, `/menu-data`).
5. `tests/unit/test_order_service.py`: Unit test kalkulasi pesanan, pemformatan mata uang, agregasi ringkasan belanjaan, dan custom menu handling.
6. `tests/unit/test_session_service.py`: Unit test logika pembukaan sesi, batas cutoff, dan otentikasi PIN koordinator.

---

## 6. Verifikasi Tangkapan Layar Otomatis (Screenshots)
Hasil eksekusi Playwright disimpan pada folder `docs/screenshots/`:
* `docs/screenshots/e2e_coordinator_verified.png`: Memperlihatkan dashboard koordinator pasca-penutupan sesi dengan badge `DITUTUP`, metrik pesanan terakumulasi, rekap WA siap salin, dan status pembayaran lunas.
* `docs/screenshots/e2e_home_closed_verified.png`: Memperlihatkan halaman utama pemesanan dengan badge `SESI DITUTUP` serta tombol pemesanan dalam kondisi nonaktif.

---

## 7. Status Kontainer Docker
Container Docker berjalan normal dan telah diperbarui dengan image terbaru:
```text
NAME              IMAGE             COMMAND                  SERVICE   CREATED          STATUS                    PORTS
titip_makan_app   titip-makan-app   "uvicorn titip_makan…"   app       14 seconds ago   Up 12 seconds (healthy)   0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp
```

---

## 8. Lesson Learned
* **UTC Serialization Standard:** SQLite tidak menyimpan informasi zona waktu asli. Memaksa serialisasi ISO 8601 berakhiran `Z` via serializer Pydantic adalah praktik krusial untuk mencegah distorsi perhitungan waktu di antarmuka klien browser.
* **Non-blocking UI Feedback:** Menggantikan native browser dialog (`alert`) dengan komponen toast kustom meningkatkan kenyamanan pengguna secara drastis serta membuat aplikasi kompatibel dengan automation testing tanpa interupsi modal dialog.
* **UX Persistensi Pasca-Aksi:** Mengubah status entitas dari `OPEN` ke `CLOSED` seharusnya tidak menghapus tampilan kerja pengguna; koordinator tetap memerlukan akses data untuk keperluan rekonsiliasi dan komunikasi keluar (WhatsApp).
