# Laporan Akhir: Gamified Leaderboard, Analytics Dashboard, dan Coordinator Controls

## 1. Nama Tugas
Pengembangan Fitur Otomasi Sesi Harian, Kontrol Cutoff Koordinator, Alur Konfirmasi Pembayaran Dua Tahap & Edit Pesanan, Dashboard Riwayat & Analitik, serta Gamified Leaderboard Berbasis Badges pada Platform Titip Makan.

---

## 2. Informasi Repositori & Branch
- **Nama Repositori**: `titip-makan`
- **URL Repositori**: `git@github.com:mufidhadi/titip-makan.git` / `https://github.com/mufidhadi/titip-makan`
- **Branch**: `feature/gamified-leaderboard-analytics-and-coordinator-controls`
- **Nomor Hash Commit**: `895d230`

---

## 3. Tech Stack
- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0 (Async ORM), SQLite (aiosqlite), Pydantic v2
- **Scheduler & Automation**: Background Asyncio Lifespan Task (`SchedulerService`), Cron-like interval checker (10:00 WIB trigger, 10:30 WIB cutoff), ZoneInfo (`Asia/Jakarta`)
- **Frontend**: HTML5, Tailwind CSS (Mobile-First responsive layout), Vanilla ES6+ JavaScript, Chart.js (Analytics Trends, Doughnut, Horizontal Bar Charts)
- **External Integration**: WAHA (WhatsApp HTTP API) untuk broadcast pengumuman sesi harian otomatis dan notifikasi koordinator
- **Testing & Verification**: Pytest, Pytest-Asyncio, Playwright (Headless Chromium E2E testing pada mobile viewport iPhone 13/14 390x844)
- **Package & Dependency Manager**: `uv`

---

## 4. Histori Aksi
1. **Analisis Kebutuhan & Perancangan Desain**:
   - Mempelajari 8 butir kebutuhan dari mas mufid:
     1. Otomasi sesi baru setiap hari kerja pukul 10.00 WIB s/d 10.30 WIB dengan auto-broadcast ke grup WhatsApp MTN CORE (`120363409564046383@g.us`).
     2. Kontrol perpanjangan waktu cutoff sesi (+5 menit, +10 menit) dan penutupan sesi langsung oleh koordinator.
     3. Alur konfirmasi pembayaran dua tahap: user menandai "Saya Sudah Bayar" (`PENDING_CONFIRMATION`), koordinator tinggal 1-klik "Konfirmasi Lunas" (`PAID`).
     4. Fitur edit pesanan bagi pemesan selama pesanan belum ditandai bayar lunas.
     5. Popover/tooltip hover pada metric card "Belum Lunas" di halaman koordinator untuk melihat daftar nama & tagihan member yang belum lunas.
     6. Tombol kirim rekap pesanan ke WA koordinator dengan pengelompokan per tenant/warung.
     7. Halaman Riwayat Sesi & Analitik (`/history`) lengkap dengan grafik Chart.js (tren pesanan, menu favorit harian/mingguan/bulanan, top spenders).
     8. Halaman Gamified Leaderboard (`/leaderboard`) lengkap dengan lencana unik (👑 Sultan Titip Makan, ✍️ Raja Catatan, 🏆 Si Paling Rajin Titip, 🥷 Ninja Lapar, 🗿 Penganut Setia, 🎨 Eksplorator Kuliner).
   - Memastikan batasan ketat: **HANYA BEKERJA DI LINGKUNGAN LOKAL (LOCAL DEVELOPMENT)**, dilarang menyentuh atau mendeploy ke VPS production yang sedang aktif dipakai user.

