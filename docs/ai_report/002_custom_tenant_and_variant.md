# Laporan Pengerjaan: Input Kustom Tenant, Menu, dan Varian

## 1. Informasi Tugas
* **Nama Tugas:** Penambahan Input Fleksibel untuk Tenant (Vendor), Menu, dan Varian Kustom di Luar Daftar
* **Tanggal Pengerjaan:** 07 September 2026
* **Nama Branch:** `feature/custom-tenant-and-variant`
* **Nomor Hash Commit:** `9dee783240536463c8a02e2bd4d61502a6863049`
* **Nama dan URL Repo:** Lokal (`/Users/anb-0826014/project/mufid/titip-makan`)

---

## 2. Tech Stack
* **Runtime & Package Management:** Python 3.12 via `uv` (Astral)
* **Backend Framework:** FastAPI 0.141+ & SQLAlchemy Async (`aiosqlite`)
* **Testing:** `pytest` & `pytest-asyncio` (TDD - Test Driven Development)
* **Containerization:** Docker & Docker Compose
* **Frontend:** HTML5, Tailwind CSS, Vanilla JavaScript (Progressive Disclosure UI Pattern)

---

## 3. Histori Aksi
1. **Analisis Kebutuhan & Riset UI/UX:**
   * Melakukan riset best practice untuk pattern *"Select dropdown with custom other option"* (Progressive Disclosure).
   * Menentukan UX yang tidak membingungkan: Opsi *"➕ Tambah Tenant / Vendor Lain..."* dan *"➕ Varian Kustom Lainnya"* akan memunculkan input teks tambahan di bawahnya secara kontekstual dan langsung mengarahkan fokus kursor ke input tersebut.
2. **Membuat Branch Git Baru:**
   * Checkout branch baru: `feature/custom-tenant-and-variant` dari `feature/titip-makan-platform`.
3. **Penerapan TDD (Test-Driven Development):**
   * Menulis unit test baru `test_custom_tenant_and_variant_order` di `tests/unit/test_order_service.py` untuk memverifikasi pemesanan dengan tenant, menu, dan varian yang sama sekali di luar daftar standar.
   * Menemukan perlunya penandaan vendor pada ringkasan WhatsApp saat ada pesanan multi-vendor/kustom.
   * Memperbarui `OrderService.get_session_summary()` agar format WhatsApp menyertakan label `[Vendor]` di setiap item belanjaan dan daftar pemesan.
   * Menjalankan `uv run pytest` dan memverifikasi seluruh 10 test lulus.
4. **Implementasi Frontend (`index.html` & `app.js`):**
   * Menambahkan elemen input dinamis: `#input-custom-vendor`, `#input-custom-menu`, `#input-custom-price`, dan `#input-custom-variant`.
   * Memperbarui logika JavaScript di `app.js` untuk mendeteksi pilihan `__custom__` pada vendor, menu, dan varian.
   * Mengintegrasikan auto-calculation estimasi harga manual dan validasi form sebelum dikirim ke API.
5. **Rebuild Container & Verifikasi Nyata:**
   * Menjalankan `docker compose up -d --build` untuk menerapkan perubahan ke container `titip_makan_app`.
   * Menguji pemesanan nyata via `curl` ke container dengan:
     * Tenant kustom: `Kantin Mbok Darmi`
     * Menu kustom: `Nasi Rawon`
     * Varian kustom: `Daging Dobel + Telur Asin`
     * Harga kustom: `Rp 30.000`
   * Memverifikasi data tersimpan dengan benar dan muncul di ringkasan belanjaan koordinator.

---

## 4. List Kesulitan, Tantangan, Bug dan Solusi

| No | Masalah / Bug | Penyebab | Solusi |
|---|---|---|---|
| 1 | Label vendor tidak muncul di rekap WhatsApp | Format teks rekap awal mengasumsikan sesi hanya satu vendor sehingga nama vendor tidak dicetak pada baris belanjaan. | Menambahkan prefix `[item.vendor]` pada setiap baris item belanjaan dan daftar pemesan di `OrderService`. |
| 2 | Syntax error `}` ekstra di `app.js` | Kesalahan penutupan blok event listener saat refactoring handler submit. | Memeriksa baris dengan `view_file` dan membersihkan kurung kurawal ganda. |

---

## 5. List Test yang Dilakukan dan Hasilnya

Dijalankan menggunakan command `uv run pytest`:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.14, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/anb-0826014/project/mufid/titip-makan
configfile: pyproject.toml
testpaths: tests
plugins: asyncio-1.4.0, anyio-4.15.1
collected 10 items

tests/integration/test_api_flow.py .                                     [ 10%]
tests/integration/test_web_routes.py .                                   [ 20%]
tests/unit/test_order_service.py .....                                   [ 70%]
tests/unit/test_session_service.py ...                                   [100%]

============================== 10 passed in 0.22s ==============================
```

---

## 6. Verifikasi Eksekusi Nyata di Docker

Hasil pengujian pesanan custom melalui endpoint Docker yang sedang berjalan:
```json
{
  "id": 4,
  "session_id": 1,
  "user_name": "Adrian",
  "vendor": "Kantin Mbok Darmi",
  "item_name": "Nasi Rawon",
  "variant": "Daging Dobel + Telur Asin",
  "notes": "kuah pisah ya",
  "price": 30000,
  "is_paid": false
}
```

Format Rekap WhatsApp yang dihasilkan:
```text
📋 *Rekap Titip Makan: Titip Makan MTN CORE 7/09/2026*
👤 Koordinator: Zi
📊 Total Pesanan: 4 porsi
💰 Total Biaya: Rp 82,000 (Lunas: 0, Belum: 4)

🛒 *Ringkasan Belanjaan:*
• 1x [Babun] Babun Nasi Ayam (Lada Hitam) - Rp 22,000
• 1x [Kantin Mbok Darmi] Nasi Rawon (Daging Dobel + Telur Asin) - Rp 30,000
   ↳ Adrian: kuah pisah ya
• 2x [Mie Ayam] Mie Ayam (Pangsit Rebus) - Rp 30,000
   ↳ Amal: jangan pakai sayur

📝 *Daftar Pemesan:*
1. Amal - [Mie Ayam] Mie Ayam (Pangsit Rebus) - Rp 15,000 [Catatan: jangan pakai sayur] (⏳ Belum)
2. Mufid - [Mie Ayam] Mie Ayam (Pangsit Rebus) - Rp 15,000 (⏳ Belum)
3. Shazi - [Babun] Babun Nasi Ayam (Lada Hitam) - Rp 22,000 (⏳ Belum)
4. Adrian - [Kantin Mbok Darmi] Nasi Rawon (Daging Dobel + Telur Asin) - Rp 30,000 [Catatan: kuah pisah ya] (⏳ Belum)

💳 *Info Pembayaran:*
BCA 1234567 a.n. Zi
```

---

## 7. Lesson Learned
* Penerapan pola *progressive disclosure* memberikan fleksibilitas tanpa mengorbankan kecepatan pengisian formulir standar bagi pengguna yang memilih menu umum.
* TDD langsung mengungkap kebutuhan bisnis tambahan (mis. penambahan prefix nama vendor pada rekapitulasi) sebelum kode masuk ke produksi.
