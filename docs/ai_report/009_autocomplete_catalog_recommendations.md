# Laporan Akhir: Rekomendasi Auto-Complete Katalog Menu & Auto-Fill Harga

## 1. Informasi Tugas
- **Nama Tugas:** Rekomendasi Auto-Complete Katalog Menu & Auto-Fill Estimasi Harga
- **Nomor Laporan:** `009`
- **Nomor Hash Commit:** `d2f36b0`
- **Nama Branch:** `feature/autocomplete-catalog-recommendations`
- **Nama & URL Repo:** `titip-makan` (`git@github.com:mufidhadi/titip-makan.git`)
- **Tech Stack:** FastAPI, Python 3.12, UV, Pydantic v2, SQLAlchemy (Async), SQLite + aiosqlite, Tailwind CSS, Vanilla JavaScript, Playwright, Pytest, Docker Compose, Traefik Reverse Proxy, ZeroTier VPN.

---

## 2. Histori Aksi
1. **Ekstraksi & Analisa Data WhatsApp:**
   - Membaca dan menganalisis 1.000 riwayat pesan di grup **MTN CORE** dan riwayat pesan pribadi dengan **Irzi** melalui WAHA API (`waha.masmuf.cloud`).
   - Menganalisis gambar dan foto menu fisik Babun serta rekap pesanan harian.
   - Mengonsolidasikan katalog harga aktual:
     - **Babun:** 40+ item (Nasi Telor Dobel Rp 13.000, Aneka Olahan Ayam Bakar/Kremes Rp 22.000, Nasi Ikan Nila/Lele/Bawal Rp 22.000, Nasi Goreng Rendang Rp 18.000, Nasi Daging Rp 25.000, Minuman Rp 4.000 - Rp 6.000, Sayuran/Tumis Rp 8.000).
     - **Mie Ayam:** Mie Ayam Polos/Pangsit Rp 15.000, Mie Ayam Bakso Rp 18.000.
     - **Buah Potong:** Semangka, Melon, Nanas, Mangga, Pepaya Rp 5.000.
     - **Kantin:** Otak-otak Goreng Polosan Rp 10.000, Gado-gado Rp 15.000.
2. **Implementasi Master Catalog di Core:**
   - Membuat file `src/titip_makan/core/catalog.py` berisi dictionary `MASTER_CATALOG` dengan data tenant, menu, dan harga yang terverifikasi.
3. **Integrasi Service Layer:**
   - Memperbarui `OrderService.get_suggestions()` di `src/titip_makan/services/order_service.py` agar mengembalikan struktur lengkap: `tenants`, `menus`, dan kamus `prices` (pemetaan nama menu ke integer harga IDR).
4. **Test Driven Development (TDD):**
   - Menambahkan unit test `test_get_suggestions_includes_master_catalog_with_prices` pada `tests/unit/test_order_service.py`.
   - Menguji dan memastikan seluruh tes lulus menggunakan `uv run pytest`.
5. **Penyempurnaan Frontend Auto-Complete:**
   - Memperbarui `src/titip_makan/static/js/app.js`:
     - Fungsi `updateMenuDatalist()`: menampilkan label harga terformat (misal `Rp 13.000`) pada elemen `<option>` di `<datalist id="datalist-menus">`.
     - Fungsi `handleMenuInput()`: mendengarkan event `input` dan `change` pada `#input-menu`. Saat menu yang valid dipilih atau diketik, harga di `#input-price` langsung terisi otomatis.
     - Reverse Tenant Auto-fill: Jika user langsung memilih/mengetik menu saat kolom tenant masih kosong, `#input-tenant` akan otomatis terisi nama tenant terkait.
6. **E2E Playwright Browser Testing:**
   - Menambahkan skenario verifikasi auto-fill menu, harga, dan reverse-tenant di `tests/e2e/test_browser_flow.py`.
   - Menjalankan seluruh test suite Playwright & Pytest via `uv run pytest` (18 passed).
7. **Rebuild & Verifikasi Lokal:**
   - Melakukan build ulang kontainer lokal `docker compose up -d --build`.
   - Verifikasi output JSON dari `http://localhost:8080/api/v1/sessions/suggestions`.
