# AI Report: 023 — Data Cleansing Database VPS Titip Makan

## 1. Nama Tugas
Pembersihan Data (*Data Cleansing*), Normalisasi Tenant & Menu, serta Perbaikan Data Harga Nol pada Database SQLite Produksi di VPS Titip Makan.

---

## 2. Informasi Repository & Lingkungan
* **Nama & URL Repository**: `git@github.com:mufidhadi/titip-makan.git` / `https://github.com/mufidhadi/titip-makan`
* **Nama Branch**: `task/data-cleansing-vps-database`
* **Nomor Hash Commit**: `61e0560` (dan commit laporan ini)
* **Tech Stack**:
  * Python 3.12, `uv` package manager
  * SQLite3 (database engine)
  * FastAPI, SQLAlchemy / Aiosqlite, Pydantic
  * Pytest, Playwright (Test Suite)
  * Docker, Docker Compose, Traefik Reverse Proxy
  * ZeroTier Private Network

---

## 3. Histori Aksi

1. **Investigasi Data Kotor Awal di VPS (`172.23.127.184`)**:
   * Melakukan query langsung ke database `/root/project/titip-makan/data/titip_makan.db`.
   * Menemukan 329 pesanan dengan 73 kombinasi variasi data kotor:
     * Tenant typo/salah kolom: `babu` (1x), `Andrean` (1x), `Mie ayam` (3x, huruf kecil), `gado-gado` (23x, salah kategori vendor padahal menu di bawah Kantin).
     * Cross-tenant menu: `Mie Ayam Pangsit Rebus` tercatat di bawah vendor `Babun` (1x).
     * Menu duplikat: variasi nama pada Telor Dobel Babun (4 variasi), Ayam Bakar Babun (4 variasi), Mie Ayam Bakso (2 variasi).
     * 5 data pesanan dengan `price = 0` (rekening Rp 0).
