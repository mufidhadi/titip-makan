# AI Report: 027 — Penambahan Katalog Lengkap Menu Tenant Dapoer Bumbu & Normalisasi Data Produksi

## 1. Nama Tugas
Pelengkapan Database Katalog Menu Tenant Dapoer Bumbu Sesuai Daftar Menu Fisik ke `titip-irzi.masmuf.cloud`, Penambahan Aliases Vendor, Penambahan Aturan Data Hygiene / Data Cleansing, serta Deployment Produksi ke VPS Hostinger.

---

## 2. Informasi Repository & Lingkungan
* **Nama & URL Repository**: `git@github.com:mufidhadi/titip-makan.git` / `https://github.com/mufidhadi/titip-makan`
* **Nama Branch**: `task/add-dapoer-bumbu-catalog-and-menu`
* **Nomor Hash Commit**: `5ceae0e` (commit fitur) & commit laporan akhir ini
* **Tech Stack**:
  * Python 3.12, `uv` package manager
  * SQLite3 (database engine dengan snapshot backup)
  * FastAPI, Jinja2, Tailwind CSS, SQLAlchemy / aiosqlite, Pydantic v2
  * Pytest, Playwright (Unit, Integration, dan E2E Test Suite)
  * Docker, Docker Compose, Traefik Reverse Proxy v2.2
  * ZeroTier Private Network (`172.23.127.184` - VPS Hostinger)

---

## 3. Histori Aksi

1. **Riset & Ekstraksi Data Menu Fisik (Metode OCR & Transkripsi Manual Terverifikasi)**:
   * Melakukan riset best practice perancangan skema katalog restoran dan normalisasi data SQLite ([StackExchange Software Engineering](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQFvQKl0A8a0OBalIKdCL0BpUGrK8CG3ohIdqal8jMsrgopsM2hcfcg6eteDJY04xCawQ5w9V1n4GekGdpYVt2I41-C1YEvPVVRzZwQwxy-y3WrRTQU0fOnslbCqVP5mVUwWbMWtdRmAztFxGTVC1KrsbBl4wJ9pyNv8PH_D_c4xSSwFNOAXIKbsZnkvnkTPocx_XdGcnPOO9TVLqQX3hbyuEFvCW3aCLWjVsdWMMKJ5LIHMFYsokqda17juKA==)).
   * Mentranskripsikan seluruh isi daftar menu fisik "DAPOER BUMBU" dari foto yang diunggah oleh mas mufid:
     * Kategori Olahan Ayam & Paket Nasi (Nasi Ayam Penyet/Kremes/Bakar, Ayam Tanpa Nasi, Nasi Timbel Komplit, Ayam Asam Manis/Tauco/Garang Asam).
     * Kategori Olahan Ikan, Seafood, & Sayur (Nasi Sop Ikan Asam Manis Pedas, Nasi Gurame Asam Manis/Tauco, Nasi Capcay, varian Tanpa Nasi).
     * Kategori Nasi Goreng & Olahan Mie/Bihun/Kwetiau (Nasi Goreng Teri, Nasi Goreng Bakso, Nasi Goreng Mawut campur mie, Mie/Bihun/Kwetiau Goreng/Rebus).
     * Kategori Menu Tambahan (Nasi Putih, Tumis Toge/Kangkung, Tumis Sawi Putih/Ijo, Sayur Asem, Terong Penyet, Telor Dadar/Ceplok, Tahu/Tempe Goreng/Penyet, Kerupuk).
     * Kategori Minuman (Es Jeruk/Lemon Tea, Wedang Jahe, Es Teh Tarik, Es Indocafe/Kopi Tubruk, Air Mineral, Teh Manis, Es Teh Manis, Es Teh Tawar, Air Putih Es, Teh Tawar Panas).
2. **Pemeriksaan Database Eksisting di VPS Produksi**:
   * Menghubungi VPS Hostinger via SSH key native (`root@172.23.127.184`).
   * Menemukan terdapat 8 pesanan historis di bawah vendor `Dapoer Bumbu` (`Nasi Goreng Bakso`, `Nasi Capcay`, `Nasi Capcay + Telor Ceplok`) yang sebelumnya belum terhubung ke harga katalog resmi (harga manual).