8. **Deployment ke VPS Hostinger via SSH:**
   - Menghubungkan ke server VPS Hostinger (`172.23.127.184` via ZeroTier).
   - Melakukan checkout ke branch `feature/autocomplete-catalog-recommendations` dan pull dari remote repository private.
   - Rebuild kontainer di VPS: `docker compose up -d --build`.
   - Verifikasi langsung endpoint publik `https://titip-irzi.masmuf.cloud/api/v1/sessions/suggestions` dan pengecekan static asset `app.js`.
   - Membaca log uvicorn untuk memastikan tidak ada error runtime.

---

## 3. List Kesulitan, Tantangan, Bug & Solusi
1. **Keterbatasan Event pada HTML5 `<datalist>`:**
   - *Tantangan:* Elemen `<datalist>` native browser tidak menyediakan event `select` seperti elemen dropdown `<select>`.
   - *Solusi:* Menggunakan event listener ganda (`input` dan `change`) pada input text. Setiap karakter yang diketik atau dipilih dari suggestion dicek terhadap kamus `suggestionsData.prices`.
2. **Kenyamanan Pemesanan saat User Langsung Mengetik Menu:**
   - *Tantangan:* Pengguna sering kali langsung mengingat nama makanannya (contoh: "Nasi Telor Dobel") sebelum memikirkan nama warungnya ("Babun").
   - *Solusi:* Diimplementasikan reverse tenant auto-fill di `handleMenuInput()`. Ketika menu terdeteksi di master catalog sementara kolom tenant kosong, sistem langsung mengisikan tenant yang sesuai dan membatasi rekomendasi menu berikutnya sesuai tenant tersebut.

---

## 4. List Pengujian yang Dilakukan & Hasilnya
Semua pengujian dijalankan dengan `uv run pytest` sesuai aturan:

| Kategori Tes | File / Endpoint | Deskripsi Pengujian | Hasil |
| :--- | :--- | :--- | :--- |
| **Unit Test** | `tests/unit/test_order_service.py` | Memastikan `get_suggestions` memuat master catalog Babun, Mie Ayam, Buah Potong, Kantin lengkap dengan harga integer. | **PASSED** ✅ |
| **Unit Test** | `tests/unit/test_session_service.py` | Pengujian lifecycle sesi, cutoff, status, dan default coordinator. | **PASSED** ✅ |
| **Integration Test** | `tests/integration/test_api_flow.py` | Pengujian endpoint REST API dan validasi Pydantic. | **PASSED** ✅ |
| **Integration Test** | `tests/integration/test_e2e_scenarios.py` | Skenario multi-order, grouping pesanan, dan kalkulasi total. | **PASSED** ✅ |
| **Integration Test** | `tests/integration/test_web_routes.py` | Pengujian web route Jinja2 templates. | **PASSED** ✅ |
| **Browser E2E** | `tests/e2e/test_browser_flow.py` | Pengujian mobile view Playwright: interaksi modal, pemilihan nama instan, auto-complete menu, auto-fill harga `13000` & tenant `Babun`, rekap WA, dan coordinator dashboard. | **PASSED** ✅ |
| **Container Test** | `http://localhost:8080/api/v1/sessions/suggestions` | Pengujian curl payload saran lokal pada port Docker. | **PASSED (200 OK)** ✅ |
| **Live Production** | `https://titip-irzi.masmuf.cloud/api/v1/sessions/suggestions` | Pengujian live HTTPS endpoint via Traefik di VPS Hostinger. | **PASSED (200 OK)** ✅ |
| **Static Verification** | `https://titip-irzi.masmuf.cloud/static/js/app.js` | Memastikan event listener `handleMenuInput` aktif di bundle JavaScript production. | **PASSED** ✅ |

**Ringkasan Hasil Pytest:**
```
============================= 18 passed in 14.22s ==============================
```

---

## 5. Lesson Learned
- Ekstraksi langsung dari interaksi percakapan riil (grup WA MTN CORE & chat Irzi) menghasilkan katalog yang 100% kontekstual dan langsung siap pakai tanpa perlu input data manual berulang oleh koordinator.
- Kombinasi `<datalist>` native dengan JavaScript helper memberikan pengalaman interaktif auto-complete yang sangat cepat di perangkat seluler (iPhone/Android) tanpa ketergantungan pada pustaka UI pihak ketiga yang berat.
