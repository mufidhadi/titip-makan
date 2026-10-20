# AI Report: 028 — Pembersihan Menu Terdobel Tenant Dapoer Bumbu & Babun serta Normalisasi Prefix Vendor

## 1. Nama Tugas
Pembersihan List Menu Tenant Dapoer Bumbu agar Tidak Ada yang Terdobel (Khususnya Entri Komposit Bergaris Miring `/`, Ejaan Ganda, dan Terdobel dengan Prefix `Dapoer Bumbu ...`), Pemeriksaan & Pembersihan Serupa pada Tenant Babun, serta Deployment Pembaruan ke Produksi VPS Hostinger `titip-irzi.masmuf.cloud`.

---

## 2. Informasi Repository & Lingkungan
* **Nama & URL Repository**: `git@github.com:mufidhadi/titip-makan.git` / `https://github.com/mufidhadi/titip-makan`
* **Nama Branch**: `task/clean-dapoer-bumbu-and-babun-menu-dedup`
* **Nomor Hash Commit**:
  * Fitur & Fix: `5b60f3b255d9a46a4730eab8a347e261b008fe1d`
  * Laporan AI Report: commit berikutnya
* **Tech Stack**:
  * Python 3.12, `uv` package manager (strictly uv-only)
  * FastAPI, Jinja2, Tailwind CSS, SQLAlchemy / aiosqlite, Pydantic v2
  * Pytest, Playwright (Unit, Integration, dan E2E Test Suite)
  * Docker, Docker Compose, Traefik Reverse Proxy v2.2
  * ZeroTier Private Network (`172.23.127.184` - VPS Hostinger)

---

## 3. Histori Aksi

