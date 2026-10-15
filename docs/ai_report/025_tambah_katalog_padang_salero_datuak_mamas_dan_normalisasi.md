# AI Report: 025 — Penambahan Katalog Padang Salero Datuak Mamas & Normalisasi Data Anti-Kotor

## 1. Nama Tugas
Penambahan Katalog Lengkap Menu Padang Salero Datuak Mamas (Foodcourt), Normalisasi Vendor Alias, dan Pencegahan Data Kotor (*Data Hygiene*) pada Database SQLite Produksi Titip Makan.

---

## 2. Informasi Repository & Lingkungan
* **Nama & URL Repository**: `git@github.com:mufidhadi/titip-makan.git` / `https://github.com/mufidhadi/titip-makan`
* **Nama Branch**: `task/padang-vendor-normalization-and-cleansing`
* **Nomor Hash Commit**: `54e68f5` (dan commit laporan ini)
* **Tech Stack**:
  * Python 3.12, `uv` package manager
  * SQLite3 (database engine)
  * FastAPI, SQLAlchemy / Aiosqlite, Pydantic
  * Pytest, Playwright (Test Suite)
  * Docker, Docker Compose, Traefik Reverse Proxy
  * ZeroTier Private Network (`172.23.127.184`)

---

## 3. Histori Aksi

1. **Analisis Kebutuhan Data & Potensi Konflik (*Data Hygiene*)**:
   * Mas mufid meminta penambahan 32 menu Padang Salero Datuak Mamas Foodcourt ke katalog dengan memastikan data tetap bersih.
   * Investigasi menemukan bahwa pada database produksi sebelumnya terdapat 6 pesanan historis dengan nama vendor informal `Kantin Mamas` dan menu `Nasi Padang Rendang`, `Nasi Padang Ayam Bakar`, `Nasi Padang Ayam Gulai`.
   * Di sisi lain, pada PR #7 tenant didaftarkan dengan key `Padang` dan menu diawali prefix `Padang `.
   * Jika tidak diselaraskan, hal ini akan menimbulkan:
     1. Duplikasi vendor pada autocomplete (`Kantin Mamas` vs `Padang`).
     2. Duplikasi menu (`Nasi Padang Rendang` vs `Padang Nasi Rendang` vs `Nasi Rendang`).
     3. Pesanan tanpa harga (Rp 0) jika pengguna memilih nama variasi tanpa prefix.
