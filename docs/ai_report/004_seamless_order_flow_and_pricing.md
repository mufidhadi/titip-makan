# Laporan Pengerjaan: Perombakan Alur Seamless, Autocomplete Suggestion, & Fleksibilitas Harga Koordinator

## 1. Informasi Tugas
* **Nama Tugas:** Perombakan Alur Pemesanan Seamless UX (Tabel-Pertama, Modal Tambah Pesanan, Datalist Autocomplete Tenant/Menu, Notifikasi Otomatis ke Koordinator via WhatsApp, dan Fleksibilitas Pengisian Harga oleh Koordinator)
* **Tanggal Pengerjaan:** 07 September 2026
* **Nama Branch:** `feature/seamless-order-flow`
* **Nomor Hash Commit:** `633fd4e51b7619dc74418f77974dac731cbb18a0`
* **Nama dan URL Repo:** Lokal (`/Users/anb-0826014/project/mufid/titip-makan`)

---

## 2. Tech Stack
* **Runtime & Package Management:** Python 3.12 via `uv` (Astral)
* **Backend Framework:** FastAPI 0.141+ & SQLAlchemy Async (`aiosqlite`)
* **Data Validation & Serialization:** Pydantic v2 (dengan schema `OrderPriceUpdate`, `coordinator_phone`, serializer UTC ISO 8601 `Z`)
* **Testing:**
  * Unit & Integrasi: `pytest`, `pytest-asyncio`, `httpx` (ASGITransport)
  * End-to-End Browser Automation: `playwright` (Chromium headless)
* **Containerization:** Docker & Docker Compose
* **Frontend:** HTML5 (HTML `<datalist>` Autocomplete), Tailwind CSS, Vanilla JavaScript Modern

---

## 3. Histori Aksi
1. **Analisis Kebutuhan & Riset Alur Pengguna Rendah Resistensi (Low Friction UX):**
   * Melakukan riset implementasi autocomplete fleksibel menggunakan elemen native HTML `<datalist>` dikombinasikan dengan text input. Pola ini memberikan kebebasan penuh bagi pengguna untuk mengetik tenant/menu baru tanpa perlu memilih opsi khusus atau dropdown manual yang kaku.
   * Merancang alur bebas resistensi: **Buka Aplikasi ➔ Langsung Lihat Tabel Pesanan ➔ Klik "Tambah Pesanan" ➔ Isi Form Ringkas (Datalist Suggestion) ➔ Simpan ➔ Muncul Layar 1-Klik "Beri Notif Koordinator via WhatsApp" ➔ Otomatis Kembali Melihat Tabel Pesanan Terkumpul**.
2. **Pembuatan Branch Baru:**
   * Membuat branch isolasi `feature/seamless-order-flow` dari `fix/e2e-bugs-and-improvements`.
3. **Penerapan TDD (Test-Driven Development):**
   * Menulis unit test baru di `tests/unit/test_order_service.py` untuk menguji:
     * Pembuatan pesanan tanpa harga (opsional, default 0).
     * Pembaruan harga pesanan oleh koordinator melalui service `update_order_price()`.
     * Pengambilan data saran dinamis (suggestions) dari pesanan yang pernah masuk.
   * Menulis integration test di `tests/integration/test_api_flow.py` untuk endpoint:
     * `PATCH /api/v1/orders/{order_id}/price`
     * `GET /api/v1/sessions/{session_id}/suggestions`
     * Kolom `coordinator_phone` pada pembuatan sesi.
   * Menjalankan `uv run pytest` dan memverifikasi kegagalan awal (Red Stage).
4. **Implementasi Backend & Skema Data:**
   * Memperbarui model SQLAlchemy `PoolSession` dengan kolom `coordinator_phone` dan migrasi runtime aman di `init_db()`.
   * Menambahkan schema Pydantic `OrderPriceUpdate` serta menambahkan `coordinator_phone` pada `SessionCreate` dan `SessionOut`.
   * Menambahkan method `update_price()` dan `get_distinct_items()` pada `OrderRepository`.
   * Mengembangkan logika `get_suggestions()` pada `OrderService` yang menggabungkan katalog bawaan, pilihan tenant sesi, dan riwayat pesanan nyata di database.
   * Mendaftarkan route `PATCH /orders/{order_id}/price` di `orders.py` dan `GET /sessions/{session_id}/suggestions` di `sessions.py`.