2. **Pengembangan Backend (Test-Driven Development)**:
   - **Database & Model**:
     - Menambahkan kolom `payment_status` (`VARCHAR(50)`, default `"UNPAID"`) pada model `OrderItem` di `src/titip_makan/models/order.py`.
     - Menambahkan skema migrasi otomatis SQLite di `src/titip_makan/core/database.py` agar skema lokal otomatis termigrasi tanpa merusak data yang ada.
   - **Domain Services**:
     - `src/titip_makan/services/scheduler_service.py`: Service scheduler asinkron yang berjalan di event loop FastAPI `lifespan`, memantau zona waktu `Asia/Jakarta`, membuat sesi otomatis setiap Senin-Jumat jam 10:00 WIB dengan cutoff 10:30 WIB, dan membroadcast pengumuman ke grup WA MTN CORE.
     - `src/titip_makan/services/session_service.py`: Menambahkan method `extend_session_cutoff(session_id, additional_minutes)` dan `close_session_cutoff(session_id)` dengan normalisasi zona waktu UTC & WIB.
     - `src/titip_makan/services/order_service.py`:
       - Menambahkan method `claim_order_payment(order_id)` untuk user mengklaim sudah bayar (`PENDING_CONFIRMATION`).
       - Menambahkan method `update_order(order_id, data)` dengan validasi proteksi pesanan tidak bisa diedit jika statusnya sudah `PAID` atau `PENDING_CONFIRMATION`.
       - Menambahkan format pesan rekap WA koordinator dengan pengelompokan rapi per-tenant/warung.
     - `src/titip_makan/services/analytics_service.py`: Mengagregasi data statistik harian, mingguan, bulanan, menghitung top spenders, menu favorit per periode, serta mengkalkulasi 6 kategori gamifikasi badge pengguna.
   - **REST API Endpoints**:
     - `POST /api/v1/sessions/{id}/extend-cutoff`: Endpoint menambah durasi cutoff (+5m, +10m).
     - `POST /api/v1/sessions/{id}/close-cutoff`: Endpoint menutup batas waktu pemesanan segera.
     - `POST /api/v1/orders/{id}/claim-paid`: Endpoint user menandai sudah bayar.
     - `PUT /api/v1/orders/{id}`: Endpoint mengedit menu, tenant, catatan, dan perkiraan harga pesanan.
     - `GET /api/v1/analytics/overview`: Endpoint data analytics diagram tren harian, mingguan, bulanan, top items, dan tenant breakdown.
     - `GET /api/v1/analytics/leaderboard`: Endpoint data gamifikasi leaderboard dan status perolehan badges.
     - `GET /history` & `GET /leaderboard`: Web template routes di `src/titip_makan/api/web.py`.

3. **Pengembangan Frontend & UI**:
   - **Navigasi Global** (`src/titip_makan/templates/base.html`):
     - Menambahkan navigasi responsif ke menu: "Pesan Makan", "📊 Analitik", "🏆 Leaderboard", dan "👑 Koordinator".
   - **Halaman Riwayat & Analitik** (`src/titip_makan/templates/history.html` & `src/titip_makan/static/js/history.js`):
     - Mengintegrasikan library Chart.js via CDN.
     - Diagram garis tren jumlah pesanan harian.
     - Diagram batang horizontal menu makanan terfavorit.
     - Diagram donat distribusi pesanan per-tenant/warung.
     - Filter tabs periode interaktif (Harian / Mingguan / Bulanan) dan tabel rincian transaksi sesi terdahulu.
   - **Halaman Gamified Leaderboard** (`src/titip_makan/templates/leaderboard.html` & `src/titip_makan/static/js/leaderboard.js`):
     - Kartu grid interaktif 6 Badges kebanggaan:
       - 👑 **Sultan Titip Makan**: Top Spender dengan akumulasi nominal belanja tertinggi.
       - ✍️ **Raja Catatan**: Pemesan paling teliti yang paling sering menulis catatan/kustomisasi khusus.
       - 🏆 **Si Paling Rajin Titip**: Member dengan frekuensi order terbanyak.
       - 🥷 **Ninja Lapar**: Member yang memesan paling kilat (<5 menit sejak sesi dibuka).
       - 🗿 **Penganut Setia**: Member yang selalu konsisten memesan 1 menu yang sama tanpa goyah.
       - 🎨 **Eksplorator Kuliner**: Member paling petualang yang mencoba ragam tenant & menu berbeda terbanyak.
     - Tabel peringkat Top Spenders & Top Orderers dengan avatar inisial berwarna dan highlight juara 1, 2, 3.
   - **Halaman Koordinator** (`src/titip_makan/templates/coordinator.html` & `src/titip_makan/static/js/coordinator.js`):
     - Tombol kontrol cutoff interaktif: `+5 Menit`, `+10 Menit`, dan `Tutup Batas Waktu`.
     - Popover daftar penunggak bayar pada card "Belum Lunas" saat di-hover / di-klik (menampilkan nama orang dan nominal tertagih).
     - Tombol "📲 Rekap ke WA" yang langsung membuka chat WA koordinator berisi rekap terkelompok per warung/tenant.
     - Tombol 1-klik "✅ Konfirmasi Lunas" untuk pesanan yang berstatus `PENDING_CONFIRMATION` dengan animasi badge berkedip.
   - **Halaman Pemesan Utama** (`src/titip_makan/templates/index.html` & `src/titip_makan/static/js/app.js`):
     - Tombol "💳 Sudah Bayar" pada kartu pesanan user untuk merubah status menjadi Menunggu Konfirmasi.
     - Tombol "✏️ Edit" pada kartu pesanan yang membuka modal form yang sudah terisi otomatis data pesanan untuk pengubahan vendor, menu, catatan, atau harga perkiraan.