1. **Riset & Investigasi Akar Penyebab Duplikasi**:
   * Menelusuri implementasi katalog di [`src/titip_makan/core/catalog.py`](file:///Users/anb-0826014/project/mufid/titip-makan/src/titip_makan/core/catalog.py) dan service suggestions di [`src/titip_makan/services/order_service.py`](file:///Users/anb-0826014/project/mufid/titip-makan/src/titip_makan/services/order_service.py).
   * **Akar Masalah 1 (Entri Komposit & Variasi Ejaan di Dapoer Bumbu)**:
     Pada commit sebelumnya, transkripsi menu fisik Dapoer Bumbu memasukkan baris gabungan/garis miring (seperti `Dapoer Bumbu Nasi Ayam Penyet / Kremes / Bakar`, `Dapoer Bumbu Ayam Bakar / Kremes / Penyet (Tanpa Nasi)`, `Dapoer Bumbu Mie / Bihun / Kwetiau Goreng / Rebus`, dll.) serta ejaan ganda (`Nasi Cap Cay` vs `Nasi Capcay`, `Kwitiaw` vs `Kwetiau`, `Teh Manis` vs `Teh Manis Panas`). Hal ini membuat katalog Dapoer Bumbu membengkak menjadi 83 entri.
   * **Akar Masalah 2 (Duplikasi Prefix Vendor di Suggestions API)**:
     Di `order_service.py`, logic lama menulis:
     ```python
     menus_dict[vendor].add(item)
     if item.startswith(f"{vendor} "):
         menus_dict[vendor].add(item[len(vendor) + 1:].strip())
     ```
     Akibatnya, jika `item` di katalog atau database order diawali nama vendor (seperti `Dapoer Bumbu Nasi Ayam Penyet` atau `Babun Nasi Telor Dobel`), kedua versi (dengan prefix dan tanpa prefix) dimasukkan ke list menu dropdown tenant tersebut. Hal ini menduplikasi seluruh 83 item Dapoer Bumbu menjadi 166 pilihan, dan 45 item Babun menjadi 90–98 pilihan di autocomplete.
   * Melakukan riset best practice perancangan autocomplete menu dan deduplikasi prefix ([Coveo Design System & UX Magazine Best Practices](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQFcFrUah5QVyAOkZfv_DT0VkHqvIxMIhBOO4Ao_kWRlcrYtT5rPJWtcKHh7sJpvU3Kd7XJ-mLXqL-ThFV4oFQDLQadnkgkmSv7XeSdTf1ZhTv-bkxAQe56E7IiZpzjqqwsnK7_uyIBK8kgrAgue8QtFVL6OCZuB_AF6GN3e)) yang menekankan penghilangan redundansi visual pada label autocomplete sambil tetap mempertahankan canonical lookup key di layer harga/backend.

2. **Penerapan Test-Driven Development (TDD)**:
   * **Tahap RED**:
     * Menambahkan unit test di [`tests/unit/test_catalog_harga.py`](file:///Users/anb-0826014/project/mufid/titip-makan/tests/unit/test_catalog_harga.py) (`test_dapoer_bumbu_catalog_tidak_ada_menu_terdobel`): memastikan tidak ada entri slash komposit, tidak ada ejaan ganda, dan total item unik Dapoer Bumbu tepat 59 item.
     * Menambahkan unit test di [`tests/unit/test_order_service.py`](file:///Users/anb-0826014/project/mufid/titip-makan/tests/unit/test_order_service.py) (`test_suggestions_no_prefixed_duplicates_dapoer_bumbu_and_babun`): memastikan list `menus["Dapoer Bumbu"]` dan `menus["Babun"]` bebas dari prefix `Dapoer Bumbu ` maupun `Babun `, tidak ada duplikasi, namun dictionary `prices` tetap mampu mengenali kedua bentuk string.
     * Menjalankan `uv run pytest` untuk memverifikasi kegagalan test sebelum kode diperbaiki.
   * **Tahap GREEN & REFACTOR**:
     * Membersihkan `MASTER_CATALOG["Dapoer Bumbu"]` di [`src/titip_makan/core/catalog.py`](file:///Users/anb-0826014/project/mufid/titip-makan/src/titip_makan/core/catalog.py) dari seluruh 24 entri komposit dan ejaan duplikat.
     * Memperbarui logika `get_suggestions` di [`src/titip_makan/services/order_service.py`](file:///Users/anb-0826014/project/mufid/titip-makan/src/titip_makan/services/order_service.py):
       * Mendefinisikan `TENANTS_WITH_VENDOR_PREFIX = {"Babun", "Dapoer Bumbu", "Padang"}`.
       * Pada dropdown `menus[vendor]`, hanya memasukkan nama menu bersih (`clean_name`) tanpa prefix vendor.
       * Pada dictionary `prices`, tetap menyimpan pemetaan untuk `item` dan `clean_name` agar kompatibilitas harga tetap terjaga 100%.
       * Menerapkan pembersihan serupa pada item historis dari database (`distinct_items`).
     * Memperbarui [`src/titip_makan/static/js/app.js`](file:///Users/anb-0826014/project/mufid/titip-makan/src/titip_makan/static/js/app.js) pada handler autofill tenant agar mendeteksi baik nama hidangan murni maupun jika user mengetik `<vendor> <menu>`.
     * Menjalankan seluruh test suite dengan `uv run pytest`: **93 passed in 43.35s**.

3. **Pengujian Visual & Screenshot Lokal**:
   * Memperbarui screenshot lokal catalog di [`docs/screenshots/dapoer_bumbu_catalog_desktop.png`](file:///Users/anb-0826014/project/mufid/titip-makan/docs/screenshots/dapoer_bumbu_catalog_desktop.png) dan [`docs/screenshots/dapoer_bumbu_catalog_mobile.png`](file:///Users/anb-0826014/project/mufid/titip-makan/docs/screenshots/dapoer_bumbu_catalog_mobile.png).

4. **Commit & Push ke Remote Repository**:
   * Commit perubahan lokal dengan pesan commit: `fix(catalog): deduplicate Dapoer Bumbu and Babun menu lists and strip vendor prefixes` (Hash `5b60f3b`).
   * Push branch `task/clean-dapoer-bumbu-and-babun-menu-dedup` ke GitHub `origin`.

5. **Deployment ke VPS Hostinger & Verifikasi Live Produksi**:
   * SSH ke VPS Hostinger (`root@172.23.127.184` via ZeroTier).
   * Melakukan `git fetch origin && git checkout task/clean-dapoer-bumbu-and-babun-menu-dedup && git pull origin task/clean-dapoer-bumbu-and-babun-menu-dedup`.
   * Menjalankan `docker compose up -d --build`.
   * Memverifikasi container status: `titip_makan_app` berjalan up dan sehat (`0.0.0.0:8085->8080/tcp`).
   * Menguji endpoint live API `https://titip-irzi.masmuf.cloud/api/v1/sessions/suggestions`.
   * Menjalankan script Playwright untuk mengambil screenshot live:
     * `docs/screenshots/live_vps_dapoer_bumbu_dedup_desktop.png`
     * `docs/screenshots/live_vps_dapoer_bumbu_dedup_mobile.png`
     * `docs/screenshots/live_vps_babun_dedup_desktop.png`

---

## 4. Hasil Verifikasi Data Produksi Live

Pengujian langsung terhadap endpoint produksi `https://titip-irzi.masmuf.cloud/api/v1/sessions/suggestions`:

### A. Tenant Dapoer Bumbu
* **Total Item Terdaftar**: **59 item** (sebelumnya 166 akibat dobel prefix + komposit slash).
* **Item dengan Prefix "Dapoer Bumbu "**: **0 item** (100% bersih tanpa prefix redundan).
* **Jumlah Duplikasi / Terdobel**: **0 (set kosong)**.
* **Sampel Menu di Suggestion Dropdown**:
  * `Air Mineral`
  * `Air Putih Es`
  * `Ayam Asam Manis (Tanpa Nasi)`
  * `Ayam Bakar (Tanpa Nasi)`
  * `Ayam Garang Asam (Tanpa Nasi)`
  * `Nasi Ayam Penyet`
  * `Nasi Capcay`
  * `Nasi Timbel Komplit`

### B. Tenant Babun
* **Total Item Terdaftar**: **53 item** (45 item master catalog resmi + 8 item varian dari database riil VPS, bersih tanpa prefix).
* **Item dengan Prefix "Babun "**: **0 item** (100% bersih tanpa prefix redundan).
* **Jumlah Duplikasi / Terdobel**: **0 (set kosong)**.
* **Sampel Menu di Suggestion Dropdown**:
  * `Air Mineral`
  * `Cappuccino`
  * `Es Jeruk`
  * `Es Teh Manis`
  * `Kopi Hitam`
  * `Nasi Telor Dobel`
  * `Nasi Ayam Kremes`

### C. Pemetaan Harga (`prices` dictionary)
Lookup harga berjalan dua arah untuk backwards compatibility:
* `prices["Nasi Ayam Penyet"]` = `20000`
* `prices["Dapoer Bumbu Nasi Ayam Penyet"]` = `20000`
* `prices["Nasi Telor Dobel"]` = `13000`
* `prices["Babun Nasi Telor Dobel"]` = `13000`

---

## 5. List Kesulitan, Tantangan, Bug dan Solusi

| No | Isu / Tantangan | Akar Masalah | Solusi |
| :---: | :--- | :--- | :--- |
| 1 | Menu Dapoer Bumbu dan Babun muncul 2x di dropdown suggestions | `order_service.py` memasukkan `item` asli ber-prefix vendor DAN `item[len(vendor)+1:]` ke dalam `menus[vendor]`. | Memperkenalkan set `TENANTS_WITH_VENDOR_PREFIX`. Hanya masukkan `clean_name` ke daftar autocomplete `menus[vendor]`, namun simpan kedua kunci di dictionary `prices`. |
| 2 | Entri menu komposit fisik (`/`) membingungkan pemesan | Transkripsi fisik mencantumkan baris gabungan seperti `Nasi Ayam Penyet / Kremes / Bakar`. | Menghapus seluruh 15 entri komposit bergaris miring karena masing-masing item individualnya sudah terdaftar lengkap dengan harga spesifik. |
| 3 | Ejaan ganda pada Capcay, Kwetiau, dan Minuman | Terdapat ejaan `Nasi Cap Cay` vs `Nasi Capcay` serta varian `Teh Manis` vs `Teh Manis Panas`. | Melakukan standardisasi ejaan baku: `Nasi Capcay`, `Kwetiau Goreng/Rebus`, serta membedakan suhu minuman secara eksplisit (`Teh Manis Panas` vs `Es Teh Manis`). |
| 4 | Regresi pada E2E Playwright Browser Test | Test E2E `test_browser_flow.py` mengetik `"Babun Nasi Telor Dobel"` pada form menu dan mengharapkan form tenant terisi `"Babun"`. Ketika prefix di dropdown dihilangkan, matching tenant sempat gagal. | Memperbarui `app.js` (`handleMenuInput`) agar selain mencocokkan `t.toLowerCase() === val.toLowerCase()`, juga mengecek jika `val.toLowerCase().startsWith(t.toLowerCase() + " ")`. Dengan ini, E2E test dan UX pengetikan langsung tetap lulus mulus. |

---

## 6. List Test yang Dilakukan dan Hasilnya

Semua test dijalankan menggunakan perintah mandatori `uv run pytest`:

| No | File Test | Cakupan Pengujian | Status |
| :---: | :--- | :--- | :---: |
| 1 | [`tests/unit/test_catalog_harga.py`](file:///Users/anb-0826014/project/mufid/titip-makan/tests/unit/test_catalog_harga.py) | Unit test katalog harga, validasi 59 menu unik Dapoer Bumbu, proteksi anti-komposit, dan normalisasi vendor. | **PASSED** |
| 2 | [`tests/unit/test_order_service.py`](file:///Users/anb-0826014/project/mufid/titip-makan/tests/unit/test_order_service.py) | Validasi API suggestions tanpa duplikasi prefix Babun & Dapoer Bumbu, auto-fill harga katalog ganda. | **PASSED** |
| 3 | [`tests/unit/test_data_cleansing.py`](file:///Users/anb-0826014/project/mufid/titip-makan/tests/unit/test_data_cleansing.py) | Validasi fungsi data cleansing dan normalisasi vendor Dapoer Bumbu. | **PASSED** |
| 4 | [`tests/unit/test_session_service.py`](file:///Users/anb-0826014/project/mufid/titip-makan/tests/unit/test_session_service.py) | Manajemen status sesi, cutoff, dan lifecycle order. | **PASSED** |
| 5 | [`tests/integration/test_web_routes.py`](file:///Users/anb-0826014/project/mufid/titip-makan/tests/integration/test_web_routes.py) | Integrasi endpoint web `/menu`, `/`, `/orders`. | **PASSED** |
| 6 | [`tests/e2e/test_menu_catalog_e2e.py`](file:///Users/anb-0826014/project/mufid/titip-makan/tests/e2e/test_menu_catalog_e2e.py) | Pengujian browser Playwright untuk filtering tenant, live search, dan layout responsif mobile. | **PASSED** |
| 7 | [`tests/e2e/test_browser_flow.py`](file:///Users/anb-0826014/project/mufid/titip-makan/tests/e2e/test_browser_flow.py) | Pengujian alur pembuatan order end-to-end via antarmuka browser. | **PASSED** |
| 8 | Endpoint Live API VPS (`/api/v1/sessions/suggestions`) | Verifikasi langsung pada server produksi Hostinger via HTTPS. | **VERIFIED** |

* **Ringkasan Hasil Pytest**: **93 passed in 43.35s** (100% Success).

---

## 7. Bukti Tangkapan Layar (Screenshots)

* Desktop Menu Dapoer Bumbu Bersih & Rapi di Live VPS:
  ![Dapoer Bumbu Live Desktop](file:///Users/anb-0826014/project/mufid/titip-makan/docs/screenshots/live_vps_dapoer_bumbu_dedup_desktop.png)

* Mobile Menu Dapoer Bumbu di Live VPS:
  ![Dapoer Bumbu Live Mobile](file:///Users/anb-0826014/project/mufid/titip-makan/docs/screenshots/live_vps_dapoer_bumbu_dedup_mobile.png)

* Desktop Menu Babun Bebas Prefix di Live VPS:
  ![Babun Live Desktop](file:///Users/anb-0826014/project/mufid/titip-makan/docs/screenshots/live_vps_babun_dedup_desktop.png)

---

## 8. Lesson Learned

1. **Pemisahan Antara Penyajian UI (Presentation Layer) dan Identifikasi Data (Identity/Pricing Layer)**:
   Menyimpan prefix vendor pada nama hidangan (`Babun Nasi Telor Dobel`) sangat berguna untuk disambiguasi data internal jika tanpa relasi foreign key, namun sangat mengganggu user experience jika ditampilkan mentah-mentah di dropdown autocomplete yang sudah berada di bawah filter tenant bersangkutan. Pendekatan memisahkan `clean_name` untuk dropdown dan dual-key lookup untuk dictionary `prices` memberikan solusi ideal: UI ringkas tanpa mengorbankan kompatibilitas order terdahulu.
2. **Kerapian Transkripsi Menu Fisik ke Format Digital**:
   Papan menu restoran sering kali menggabungkan beberapa jenis masakan dalam satu baris dengan tanda garis miring untuk menghemat tempat cetak (misalnya: *Ayam Bakar / Penyet / Kremes*). Saat diintegrasikan ke sistem digital, baris gabungan tersebut tidak boleh dimasukkan sebagai satu entri menu jika entri individualnya sudah terdaftar, karena akan memicu kebingungan bagi pembeli dan menyulitkan pelacakan harga otomatis.