5. **Perombakan Frontend Antarmuka Anggota (`index.html` & `app.js`):**
   * Mengubah tata letak halaman utama: **Tabel Pesanan Terkumpul** kini menjadi fokus utama (full-width) langsung terlihat saat aplikasi dibuka.
   * Menempatkan tombol utama yang menonjol: **`➕ Tambah Pesanan`**.
   * Membangun Modal Popup interaktif (`#modal-order`) untuk form input pesanan:
     * Quick Name chips (`Amal`, `Mufid`, `Shazi`, `Adrian`, dll) dengan integrasi `localStorage`.
     * Input Tenant bebas ketik dengan autocomplete `<datalist id="datalist-tenants">`.
     * Input Menu bebas ketik dengan `<datalist id="datalist-menus">` yang reaktif terhadap tenant yang diketik.
     * Varian bebas ketik / pilihan opsional.
     * Estimasi Harga dibuat opsional (bisa dikosongkan jika belum tahu).
   * Membangun Layar Notifikasi Koordinator:
     * Setelah klik "Simpan Pesanan", modal beralih menampilkan kartu sukses dan tombol 1-klik: **`📲 Beri Notif ke Koordinator via WhatsApp`** (`https://wa.me/...`).
     * Tersedia tombol salin teks pesan untuk dibagikan ke grup MTN CORE, serta tombol kembali ke tabel.
   * Memperbarui tabel dengan penanda `⏳ Belum di-set` untuk pesanan tanpa harga, serta highlight baris pesanan milik pengguna yang sedang aktif.
6. **Peningkatan Antarmuka Koordinator (`coordinator.html` & `coordinator.js`):**
   * Menambahkan input opsional `Nomor WhatsApp Koordinator` di formulir pembuatan sesi.
   * Menambahkan fitur inline price editing pada kolom Biaya tabel koordinator:
     * Jika harga 0: muncul badge `Belum di-set` dan tombol `✏️ Set`.
     * Jika harga sudah ada: muncul nominal dan icon pensil `✏️` untuk penyesuaian harga kapan saja.
     * Menggunakan dialog prompt cepat yang langsung memperbarui DB dan menghitung ulang metrik total tagihan seketika.
7. **Pembaruan & Verifikasi E2E Headless Browser (`test_browser_flow.py`):**
   * Memperbarui skenario Playwright meniru alur seamless baru secara penuh.
   * Menjalankan `uv run pytest` — seluruh 15 test lulus 100%.
   * Membangun ulang kontainer Docker dan memverifikasi container berstatus `healthy`.
   * Menghasilkan screenshot bukti di `docs/screenshots/`.

---

## 4. List Kesulitan, Tantangan, Bug dan Solusi

| No | Masalah / Tantangan | Penyebab | Solusi |
|---|---|---|---|
| 1 | Pengguna ragu memesan jika tidak mengetahui harga makanan | Form sebelumnya mewajibkan atau mengunci harga per-menu, memicu resistensi pengguna yang hanya ingin menitip tanpa tahu nominal pasti. | Mengubah field harga menjadi opsional di form anggota (default 0), dan menyediakan tombol cepat `✏️ Set` bagi koordinator untuk mengisi atau merevisi harga di dashboard koordinator. |
| 2 | Kebutuhan input tenant & menu baru yang fleksibel tanpa resistensi dropdown | Form sebelumnya menggunakan `<select>` kaku yang mengharuskan memilih opsi `__custom__` terlebih dahulu sebelum muncul input teks tambahan. | Mengganti dropdown `<select>` dengan text `<input list="...">` yang terhubung ke elemen `<datalist>`. Pengguna bebas mengetik apa saja; jika item sudah pernah dipesan, saran otomatis muncul; jika belum pernah, pengguna cukup melanjutkan mengetik biasa. |
| 3 | Pengguna lupa memberi tahu koordinator setelah submit | Setelah pesanan tersimpan, tidak ada instruksi jelas untuk mengabari koordinator, sehingga koordinator sering tidak menyadari ada pesanan baru. | Menambahkan langkah konfirmasi instan di dalam modal pasca-simpan dengan tombol **`📲 Beri Notif ke Koordinator via WhatsApp`** (`wa.me`) lengkap dengan template pesan siap kirim dan nomor koordinator yang dituju. |
| 4 | Penghitungan total belanjaan saat ada harga bernilai 0 | Item belanjaan teragregasi dan baris pemesan dapat menampilkan format harga Rp 0 yang ambigu jika belum diisi. | Menambahkan penanda badge `⏳ Belum di-set` pada tabel dan menampilkan keterangan `(Belum di-set)` pada teks rekapitulasi WhatsApp. |

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
collected 15 items

