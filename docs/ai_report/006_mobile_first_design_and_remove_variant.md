# Laporan Pengerjaan: Desain Tampilan Mobile-First & Penghapusan Input Varian

## 1. Informasi Tugas
* **Nama Tugas:** Penerapan Desain Antarmuka Mobile-First (Sticky Bottom Bar, Touch Cards, Bottom Sheet Modal) dan Penghapusan Input Varian
* **Tanggal Pengerjaan:** 07 September 2026
* **Nama Branch:** `feature/mobile-first-design`
* **Nomor Hash Commit:** `32a7cce5f12acf9a27fe468d07eb082f73e68301`
* **Nama dan URL Repo:**
  * **Nama Repo:** `mufidhadi/titip-makan`
  * **Web URL:** `https://github.com/mufidhadi/titip-makan`
  * **SSH Remote URL:** `git@github.com:mufidhadi/titip-makan.git` (Private)

---

## 2. Tech Stack
* **Runtime & Package Management:** Python 3.12 via `uv` (Astral)
* **Backend Framework:** FastAPI 0.141+ & SQLAlchemy Async (`aiosqlite`)
* **Testing:**
  * Unit & Integrasi: `pytest`, `pytest-asyncio`, `httpx`
  * Mobile Emulation E2E Testing: `playwright` (Chromium viewport 390x844 with touch enabled)
* **Containerization:** Docker & Docker Compose
* **Frontend:** HTML5, Tailwind CSS (Mobile-first responsive utilities, Sticky Bottom Navigation, Bottom Sheet Modal), Vanilla JavaScript

---

## 3. Histori Aksi
1. **Analisis Kebutuhan & Riset Mobile-First UX:**
   * Melakukan riset best practice aplikasi pemesanan makanan berbasis web untuk viewport layar smartphone (375px - 430px).
   * Mengidentifikasi bahwa input "Varian" seringkali redundan dengan nama menu atau catatan khusus, dan menambah beban kognitif pengguna saat memesan cepat dari ponsel.
   * Merancang elemen antarmuka ramah jempol (*thumb-friendly*):
     * **Sticky Bottom Action Bar:** Tombol mengambang tetap di bagian bawah layar ponsel untuk akses instan ke form pemesanan tanpa perlu scroll.
     * **Card List View untuk Mobile:** Menggantikan tabel horizontal yang terpotong di ponsel dengan kartu pesanan vertikal yang terstruktur rapi.
     * **Bottom Sheet Modal:** Modal pemesanan meluncur dari bawah layar ponsel seperti aplikasi native mobile modern, dilengkapi *drag handle*.
2. **Pembuatan Branch Baru:**
   * Membuat branch baru `feature/mobile-first-design` dari `feature/seamless-order-flow`.
3. **Penerapan TDD (Test-Driven Development):**
   * Menyesuaikan unit test di `tests/unit/test_order_service.py` (`test_order_without_variant_and_clean_aggregation`) untuk memastikan agregasi pesanan belanjaan berbasis `(vendor, item_name)` berjalan sempurna tanpa memerlukan varian.
   * Menulis browser E2E test otomatis Playwright dengan emulasi layar mobile (`viewport={"width": 390, "height": 844}`, `is_mobile=True`, `has_touch=True`) di `tests/e2e/test_browser_flow.py`.
4. **Penghapusan Total Input Varian di Seluruh Lapisan:**
   * Menghapus input `#input-variant` dan datalist `#datalist-variants` dari `index.html`.
   * Menghapus referensi varian dari `app.js` dan `coordinator.js`.
   * Menyederhanakan logika agregasi belanjaan dan format pesan WhatsApp di `OrderService`:
     `• {item.quantity}x [{item.vendor}] {item.item_name}`
     `{idx}. {o.user_name} - [{o.vendor}] {o.item_name}{price_str}{note_str} ({status_icon})`
5. **Implementasi Desain Mobile-First di Frontend:**
   * **`index.html`**:
     * Menambahkan kartu pesanan mobile (`#orders-cards-container`, kelas `block md:hidden`) dengan visual hirarki: nomor antrean, nama pemesan, badge tenant, status lunas, menu pesanan, catatan, harga, serta tombol aksi sentuh (`📲 Notif WA` dan `✕ Batal`).
     * Mempertahankan tampilan tabel desktop (`#orders-table-card`, kelas `hidden md:block`) untuk monitor lebar.
     * Menambahkan Sticky Bottom Action Bar (`#mobile-bottom-bar`, kelas `sm:hidden`) dengan ringkasan antrean dan tombol hijau `[➕ Tambah Pesanan]` berukuran besar.
     * Mengatur padding bawah kontainer (`pb-24 sm:pb-8`) agar konten tidak tertutup fixed bottom bar.
     * Menyesuaikan modal pemesanan menjadi format Bottom Sheet pada ponsel (`rounded-t-3xl sm:rounded-2xl`).
     * Menggunakan ukuran teks minimum 16px (`text-base sm:text-sm`) pada input formulir ponsel untuk mencegah auto-zoom browser iOS/Android.
   * **`coordinator.html` & `coordinator.js`**:
     * Menghapus kolom varian dan menyelaraskan ringkasan belanjaan menjadi per-menu.
6. **Eksekusi Pengujian & Verifikasi Visual:**
   * Menjalankan seluruh test suite dengan `uv run pytest` — seluruh 16 test berhasil lulus 100%.
   * Membangun ulang kontainer Docker dan memverifikasi container berjalan normal.
   * Menghasilkan screenshot hasil render mobile nyata menggunakan Playwright.

