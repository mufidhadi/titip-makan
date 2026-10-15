# Laporan Pengerjaan Fitur: Halaman Katalog Tenant dan Menu Makanan

- **Nama Tugas:** Pembuatan Fitur Halaman Baru Katalog Tenant dan Menu Makanan (`/menu`)
- **Nomor Hash Commit:** `4ce6035`
- **Nama Branch:** `feature/tenant-menu-catalog-page`
- **Nama dan URL Repo:** `titip-makan` (`git@github.com:mufidhadi/titip-makan.git`)
- **Tech Stack:** Python 3.12, FastAPI, Jinja2, Tailwind CSS, Playwright, Pytest, Uvicorn, Docker Compose, SQLite.

---

## 1. Histori Aksi

1. **Analisis Kebutuhan & Desain Antarmuka:**
   - Menganalisis kebutuhan user mas mufid untuk menampilkan daftar tenant/warung makan beserta seluruh varian menunya secara bersih dan terstruktur.
   - Merancang antarmuka mobile-first responsif dengan:
     - Header ringkasan statistik (total tenant, total menu terdaftar, status sesi aktif).
     - Input pencarian real-time (live search) instan tanpa reload, dengan tombol reset / clear.
     - Horizontal pill buttons untuk quick filtering per tenant (`Padang`, `Babun`, `Mie Ayam`, `Buah Potong`, `Kantin`, dll.) beserta badge jumlah menu masing-masing.
     - Grid kartu menu dengan badge aksen warna khas tiap tenant, nama menu, harga terformat Rupiah (`Rp 23.000`), dan CTA tombol "Pesan".
     - Integrasi seamless ke form order beranda (`/?vendor=...&item=...`) yang otomatis membuka modal pemesanan dan mengisi input secara otomatis (prefill).
     - Empty state ramah jika pencarian tidak menemukan hasil.

2. **Penerapan Test-Driven Development (TDD):**
   - Menulis integration test baru di `tests/integration/test_web_routes.py` untuk menguji route `GET /menu`.
   - Menjalankan `uv run pytest tests/integration/test_web_routes.py` dan memverifikasi kegagalan awal (HTTP 404 - Red Phase).
   - Mengimplementasikan endpoint `GET /menu` pada `src/titip_makan/api/web.py` yang mengambil data suggestions resmi dari `OrderService` dan menyajikan data terstruktur ke template Jinja2.
   - Menemukan bug Jinja2: benturan nama atribut `dict.items` bawaan Python saat iterasi di template `menu.html`, segera memperbaikinya menjadi `menu_items` (Green Phase).
   - Menambahkan navigasi link `📋 Katalog Menu` pada desktop header dan mobile collapsible menu drawer di `src/titip_makan/templates/base.html`.
   - Menambahkan logic `handleUrlPrefill()` pada `src/titip_makan/static/js/app.js` untuk auto-open modal pemesanan dan auto-fill nama tenant, nama menu, dan harga ketika user mengklik tombol "Pesan" dari halaman katalog.

3. **Verifikasi End-to-End (E2E) & Visual Regression:**
   - Menulis suite pengujian Playwright E2E lengkap di `tests/e2e/test_menu_catalog_e2e.py` menguji render halaman, live search filtering, filter pill tenant, empty search state, navigasi responsif, dan memastikan tidak ada horizontal overflow pada viewport mobile (390x844).
   - Menjalankan full regression test suite: 88 passed dalam 52.37s.
   - Mengambil screenshot bukti visual: `docs/screenshots/menu_catalog_desktop.png` dan `docs/screenshots/menu_catalog_mobile.png`.

---

## 2. List Kesulitan, Tantangan, Bug dan Solusi

1. **Jinja2 Dict `.items` Collision:**
   - *Tantangan:* Ketika mengirimkan dictionary yang memiliki key `"items"` (`t.items`), Jinja2 menganggapnya sebagai pemanggilan method `dict.items()` bawaan Python sehingga memunculkan error `TypeError: 'builtin_function_or_method' object is not iterable`.
   - *Solusi:* Merename key dictionary data menjadi `"menu_items"` di `web.py` dan `menu.html` sehingga iterasi Jinja2 berjalan mulus dan aman.

2. **Playwright Strict Mode Conflict:**
   - *Tantangan:* Pemanggilan `locator("h1")` menghasilkan 2 elemen karena logo beranda di navbar juga menggunakan tag `<h1>`.
   - *Solusi:* Mempertegas target locator menjadi `locator("main h1")` pada script test E2E.

---

## 3. List Test yang Dilakukan dan Hasil

Semua test dijalankan dengan `uv run pytest`:

| No | Modul Test | Lingkup Pengujian | Hasil |
|---|---|---|---|
| 1 | `tests/integration/test_web_routes.py` | Status code 200 untuk `GET /menu`, verifikasi teks tenant & menu | **PASSED** |
| 2 | `tests/e2e/test_menu_catalog_e2e.py` | UI rendering, live search, tenant pill filter, empty state, mobile layout | **PASSED** |
| 3 | `tests/e2e/test_responsive_navigation_e2e.py` | Navigasi menu pada desktop dan mobile drawer | **PASSED** |
| 4 | Full Test Suite (`uv run pytest`) | Seluruh 88 skenario unit, integrasi, dan E2E tanpa regresi | **88 PASSED (52.37s)** |

---

## 4. Lesson Learned

- Prinsip TDD membantu menangkap benturan sintaks Jinja2 (`dict.items`) di tahap awal sebelum kode menyentuh server produksi.
- Prefill query string parameter (`/?vendor=...&item=...`) menciptakan alur pengguna (user journey) yang sangat cepat dan menyenangkan: pengguna cukup melihat katalog, memilih makanan yang disukai, dan form pemesanan langsung terisi otomatis beserta estimasi harganya.