tests/e2e/test_browser_flow.py .                                         [  6%]
tests/integration/test_api_flow.py ..                                    [ 20%]
tests/integration/test_e2e_scenarios.py .                                [ 26%]
tests/integration/test_web_routes.py .                                   [ 33%]
tests/unit/test_order_service.py .......                                 [ 80%]
tests/unit/test_session_service.py ...                                   [100%]

============================== 15 passed in 8.51s ==============================
```

### Rincian 15 Test Suite:
1. `tests/e2e/test_browser_flow.py`: Pengujian browser headless Playwright mensimulasikan alur seamless lengkap:
   - Koordinator membuka sesi baru dengan nomor WhatsApp.
   - Anggota membuka `/`, langsung melihat tabel antrean, membuka modal "Tambah Pesanan".
   - Mengisi nama cepat "Amal", mengetik tenant "Mie Ayam", varian, dan menyimpan.
   - Memverifikasi munculnya layar notifikasi WhatsApp dengan tautan `wa.me`.
   - Mengisi pesanan kedua "Adrian" untuk tenant baru "Soto Betawi Bang Mamat" dengan harga dikosongkan (opsional).
   - Memverifikasi pesanan Adrian muncul di tabel dengan badge `Belum di-set`.
   - Koordinator membuka dashboard, melihat pesanan Adrian, mengklik `✏️ Set` dan mengisi Rp 35.000 via prompt -> total terakumulasi menjadi Rp 50.000.
   - Koordinator menandai pembayaran lunas, menghapus pesanan uji coba, dan menutup sesi.
   - Memverifikasi tombol tambah pesanan di halaman utama otomatis dinonaktifkan (`🔒 Pemesanan Ditutup`).
2. `tests/integration/test_api_flow.py`:
   - Pengujian siklus hidup API.
   - Pengujian pembaruan harga pesanan via `PATCH /orders/{order_id}/price` dan endpoint `GET /sessions/{session_id}/suggestions`.
3. `tests/integration/test_e2e_scenarios.py`: Validasi backend full-lifecycle integrasi DB isolated.
4. `tests/integration/test_web_routes.py`: Validasi rendering routing web template.
5. `tests/unit/test_order_service.py`: 7 unit test untuk pembuatan order, agregasi belanjaan, deadline cutoff, penghapusan, tenant kustom, harga opsional & pembaruan koordinator, serta generasi data saran autocomplete.
6. `tests/unit/test_session_service.py`: 3 unit test untuk pembuatan sesi, auto-close sesi lama, dan validasi PIN koordinator.

---

## 6. Verifikasi Tangkapan Layar Otomatis (Screenshots)
File tangkapan layar otomatis dari Playwright disimpan di:
* `docs/screenshots/e2e_coordinator_seamless.png`: Dashboard koordinator dengan metrik harga ter-update secara inline, daftar belanjaan per-tenant, checklist lunas, dan status sesi ditutup.
* `docs/screenshots/e2e_home_seamless_closed.png`: Halaman utama dengan tabel pesanan penuh, status badge ditutup, dan tombol pesanan dinonaktifkan.

---

## 7. Status Kontainer Docker
Container Docker berjalan normal dan telah diperbarui dengan image terbaru:
```text
NAME              IMAGE             COMMAND                  SERVICE   CREATED          STATUS                    PORTS
titip_makan_app   titip-makan-app   "uvicorn titip_makan…"   app       45 seconds ago   Up 44 seconds (healthy)   0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp
```

---

## 8. Lesson Learned
* **Table-First Pattern:** Mengedepankan tabel pesanan saat pengguna membuka aplikasi memberikan transparansi instan: pengguna langsung mengetahui siapa saja yang sudah menitip dan apa yang dipesan teman-temannya tanpa harus menggulir form panjang.
* **HTML5 `<datalist>` Autocomplete:** Menggantikan select-box dengan text input yang terhubung ke `<datalist>` memangkas friksi secara dramatis. Pengguna tidak merasa "terpaksa" memilih opsi baku atau mengaktifkan mode manual tambahan.
* **Decoupling Price Entry:** Memisahkan kewajiban pengisian harga dari pengguna ke koordinator menyelesaikan salah satu penyebab utama resistensi pemesanan titip makan di tim kantor, karena seringkali anggota tidak mengetahui harga pasti sebelum koordinator membelinya di lokasi.