---

## 4. List Kesulitan, Tantangan, Bug dan Solusi

| No | Masalah / Tantangan | Penyebab | Solusi |
|---|---|---|---|
| 1 | Beban input berlebih (*form friction*) akibat adanya kolom varian | Pengguna sering bingung membedakan antara menu, varian, dan catatan (misal: "Mie Ayam Pangsit Rebus" vs menu "Mie Ayam" + varian "Pangsit Rebus"). | Menghilangkan field varian sepenuhnya. Pengguna kini hanya perlu mengisi Tenant, Menu, dan Catatan (jika ada hal khusus). Form menjadi sangat ringkas dan cepat diisi dari ponsel. |
| 2 | Tabel data desktop terpotong dan sulit dibaca di layar HP | Tabel HTML standar memerlukan horizontal scroll pada layar selebar 390px, membuat teks status dan tombol aksi tersembunyi di sisi kanan. | Menerapkan pola responsif ganda: kartu mandiri (*card view*) khusus mobile (`block md:hidden`) dan tabel tabular untuk layar desktop (`hidden md:block`). |
| 3 | Tombol "Tambah Pesanan" di desktop tergulir keluar pandangan saat daftar pesanan panjang | Saat pesanan tim kantor sudah terkumpul 10+ porsi, pengguna ponsel harus scroll jauh ke atas/bawah untuk mencari tombol pesan. | Menyediakan sticky bottom navigation bar yang selalu mengambang di bawah layar ponsel, menjaga tombol aksi utama selalu dalam jangkauan satu ketukan jempol. |
| 4 | Assertion teks huruf kapital pada Playwright Playback | Elemen badge tenant di styling dengan utilitas Tailwind `uppercase`, sehingga `inner_text()` Playwright mengekstrak teks dalam huruf besar semua (`SOTO BETAWI BANG MAMAT`). | Menyesuaikan assertion pengujian Playwright agar menggunakan pencocokan *case-insensitive* `.upper()`. |

---

## 5. List Test yang Dilakukan dan Hasil dari Test

Pengujian dijalankan dengan:
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
collected 16 items

tests/e2e/test_browser_flow.py .                                         [  6%]
tests/integration/test_api_flow.py ..                                    [ 18%]
tests/integration/test_e2e_scenarios.py .                                [ 25%]
tests/integration/test_web_routes.py .                                   [ 31%]
tests/unit/test_order_service.py ........                                [ 81%]
tests/unit/test_session_service.py ...                                   [100%]

============================= 16 passed in 14.81s ==============================
```

### Rincian Cakupan Test:
1. `tests/e2e/test_browser_flow.py`: Pengujian browser headless Playwright dengan konfigurasi viewport smartphone nyata (390x844 touch device):
   - Memvalidasi kemunculan sticky bottom action bar `#mobile-bottom-bar`.
   - Mengklik tombol aksi jempol untuk memunculkan bottom sheet modal.
   - Memastikan tidak ada lagi input `#input-variant` di DOM.
   - Memasukkan pesanan tenant, menu, catatan, dan harga opsional.
   - Memvalidasi kartu pesanan mobile `#orders-cards-container` ter-render sempurna lengkap dengan badge tenant, nama pemesan, harga, dan tombol aksi.
   - Memvalidasi pembaharuan harga oleh koordinator dan penutupan sesi.
2. `tests/unit/test_order_service.py`: 8 unit test memverifikasi agregasi belanjaan bersih tanpa varian, kalkulasi rupiah, cutoff, dan saran autocomplete.
3. `tests/integration/test_api_flow.py` & `test_e2e_scenarios.py`: 3 integrasi test untuk lifecycle API, isolated database sessions, dan web routing.

---

## 6. Verifikasi Tangkapan Layar Otomatis (Screenshots)
File tangkapan layar emulasi mobile smartphone (iPhone 390x844) tersimpan di:
* `docs/screenshots/mobile_orders_view.png`: Menampilkan kartu antrean pesanan mobile yang terstruktur rapi, badge tenant, status bayar, format rupiah, dan sticky bottom bar yang ramah jempol.
* `docs/screenshots/mobile_coordinator_view.png`: Menampilkan antarmuka koordinator yang responsif di ponsel dengan metrik ringkas dan toast non-blocking.
* `docs/screenshots/mobile_home_closed.png`: Menampilkan status sesi ditutup di layar ponsel dengan tombol yang dinonaktifkan secara tepat.

---

## 7. Status Kontainer Docker
Container aplikasi aktif dan sehat (*healthy*) pada port `8080`:
```text
NAME              IMAGE             COMMAND                  SERVICE   CREATED          STATUS                    PORTS
titip_makan_app   titip-makan-app   "uvicorn titip_makan…"   app       4 minutes ago    Up 4 minutes (healthy)   0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp
```

---

## 8. Lesson Learned
* **Penghapusan Redundansi Varian:** Pada kasus titip makan kantor, pengguna jarang membutuhkan dropdown varian yang kaku; variasi pesanan (seperti level pedas, kuah pisah, atau jenis mie) jauh lebih alami dituangkan langsung di nama menu atau field catatan.
* **Dual-View Rendering:** Mengombinasikan kartu mobile (`block md:hidden`) dan tabel desktop (`hidden md:block`) memberikan pengalaman pengguna terbaik di kedua dunia: efisien dan padat di laptop koordinator, namun lapang dan mudah disentuh di smartphone anggota.