3. **Penerapan Test-Driven Development (TDD)**:
   * **Tahap RED**:
     * Menulis unit test baru di [`tests/unit/test_catalog_harga.py`](file:///Users/anb-0826014/project/mufid/titip-makan/tests/unit/test_catalog_harga.py) (`test_menu_dapoer_bumbu_lengkap` dan `test_normalize_vendor_dapoer_bumbu`).
     * Menulis unit test auto-fill harga katalog di [`tests/unit/test_order_service.py`](file:///Users/anb-0826014/project/mufid/titip-makan/tests/unit/test_order_service.py) (`test_create_order_auto_fills_dapoer_bumbu_catalog_price`).
     * Menulis unit test data cleansing di [`tests/unit/test_data_cleansing.py`](file:///Users/anb-0826014/project/mufid/titip-makan/tests/unit/test_data_cleansing.py).
     * Menjalankan `uv run pytest` dan membuktikan test gagal sesuai ekspektasi (RED phase).
   * **Tahap GREEN**:
     * Menambahkan seluruh variasi menu Dapoer Bumbu (dengan estimasi harga resmi) ke `MASTER_CATALOG` di [`src/titip_makan/core/catalog.py`](file:///Users/anb-0826014/project/mufid/titip-makan/src/titip_makan/core/catalog.py).
     * Mendaftarkan alias vendor (`dapoer bumbu`, `dapur bumbu`, `dapoer`, `dapur`) ke `VENDOR_ALIASES` dan fungsi `normalize_vendor()`.
     * Memperbarui aturan normalisasi di [`src/titip_makan/tools/data_cleansing.py`](file:///Users/anb-0826014/project/mufid/titip-makan/src/titip_makan/tools/data_cleansing.py).
     * Memperbarui UI template [`src/titip_makan/templates/menu.html`](file:///Users/anb-0826014/project/mufid/titip-makan/src/titip_makan/templates/menu.html) dengan ikon khas (`🥘`) dan badge oranye lembut (`bg-orange-50 text-orange-700`).
     * Menambahkan assertion integrasi di [`tests/integration/test_web_routes.py`](file:///Users/anb-0826014/project/mufid/titip-makan/tests/integration/test_web_routes.py) dan E2E Playwright di [`tests/e2e/test_menu_catalog_e2e.py`](file:///Users/anb-0826014/project/mufid/titip-makan/tests/e2e/test_menu_catalog_e2e.py).
     * Menjalankan seluruh test suite dengan `uv run pytest`: **91 passed in 31.32s**.
4. **Pengujian Visual & UI Testing (Playwright)**:
   * Mengambil screenshot desktop dan mobile secara lokal dan menyimpannya di `docs/screenshots/dapoer_bumbu_catalog_desktop.png` dan `docs/screenshots/dapoer_bumbu_catalog_mobile.png`.
5. **Deployment ke VPS Produksi & Pembersihan Data**:
   * Commit dan push branch `task/add-dapoer-bumbu-catalog-and-menu` ke GitHub private repo.
   * Melakukan checkout dan pull di VPS Hostinger `/root/project/titip-makan`.
   * Menjalankan dry-run cleaner: mendeteksi 8 pesanan lama Dapoer Bumbu.
   * Menjalankan cleaner riil: snapshot backup database otomatis dibuat di `/root/project/titip-makan/data/titip_makan.db.backup_pre_clean_20261020_075219`.
   * Melakukan re-build dan restart container: `docker compose up -d --build`.
   * Mengambil screenshot bukti render langsung dari situs live `https://titip-irzi.masmuf.cloud/menu`.

---

## 4. Daftar Lengkap Menu Dapoer Bumbu Terdaftar

| No | Nama Menu (Katalog Resmi) | Varian Bebas Prefix | Estimasi Harga (Rp) | Kategori |
| :---: | :--- | :--- | :---: | :--- |
| 1 | `Dapoer Bumbu Nasi Ayam Penyet` | `Nasi Ayam Penyet` | 20.000 | Paket Nasi |
| 2 | `Dapoer Bumbu Nasi Ayam Kremes` | `Nasi Ayam Kremes` | 20.000 | Paket Nasi |
| 3 | `Dapoer Bumbu Nasi Ayam Bakar` | `Nasi Ayam Bakar` | 20.000 | Paket Nasi |
| 4 | `Dapoer Bumbu Nasi Ayam Penyet / Kremes / Bakar` | `Nasi Ayam Penyet / Kremes / Bakar` | 20.000 | Paket Nasi |
| 5 | `Dapoer Bumbu Ayam Bakar (Tanpa Nasi)` | `Ayam Bakar (Tanpa Nasi)` | 15.000 | Lauk Saja |
| 6 | `Dapoer Bumbu Ayam Kremes (Tanpa Nasi)` | `Ayam Kremes (Tanpa Nasi)` | 15.000 | Lauk Saja |
| 7 | `Dapoer Bumbu Ayam Penyet (Tanpa Nasi)` | `Ayam Penyet (Tanpa Nasi)` | 15.000 | Lauk Saja |
| 8 | `Dapoer Bumbu Ayam Bakar / Kremes / Penyet (Tanpa Nasi)` | `Ayam Bakar / Kremes / Penyet (Tanpa Nasi)` | 15.000 | Lauk Saja |
| 9 | `Dapoer Bumbu Nasi Ayam Goreng Asam Manis` | `Nasi Ayam Goreng Asam Manis` | 20.000 | Paket Nasi |
| 10 | `Dapoer Bumbu Nasi Ayam Goreng Tauco` | `Nasi Ayam Goreng Tauco` | 20.000 | Paket Nasi |
| 11 | `Dapoer Bumbu Nasi Ayam Goreng Asam Manis / Tauco` | `Nasi Ayam Goreng Asam Manis / Tauco` | 20.000 | Paket Nasi |
| 12 | `Dapoer Bumbu Ayam Asam Manis (Tanpa Nasi)` | `Ayam Asam Manis (Tanpa Nasi)` | 15.000 | Lauk Saja |
| 13 | `Dapoer Bumbu Ayam Tauco (Tanpa Nasi)` | `Ayam Tauco (Tanpa Nasi)` | 15.000 | Lauk Saja |
| 14 | `Dapoer Bumbu Ayam Garang Asam (Tanpa Nasi)` | `Ayam Garang Asam (Tanpa Nasi)` | 15.000 | Lauk Saja |
| 15 | `Dapoer Bumbu Ayam Asam Manis / Tauco / Garang Asam (Tanpa Nasi)` | `Ayam Asam Manis / Tauco / Garang Asam (Tanpa Nasi)` | 15.000 | Lauk Saja |
| 16 | `Dapoer Bumbu Nasi Ayam Garang Asam` | `Nasi Ayam Garang Asam` | 20.000 | Paket Nasi |
| 17 | `Dapoer Bumbu Nasi Timbel Komplit` | `Nasi Timbel Komplit` | 27.000 | Paket Nasi |
| 18 | `Dapoer Bumbu Nasi Timbel Komplit Ayam Goreng` | `Nasi Timbel Komplit Ayam Goreng` | 27.000 | Paket Nasi |
| 19 | `Dapoer Bumbu Nasi Timbel Komplit Ayam Bakar` | `Nasi Timbel Komplit Ayam Bakar` | 27.000 | Paket Nasi |
| 20 | `Dapoer Bumbu Nasi Sop Ikan Asam Manis Pedas` | `Nasi Sop Ikan Asam Manis Pedas` | 18.000 | Paket Nasi |
| 21 | `Dapoer Bumbu Nasi Gurame Asam Manis` | `Nasi Gurame Asam Manis` | 18.000 | Paket Nasi |
| 22 | `Dapoer Bumbu Nasi Gurame Tauco` | `Nasi Gurame Tauco` | 18.000 | Paket Nasi |
| 23 | `Dapoer Bumbu Nasi Gurame Asam Manis / Tauco` | `Nasi Gurame Asam Manis / Tauco` | 18.000 | Paket Nasi |
| 24 | `Dapoer Bumbu Nasi Cap Cay` | `Nasi Cap Cay` | 18.000 | Paket Nasi |
| 25 | `Dapoer Bumbu Nasi Capcay` | `Nasi Capcay` | 18.000 | Paket Nasi |
| 26 | `Dapoer Bumbu Nasi Capcay + Telor Ceplok` | `Nasi Capcay + Telor Ceplok` | 23.000 | Paket Nasi |
| 27 | `Dapoer Bumbu Cap Cay (Tanpa Nasi)` | `Cap Cay (Tanpa Nasi)` | 14.000 | Lauk Saja |
| 28 | `Dapoer Bumbu Capcay (Tanpa Nasi)` | `Capcay (Tanpa Nasi)` | 14.000 | Lauk Saja |
| 29 | `Dapoer Bumbu Sop Ikan (Tanpa Nasi)` | `Sop Ikan (Tanpa Nasi)` | 14.000 | Lauk Saja |
| 30 | `Dapoer Bumbu Gurame Asam Manis (Tanpa Nasi)` | `Gurame Asam Manis (Tanpa Nasi)` | 14.000 | Lauk Saja |
| 31 | `Dapoer Bumbu Gurame Tauco (Tanpa Nasi)` | `Gurame Tauco (Tanpa Nasi)` | 14.000 | Lauk Saja |
| 32 | `Dapoer Bumbu Cap Cay / Sop Ikan / Gurame Asam Manis / Tauco (Tanpa Nasi)` | `Cap Cay / Sop Ikan / Gurame Asam Manis / Tauco (Tanpa Nasi)` | 14.000 | Lauk Saja |
| 33 | `Dapoer Bumbu Nasi Goreng Teri` | `Nasi Goreng Teri` | 15.000 | Nasi Goreng |
| 34 | `Dapoer Bumbu Nasi Goreng Bakso` | `Nasi Goreng Bakso` | 15.000 | Nasi Goreng |
| 35 | `Dapoer Bumbu Nasi Goreng Teri / Nasi Goreng Bakso` | `Nasi Goreng Teri / Nasi Goreng Bakso` | 15.000 | Nasi Goreng |
| 36 | `Dapoer Bumbu Nasi Goreng Mawut` | `Nasi Goreng Mawut` | 18.000 | Nasi Goreng |
| 37 | `Dapoer Bumbu Nasi Goreng Mawut (Campur Mie)` | `Nasi Goreng Mawut (Campur Mie)` | 18.000 | Nasi Goreng |
| 38 | `Dapoer Bumbu Mie Goreng` | `Mie Goreng` | 15.000 | Mie / Kwetiau |
| 39 | `Dapoer Bumbu Mie Rebus` | `Mie Rebus` | 15.000 | Mie / Kwetiau |
| 40 | `Dapoer Bumbu Bihun Goreng` | `Bihun Goreng` | 15.000 | Mie / Kwetiau |
| 41 | `Dapoer Bumbu Bihun Rebus` | `Bihun Rebus` | 15.000 | Mie / Kwetiau |
| 42 | `Dapoer Bumbu Kwetiau Goreng` | `Kwetiau Goreng` | 15.000 | Mie / Kwetiau |
| 43 | `Dapoer Bumbu Kwetiau Rebus` | `Kwetiau Rebus` | 15.000 | Mie / Kwetiau |
| 44 | `Dapoer Bumbu Kwitiaw Goreng` | `Kwitiaw Goreng` | 15.000 | Mie / Kwetiau |
| 45 | `Dapoer Bumbu Kwitiaw Rebus` | `Kwitiaw Rebus` | 15.000 | Mie / Kwetiau |
| 46 | `Dapoer Bumbu Mie / Bihun / Kwetiau Goreng / Rebus` | `Mie / Bihun / Kwetiau Goreng / Rebus` | 15.000 | Mie / Kwetiau |
| 47 | `Dapoer Bumbu Nasi Putih` | `Nasi Putih` | 5.000 | Tambahan |
| 48 | `Dapoer Bumbu Tumis Toge` | `Tumis Toge` | 8.000 | Tambahan |
| 49 | `Dapoer Bumbu Tumis Kangkung` | `Tumis Kangkung` | 8.000 | Tambahan |
| 50 | `Dapoer Bumbu Tumis Toge / Kangkung` | `Tumis Toge / Kangkung` | 8.000 | Tambahan |
| 51 | `Dapoer Bumbu Tumis Sawi Putih` | `Tumis Sawi Putih` | 8.000 | Tambahan |
| 52 | `Dapoer Bumbu Tumis Sawi Ijo` | `Tumis Sawi Ijo` | 8.000 | Tambahan |
| 53 | `Dapoer Bumbu Tumis Sawi Putih / Ijo` | `Tumis Sawi Putih / Ijo` | 8.000 | Tambahan |
| 54 | `Dapoer Bumbu Sayur Asem` | `Sayur Asem` | 8.000 | Tambahan |
| 55 | `Dapoer Bumbu Terong Penyet` | `Terong Penyet` | 5.000 | Tambahan |
| 56 | `Dapoer Bumbu Telor Dadar` | `Telor Dadar` | 5.000 | Tambahan |
| 57 | `Dapoer Bumbu Telor Ceplok` | `Telor Ceplok` | 5.000 | Tambahan |
| 58 | `Dapoer Bumbu Telor Dadar / Ceplok` | `Telor Dadar / Ceplok` | 5.000 | Tambahan |
| 59 | `Dapoer Bumbu Tahu Goreng` | `Tahu Goreng` | 2.000 | Tambahan |
| 60 | `Dapoer Bumbu Tempe Goreng` | `Tempe Goreng` | 2.000 | Tambahan |
| 61 | `Dapoer Bumbu Tahu / Tempe Goreng` | `Tahu / Tempe Goreng` | 2.000 | Tambahan |
| 62 | `Dapoer Bumbu Tahu Penyet` | `Tahu Penyet` | 3.000 | Tambahan |
| 63 | `Dapoer Bumbu Tempe Penyet` | `Tempe Penyet` | 3.000 | Tambahan |
| 64 | `Dapoer Bumbu Tahu / Tempe Penyet` | `Tahu / Tempe Penyet` | 3.000 | Tambahan |
| 65 | `Dapoer Bumbu Kerupuk` | `Kerupuk` | 2.000 | Tambahan |
| 66 | `Dapoer Bumbu Es Jeruk` | `Es Jeruk` | 8.000 | Minuman |
| 67 | `Dapoer Bumbu Es Lemon Tea` | `Es Lemon Tea` | 8.000 | Minuman |
| 68 | `Dapoer Bumbu Lemon Tea` | `Lemon Tea` | 8.000 | Minuman |
| 69 | `Dapoer Bumbu Es Jeruk / Es Lemon Tea` | `Es Jeruk / Es Lemon Tea` | 8.000 | Minuman |
| 70 | `Dapoer Bumbu Wedang Jahe` | `Wedang Jahe` | 5.000 | Minuman |
| 71 | `Dapoer Bumbu Es Teh Tarik` | `Es Teh Tarik` | 6.000 | Minuman |
| 72 | `Dapoer Bumbu Teh Tarik` | `Teh Tarik` | 6.000 | Minuman |
| 73 | `Dapoer Bumbu Es Indocafe` | `Es Indocafe` | 5.000 | Minuman |
| 74 | `Dapoer Bumbu Kopi Tubruk` | `Kopi Tubruk` | 5.000 | Minuman |
| 75 | `Dapoer Bumbu Es Indocafe / Kopi Tubruk` | `Es Indocafe / Kopi Tubruk` | 5.000 | Minuman |
| 76 | `Dapoer Bumbu Air Mineral` | `Air Mineral` | 4.000 | Minuman |
| 77 | `Dapoer Bumbu Teh Manis` | `Teh Manis` | 4.000 | Minuman |
| 78 | `Dapoer Bumbu Teh Manis Panas` | `Teh Manis Panas` | 4.000 | Minuman |
| 79 | `Dapoer Bumbu Es Teh Manis` | `Es Teh Manis` | 5.000 | Minuman |
| 80 | `Dapoer Bumbu Es Teh Tawar` | `Es Teh Tawar` | 3.000 | Minuman |
| 81 | `Dapoer Bumbu Air Putih Es` | `Air Putih Es` | 2.000 | Minuman |
| 82 | `Dapoer Bumbu Teh Tawar` | `Teh Tawar` | 1.000 | Minuman |
| 83 | `Dapoer Bumbu Teh Tawar Panas` | `Teh Tawar Panas` | 1.000 | Minuman |

---

## 5. List Kesulitan, Tantangan, Bug dan Solusi

1. **Variasi Penulisan Menu Gabungan pada Papan Fisik**:
   * *Tantangan:* Pada papan fisik, beberapa item digabung dalam satu baris, misalnya `Nasi Ayam Penyet / Kremes/ Bakar` (20.000) atau `Mie / Bihun / Kwitiaw Goreng / Rebus` (15.000). Pengguna sistem titip makan umumnya mengetik nama menu spesifik (`Nasi Ayam Penyet` atau `Kwetiau Goreng`), namun ada kemungkinan pengguna lain menyalin seluruh teks baris tersebut.
   * *Solusi:* Mendaftarkan seluruh entri spesifik secara atomik (per menu unik) sekaligus menyediakan entri gabungan di `MASTER_CATALOG`. Dengan demikian, baik pengetikan spesifik maupun pengetikan gabungan sama-sama memiliki estimasi harga valid (tidak Rp 0).
2. **Kabel Menutupi Sebagian Huruf pada Foto Menu Fisik**:
   * *Tantangan:* Sebuah kabel hitam vertikal melintas di tengah papan menu menutupi huruf awal pada beberapa baris (mis. `[y]am goreng Tauco`, `[Aya]m garang asam`, `[ngk]ung`, `[ce]plok`).
   * *Solusi:* Melakukan verifikasi konteks kuliner Indonesia dan analisis perbandingan baris atas-bawah (contoh: baris atas `Nasi ayam garang Asam`, maka baris bawah tanpa nasi adalah `Ayam garang asam (tanpa nasi)`).
3. **Environment Execution Non-Interactive SSH**:
   * *Tantangan:* Pemanggilan langsung `uv` di VPS melalui SSH non-interactive sempat mengembalikan `bash: line 1: uv: command not found` karena `uv` terpasang di `/root/.local/bin/uv` yang belum masuk ke default non-interactive PATH.
   * *Solusi:* Menambahkan prefix `export PATH="/root/.local/bin:$PATH"` pada pemanggilan remote script di VPS sehingga seluruh eksekusi `uv run` berjalan mulus.

---

## 6. List Test yang Dilakukan dan Hasil

Seluruh pengujian dijalankan dengan `uv run pytest`:

| No | Modul Test | Cakupan Uji | Hasil |
| :---: | :--- | :--- | :---: |
| 1 | `tests/unit/test_catalog_harga.py` | Validasi kelengkapan menu Dapoer Bumbu, kewajaran harga (1.000–100.000), dan normalisasi vendor alias | **PASSED** |
| 2 | `tests/unit/test_order_service.py` | Auto-fill harga Dapoer Bumbu saat membuat order dengan harga 0 / alias vendor | **PASSED** |
| 3 | `tests/unit/test_data_cleansing.py` | Eksekusi normalisasi database historis, vendor casing, dan pencegahan data kotor | **PASSED** |
| 4 | `tests/integration/test_web_routes.py` | Endpoint `/menu` menyajikan tenant Dapoer Bumbu beserta harganya | **PASSED** |
| 5 | `tests/e2e/test_menu_catalog_e2e.py` | Playwright E2E: Verifikasi filter pill Dapoer Bumbu, rendering kartu menu, pencarian, dan mobile viewport | **PASSED** |
| 6 | Full Test Suite (`uv run pytest`) | Regresi menyeluruh terhadap 91 test skenario | **91 PASSED (31.32s)** |

---

## 7. Lesson Learned

- Desain sistem autocomplete dan katalog yang fleksibel (mendukung prefixing `Dapoer Bumbu <Item>` dan varian tanpa prefix `<Item>`) terbukti sangat efektif: pengguna yang mengetik secara cepat maupun memilih dari katalog sama-sama mendapatkan harga yang akurat tanpa kebingungan.
- Menjaga kebersihan data historis dengan skrip data cleansing berfitur automatic snapshot backup memberikan rasa aman maksimal saat melakukan perubahan pada database produksi.