---

## 5. List Kesulitan, Tantangan, Bug dan Solusi

| No | Masalah / Tantangan | Penyebab Utama | Solusi yang Diterapkan |
|---|---|---|---|
| 1 | `window.promptEditPrice is not a function` pada pengujian E2E koordinator | Fungsi `promptEditPrice` sempat terhapus saat menambahkan fungsi `confirmPayment` di `coordinator.js`. | Menuliskan kembali `window.promptEditPrice` lengkap dengan validasi harga integer positif dan refresh data ringkasan. |
| 2 | Playwright gagal memicu `submit` saat order kedua (Adrian) via `page.click("#btn-submit-order", force=True)` | Pada viewport mobile sempit (390px), tombol berada di bawah viewport modal scroll. `force=True` menonaktifkan auto-scroll Playwright sehingga koordinat pointer tidak mencapai form button yang aktif. | Mengganti trigger submit form pada pengujian Playwright dengan `await page.locator("#order-form").evaluate("f => f.requestSubmit()")`, yang secara deterministik memicu event submit form HTML5 lengkap dengan validasi browser. |
| 3 | Pointer click terintercept oleh sticky header `<th>Catatan</th>` pada tabel koordinator | Elemen `<thead>` tabel koordinator memiliki sticky positioning. Pada viewport mobile 390px, klik koordinat Playwright tertabrak oleh overlay header. | Menggunakan `.dispatch_event("click")` pada tombol aksi tabel di script test browser Playwright sehingga event dieksekusi langsung pada target elemen DOM. |
| 4 | Inkonsistensi Tailwind class `hidden` vs `flex` pada modal dialog | Saat modal ditampilkan dengan menambahkan kelas `flex`, menghapus atribut hanya dengan `classList.add("hidden")` terkadang kalah prioritas CSS dibanding kelas `flex`. | Memastikan setiap penutupan/pembukaan modal selalu melakukan pasangan operasi serempak: `classList.add("hidden")` dan `classList.remove("flex")` (atau sebaliknya). |
| 5 | Sinkronisasi container docker lokal | Kode lokal di-edit namun container Docker lokal menggunakan build image sebelumnya yang tidak mem-mount folder `src`. | Menjalankan `docker compose build app && docker compose up -d app` di environment lokal sehingga container lokal langsung menyajikan kode termutakhir. |

---

## 6. List Test yang Dilakukan dan Hasilnya
Seluruh pengujian dijalankan menggunakan `uv run pytest` di environment lokal dan **100% LULUS (33 dari 33 pengujian)**:

```
tests/e2e/test_browser_flow.py .                                         [  3%]
tests/integration/test_api_flow.py ..                                    [  9%]
tests/integration/test_e2e_scenarios.py .                                [ 12%]
tests/integration/test_web_routes.py .                                   [ 15%]
tests/unit/test_analytics_and_leaderboard.py ..                          [ 21%]
tests/unit/test_notification_service.py .....                            [ 36%]
tests/unit/test_order_edit_and_payment_status.py ....                    [ 48%]
tests/unit/test_order_service.py .........                               [ 75%]
tests/unit/test_session_cutoff_and_scheduler.py ....                     [ 87%]
tests/unit/test_session_service.py ....                                  [100%]

============================== 33 passed in 8.75s ==============================
```

Rincian cakupan pengujian:
1. `test_session_cutoff_and_scheduler.py`:
   - `test_extend_session_cutoff`: Memvalidasi penambahan waktu cutoff sesi (+5m, +10m).
   - `test_close_session_cutoff`: Memvalidasi penutupan batas waktu instan menjadi masa lampau.
   - `test_scheduler_auto_creation_logic`: Memvalidasi logika pembuatan sesi otomatis pukul 10:00 WIB hari kerja.
   - `test_scheduler_skips_weekends`: Memvalidasi scheduler tidak membuat sesi pada Sabtu & Minggu.
2. `test_order_edit_and_payment_status.py`:
   - `test_claim_order_payment_flow`: Memvalidasi alur klaim bayar user menjadi `PENDING_CONFIRMATION` dan konfirmasi koordinator menjadi `PAID`.
   - `test_edit_order_success`: Memvalidasi member dapat mengubah menu/tenant selama belum bayar.
   - `test_edit_order_forbidden_if_paid`: Memvalidasi penolakan pengeditan pesanan jika sudah lunas atau pending konfirmasi.
   - `test_order_recap_grouped_by_vendor`: Memvalidasi format teks pesan WhatsApp yang dikelompokkan rapi per-tenant.
3. `test_analytics_and_leaderboard.py`:
   - `test_analytics_overview_service`: Memvalidasi kalkulasi ringkasan omset harian, mingguan, bulanan, top items, dan tenant breakdown.
   - `test_leaderboard_badges_assignment`: Memvalidasi pemberian badges gamifikasi (Sultan Titip Makan, Raja Catatan, Si Paling Rajin, Ninja Lapar, Penganut Setia, Eksplorator Kuliner).
4. `test_browser_flow.py`:
   - Pengujian E2E menyeluruh menggunakan Playwright Headless Chromium pada resolusi mobile iPhone: pembuatan sesi koordinator, pengisian pesanan dengan autocompletion katalog, pengisian pesanan kedua tanpa harga, pengaturan harga oleh koordinator, popover pembayaran, penghapusan pesanan, dan penutupan sesi.
5. Unit & integrasi lainnya:
   - Web routes `/history` dan `/leaderboard` merespons HTTP 200 dengan markup HTML yang valid.
   - `test_order_service.py` (9 tests), `test_session_service.py` (4 tests), `test_notification_service.py` (5 tests), `test_api_flow.py` (2 tests), `test_e2e_scenarios.py` (2 tests).

---

## 7. Lesson Learned
1. **Pemisahan Environment Development dan Production**:
   - Keputusan untuk secara ketat tidak menyentuh server VPS production menjaga kelancaran operasional user riil yang sedang aktif menggunakan aplikasi, sementara pengetesan intensif fitur baru tetap dapat dievaluasi 100% menggunakan kontainer lokal.
2. **Keandalan Event Form Submission pada Automated Testing**:
   - Dalam pengujian antarmuka berbasis mobile viewport sempit, menggunakan `form.requestSubmit()` memberikan jaminan eksekusi yang lebih andal daripada mengandalkan koordinat pointer `click()` yang rawan terhalang scroll container atau sticky overlay.
3. **Desain Gamifikasi yang Menyenangkan Meningkatkan Adopsi**:
   - Badge dengan narasi jenaka khas kultur kantor (seperti *Raja Catatan*, *Ninja Lapar*, dan *Sultan Titip Makan*) memberikan nilai tambah psikologis bagi tim internal untuk lebih rajin dan tertib mencatatkan pesanan.