2. **Pengembangan Fitur Normalisasi & Auto-Fill Harga (TDD)**:
   * Menambahkan `VENDOR_ALIASES` dan fungsi `normalize_vendor()` di [`src/titip_makan/core/catalog.py`](file:///Users/anb-0826014/project/mufid/titip-makan/src/titip_makan/core/catalog.py):
     * Memetakan variasi `kantin mamas`, `padang salero datuak`, `padang salero datuak mamas`, `salero datuak`, `mamas` $\rightarrow$ kanonikal `Padang`.
   * Memperbarui [`src/titip_makan/services/order_service.py`](file:///Users/anb-0826014/project/mufid/titip-makan/src/titip_makan/services/order_service.py):
     * Di `create_order`: otomatis menjalankan `normalize_vendor` pada nama vendor pemesan.
     * Di `create_order`: jika pesanan masuk dengan `price <= 0`, otomatis mencocokkan nama menu dengan katalog dan mengisikan harga resmi secara otomatis (mencegah harga Rp 0).
     * Di `get_suggestions`: mendaftarkan harga baik dengan prefix maupun tanpa prefix (`Padang Nasi Rendang` dan `Nasi Rendang` sama-sama bernilai Rp 23.000).
   * Menulis unit test di [`tests/unit/test_catalog_harga.py`](file:///Users/anb-0826014/project/mufid/titip-makan/tests/unit/test_catalog_harga.py) dan [`tests/unit/test_order_service.py`](file:///Users/anb-0826014/project/mufid/titip-makan/tests/unit/test_order_service.py).
   * Menjalankan seluruh test suite dengan `uv run pytest`: **85 passed in 33.74s**.
3. **Pembersihan Data Historis di VPS Produksi**:
   * Membuat backup snapshot database di `/root/project/titip-makan/data/titip_makan.db.backup_pre_clean_20261015_111704`.
   * Menjalankan migrasi 6 data pesanan lama:
     * Vendor `Kantin Mamas` $\rightarrow$ `Padang`.
     * Menu `Nasi Padang Ayam Bakar` $\rightarrow$ `Padang Nasi Ayam Bakar`.
     * Menu `Nasi Padang Ayam Gulai` $\rightarrow$ `Padang Nasi Ayam Gulai`.
     * Menu `Nasi Padang Rendang` $\rightarrow$ `Padang Nasi Rendang`.
   * Membangun ulang dan restart container di VPS via `docker compose up -d --build`.
4. **Verifikasi Hasil Akhir**:
   * Query database SQLite membuktikan vendor `Kantin Mamas` telah bersih (0 baris), seluruh 6 pesanan tergabung rapi di vendor `Padang`.
   * Endpoint `GET /api/v1/sessions/suggestions` memuat 7 vendor resmi tanpa duplikasi.
   * Dictionary `prices` memuat harga valid untuk seluruh variasi pengetikan (dengan dan tanpa prefix).

---

## 4. Daftar Lengkap 32 Menu Padang & Harga Resmi

| No | Nama Menu (Katalog) | Nama Alias / Alternatif | Harga (Rp) | Kategori |
| :---: | :--- | :--- | :---: | :--- |
| 1 | `Padang Nasi Ayam Bakar` | `Nasi Ayam Bakar` | 23.000 | Paket Nasi |
| 2 | `Padang Nasi Ayam Gulai` | `Nasi Ayam Gulai` | 23.000 | Paket Nasi |
| 3 | `Padang Nasi Ayam Goreng` | `Nasi Ayam Goreng` | 23.000 | Paket Nasi |
| 4 | `Padang Nasi Paru` | `Nasi Paru` | 23.000 | Paket Nasi |
| 5 | `Padang Nasi Rendang` | `Nasi Rendang` | 23.000 | Paket Nasi |
| 6 | `Padang Nasi Dendeng` | `Nasi Dendeng` | 23.000 | Paket Nasi |
| 7 | `Padang Nasi Cincang` | `Nasi Cincang` | 23.000 | Paket Nasi |
| 8 | `Padang Nasi Telur Dadar` | `Nasi Telur Dadar` | 23.000 | Paket Nasi |
| 9 | `Padang Nasi Telur Balado` | `Nasi Telur Balado` | 23.000 | Paket Nasi |
| 10 | `Padang Nasi Tunjang` | `Nasi Tunjang` | 30.000 | Paket Nasi |
| 11 | `Padang Nasi Ikan Kembung Goreng` | `Nasi Ikan Kembung Goreng` | 22.000 | Paket Nasi |
| 12 | `Padang Nasi Ikan Salem Goreng` | `Nasi Ikan Salem Goreng` | 22.000 | Paket Nasi |
| 13 | `Padang Nasi Ikan Kembung Bakar` | `Nasi Ikan Kembung Bakar` | 22.000 | Paket Nasi |
| 14 | `Padang Nasi Ikan Salem Bakar` | `Nasi Ikan Salem Bakar` | 22.000 | Paket Nasi |
| 15 | `Padang Nasi Ikan Bawal Bakar` | `Nasi Ikan Bawal Bakar` | 22.000 | Paket Nasi |
| 16 | `Padang Nasi Ikan Tongkol Balado` | `Nasi Ikan Tongkol Balado` | 20.000 | Paket Nasi |
| 17 | `Padang Ikan Kembung` | `Ikan Kembung` | 14.000 | Lauk Saja |
| 18 | `Padang Ikan Salem` | `Ikan Salem` | 14.000 | Lauk Saja |
| 19 | `Padang Ikan Tongkol Balado` | `Ikan Tongkol Balado` | 20.000 | Lauk Saja |
| 20 | `Padang Ikan Bawal Bakar` | `Ikan Bawal Bakar` | 14.000 | Lauk Saja |
| 21 | `Padang Telur Dadar` | `Telur Dadar` | 8.000 | Lauk Saja |
| 22 | `Padang Terong` | `Terong` | 5.000 | Lauk Saja |
| 23 | `Padang Perkedel` | `Perkedel` | 4.000 | Lauk Saja |
| 24 | `Padang Telur Balado` | `Telur Balado` | 6.000 | Lauk Saja |
| 25 | `Padang Ayam Bakar` | `Ayam Bakar` | 16.000 | Lauk Saja |
| 26 | `Padang Ayam Goreng` | `Ayam Goreng` | 16.000 | Lauk Saja |
| 27 | `Padang Ayam Gulai` | `Ayam Gulai` | 16.000 | Lauk Saja |
| 28 | `Padang Dendeng` | `Dendeng` | 16.000 | Lauk Saja |
| 29 | `Padang Paru` | `Paru` | 16.000 | Lauk Saja |
| 30 | `Padang Rendang` | `Rendang` | 16.000 | Lauk Saja |
| 31 | `Padang Cincang` | `Cincang` | 16.000 | Lauk Saja |
| 32 | `Padang Tunjang` | `Tunjang` | 22.000 | Lauk Saja |

---

## 5. List Kesulitan, Tantangan, Bug dan Solusi

1. **Konflik Naming Casing & Pengetikan Informal**:
   * *Masalah:* Anggota tim kerap mengetik "Mamas", "Kantin Mamas", "Salero Datuak", atau "Padang Salero Datuak Mamas" secara bergantian.
   * *Solusi:* Implementasi kamus `VENDOR_ALIASES` di `catalog.py` yang otomatis menormalisasi semua variasi case-insensitive ke kanonikal `Padang`.
2. **Variasi Penulisan Menu dengan dan tanpa Prefix**:
   * *Masalah:* Pengguna sering mengetik hanya "Nasi Rendang" alih-alih "Padang Nasi Rendang". Jika katalog hanya menyimpan nama ber-prefix, harga tidak terdeteksi otomatis dan pesanan tersimpan Rp 0.
   * *Solusi:* Sistem autocomplete dan backend `create_order` kini mendukung pencocokan dwiarah (dengan dan tanpa prefix).
3. **Data Historis di Database**:
   * *Masalah:* Database produksi memiliki 6 rekaman lama dengan label `Kantin Mamas`.
   * *Solusi:* Skrip `data_cleansing.py` mengeksekusi normalisasi rekaman historis tersebut ke vendor dan nama menu resmi.

---

## 6. List Test yang Dilakukan dan Hasilnya

* **Unit Test Normalisasi Vendor & Katalog**:
  * `tests/unit/test_catalog_harga.py::test_menu_padang_salero_datuak_mamas_lengkap` $\rightarrow$ **PASSED**
  * `tests/unit/test_catalog_harga.py::test_normalize_vendor_padang_salero_datuak` $\rightarrow$ **PASSED**
* **Unit Test Auto-Fill Harga**:
  * `tests/unit/test_order_service.py::test_create_order_auto_fills_catalog_price_if_zero` $\rightarrow$ **PASSED**
* **Unit Test Data Cleansing**:
  * `tests/unit/test_data_cleansing.py::test_clean_fixes_all_anomalies` $\rightarrow$ **PASSED**
* **Full Test Suite (Lokal)**:
  * `uv run pytest` $\rightarrow$ **85 passed in 33.74s**.
* **Verifikasi Live API VPS**:
  * `curl -s http://127.0.0.1:8085/api/v1/sessions/suggestions | jq .tenants` $\rightarrow$ Hanya 7 tenant resmi, tidak ada duplikat `Kantin Mamas`.

---

## 7. Lesson Learned

* Mencegah data kotor harus dilakukan di dua sisi: di tingkat migrasi data historis (*database cleansing*) dan di pintu masuk (*input normalization & catalog auto-fill*).
* Menyediakan fleksibilitas pengetikan bagi pengguna (misal: alias vendor dan menu tanpa prefix) sambil tetap menyimpan data dalam format kanonikal yang bersih adalah pendekatan terbaik untuk menjaga integritas data tanpa merusak kenyamanan pengguna.