2. **Pengembangan Modul Data Cleansing dengan Prinsip TDD**:
   * Membuat file test unit [`tests/unit/test_data_cleansing.py`](file:///Users/anb-0826014/project/mufid/titip-makan/tests/unit/test_data_cleansing.py).
   * Mengimplementasikan modul modular [`src/titip_makan/tools/data_cleansing.py`](file:///Users/anb-0826014/project/mufid/titip-makan/src/titip_makan/tools/data_cleansing.py) dengan class `DatabaseCleaner` dan DTO `CleansingReport` yang menerapkan prinsip SOLID.
   * Menjalankan unit test dengan `uv run pytest tests/unit/test_data_cleansing.py` (2 passed).
   * Menjalankan seluruh test suite regresi dengan `uv run pytest` (74 passed in 30.86s).
3. **Commit & Push ke GitHub**:
   * Commit `61e0560`: `feat(tools): add database cleaner module and tests for data hygiene`.
   * Push ke remote branch `task/data-cleansing-vps-database`.
4. **Eksekusi di VPS Produksi**:
   * Menghubungkan ke VPS via SSH (`172.23.127.184`).
   * Melakukan git fetch & checkout branch `task/data-cleansing-vps-database`.
   * Menjalankan uji kering (*dry-run*) dengan `uv run src/titip_makan/tools/data_cleansing.py ... --dry-run` (hasil: 52 fixes terdeteksi, 0 error).
   * Menjalankan eksekusi pembersihan nyata dengan pembuatan backup otomatis:
     * Lokasi backup: `/root/project/titip-makan/data/titip_makan.db.backup_pre_clean_20261015_105942`.
     * Total perbaikan diterapkan: 52 baris (29 vendor fix, 18 menu fix, 5 price fix).
5. **Verifikasi Hasil Pembersihan**:
   * Query database SQLite: `SELECT COUNT(*) WHERE price <= 0` menghasilkan **0**.
   * Query vendor: daftar vendor bersih menjadi 7 tenant resmi (`Babun`, `Mie Ayam`, `Kantin`, `Buah Potong`, `Kantin Parkiran`, `Kantin Mamas`, `Dapoer Bumbu`).
   * Curl API `GET /api/v1/sessions/suggestions`: saran autocomplete kini sepenuhnya bersih dari typo dan nama ganda.

---

## 4. Rincian Perbaikan Data (*Cleansing Breakdown*)

### A. Perbaikan Vendor (29 baris)
* **`babu` $\rightarrow$ `Babun`** (1 baris: Order ID 80 oleh Amal).
* **`Mie ayam` $\rightarrow$ `Mie Ayam`** (3 baris: Order ID 91, 97, 173).
* **`Andrean` $\rightarrow$ `Mie Ayam`** (1 baris: Order ID 40 oleh Andre yang salah mengisi nama pemesan ke kolom vendor).
* **Cross-vendor fix** (1 baris: Order ID 209 oleh Harist memesan `Mie Ayam Pangsit Rebus` dengan vendor `Babun` $\rightarrow$ dipindahkan ke `Mie Ayam`).
* **`gado-gado` $\rightarrow$ `Kantin`** (23 baris: Order ID 59, 68, 70, 76, 81, 85, 87, 89, 110, 128, 134, 135, 156, 221, 223, 226, 274, 275, 276, 277, 279, 288, 295).

### B. Perbaikan Menu (18 baris)
* Variasi `Nasi + telor dadar bakar double` & `Nasi telor double` (12 baris) $\rightarrow$ `Babun Nasi Telor Dobel`.
* Variasi `Ayam bakar`, `Nasi Ayam bakar`, `Nasi ayam bakar` (3 baris) $\rightarrow$ `Babun Nasi Ayam Bakar`.
* `Nasi goreng ayam` (1 baris) $\rightarrow$ `Babun Nasi Goreng Ayam`.
* `Nasi goreng rendang` (1 baris) $\rightarrow$ `Babun Nasi Goreng Rendang`.
* `Mie ayam bakso pangsit rebus` (1 baris) $\rightarrow$ `Mie Ayam Bakso (Pangsit Rebus)`.

### C. Perbaikan Harga Nol (5 baris)
* **ID 77** (Repka, Babun Nasi Telor Dobel): Rp 0 $\rightarrow$ **Rp 13.000**
* **ID 78** (Raka, Kantin Parkiran Nasi Tongseng Ayam): Rp 0 $\rightarrow$ **Rp 25.000** (sesuai harga ID 75 pada sesi yang sama)
* **ID 205** (Shazi, Babun Nasi Telor Dobel): Rp 0 $\rightarrow$ **Rp 13.000**
* **ID 297** (Diky, Babun Nasi Telor + Tahu + Tempe): Rp 0 $\rightarrow$ **Rp 15.000**
* **ID 321** (Raka, Kantin Mamas Nasi Padang Rendang): Rp 0 $\rightarrow$ **Rp 23.000**

---

## 5. List Kesulitan, Tantangan, Bug dan Solusi

1. **Feedback Loop Data Kotor pada Autocomplete**:
   * *Tantangan*: Autocomplete membaca riwayat langsung dari tabel `order_items`. Sekali ada input typo dari pengguna, data tersebut langsung diajukan sebagai saran bagi pengguna lain.
   * *Solusi*: Data di tabel `order_items` dinormalisasi secara menyeluruh, sehingga query DISTINCT hanya memunculkan nama kanonikal yang valid.
2. **Ketiadaan Harga untuk Menu Non-Katalog**:
   * *Tantangan*: Ketika pengguna memilih menu kustom dari riwayat autocomplete, harga tidak tersedia di `prices_dict`, dan form frontend mengizinkan submit dengan harga 0.
   * *Solusi*: Seluruh harga 0 diperbaiki dengan harga pesanan serupa pada sesi terkait, serta disiapkan pemetaan acuan harga yang konsisten.
3. **Environment VPS Non-Interactive PATH**:
   * *Tantangan*: Command `which uv` di non-interactive SSH gagal karena binary `uv` berada di `/root/.local/bin/uv`.
   * *Solusi*: Menambahkan `export PATH="/root/.local/bin:$PATH"` saat memanggil perintah `uv run` via SSH.

---

## 6. List Test yang Dilakukan dan Hasilnya

* **Unit Test Cleansing Tool**:
  * `tests/unit/test_data_cleansing.py::test_dry_run_does_not_modify` $\rightarrow$ **PASSED**
  * `tests/unit/test_data_cleansing.py::test_clean_fixes_all_anomalies` $\rightarrow$ **PASSED**
* **Full Regression Test Suite**:
  * Menjalankan `uv run pytest` di seluruh repositori:
  * **Hasil**: **74 passed in 30.86s** (termasuk e2e Playwright, integrasi API, dan unit tests).
* **Verifikasi SQL di VPS**:
  * `SELECT COUNT(*) FROM order_items WHERE price <= 0` $\rightarrow$ Hasil: **0**
  * `SELECT vendor, COUNT(*) FROM order_items GROUP BY vendor` $\rightarrow$ Hasil: seluruh typo lenyap, hanya 7 tenant resmi.
* **Verifikasi API Endpoint VPS**:
  * `curl -s http://127.0.0.1:8085/api/v1/sessions/suggestions` $\rightarrow$ Valid JSON, tenant dan menu bersih dan rapi.

---

## 7. Lesson Learned

* Selalu sediakan fitur *dry-run* dan *automatic backup* sebelum melakukan manipulasi data di database produksi.
* Mengandalkan query bebas `DISTINCT` dari user input untuk saran autocomplete tanpa validasi/sanitasi di titik masuk (*entry point*) adalah anti-pattern yang menyebabkan kontaminasi data eksponensial.
* Validasi input harga pada frontend dan backend sebaiknya tidak mengizinkan nilai `0` secara implisit kecuali secara eksplisit ada toggle "Tanya Koordinator / Belum Tahu Harga".
