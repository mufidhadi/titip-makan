# Titip Makan MTN CORE 🍜

Platform internal pemesanan titip makan bersama untuk tim MTN CORE. Dirancang untuk mengatasi masalah *race condition* / pesan saling tertimpa di grup WhatsApp, menyederhanakan pemilihan menu, serta mengotomatisasi rekap belanjaan dan pelacakan status pembayaran koordinator.

---

## 🌟 Fitur Utama

1. **Atomic Ordering (Anti-Ketimpa):**
   - Setiap anggota tim melakukan submit pesanan masing-masing secara independen via web-form.
   - Tidak ada lagi konflik suntingan atau list WhatsApp yang terpotong.
2. **Katalog & Varian Menu:**
   - Mendukung multi-vendor (Mie Ayam, Babun, Nasi Goreng, Dimsum).
   - Pilihan varian terstruktur (Pangsit Rebus vs Goreng, Lada Hitam vs Kremes vs Telor Dobel).
3. **Rekapitulasi Otomatis (*Order Aggregator*):**
   - Dashboard koordinator mengelompokkan jumlah belanjaan per varian secara otomatis.
   - Mengurangi beban perhitungan manual sebelum membeli makanan.
4. **Pelacakan Status Pembayaran:**
   - Tombol toggle untuk menandai pesanan yang sudah lunas atau belum.
   - Rincian total biaya pesanan per individu dan total tagihan keseluruhan.
5. **Export Format Rekap WhatsApp:**
   - Tombol satu-klik untuk menyalin rekap rapi berformat markdown WhatsApp ke clipboard, siap di-paste ke grup MTN CORE.
6. **Batas Waktu Otomatis (*Cut-off Timer*):**
   - Sesi otomatis terkunci saat jam batas pemesanan habis.

---

## 🛠️ Tech Stack

- **Runtime & Package Manager:** Python 3.12+ via [`uv`](https://github.com/astral-sh/uv) (No pip)
- **Backend Framework:** FastAPI (Clean & Modular Architecture: Core, Models, Schemas, Repositories, Services, API)
- **Database:** SQLite dengan Async SQLAlchemy (`aiosqlite`)
- **Testing:** `pytest`, `pytest-asyncio`, `httpx` (Strict TDD)
- **Containerization:** Docker & Docker Compose (Multi-stage build dengan official Astral `uv`)
- **Frontend:** Responsive HTML5, Tailwind CSS, Vanilla JavaScript

---

## 🚀 Menjalankan Aplikasi

### Opsi 1: Docker Compose (Disarankan)

Pastikan Docker sudah berjalan, lalu jalankan:

```bash
docker compose up -d --build
```

Akses aplikasi di browser:
- **Pemesanan Anggota:** `http://localhost:8080/`
- **Dashboard Koordinator:** `http://localhost:8080/coordinator`
- **Health Check:** `http://localhost:8080/api/health`

### Opsi 2: Lokal dengan `uv`

```bash
# Sync dependensi
uv sync

# Menjalankan test
uv run pytest

# Menjalankan server aplikasi
uv run uvicorn titip_makan.main:app --host 0.0.0.0 --port 8080 --reload
```

---

## 🧪 Testing

Seluruh fungsi dan alur kerja diuji menggunakan `pytest` dengan prinsip Test-Driven Development (TDD):

```bash
uv run pytest -v
```

---

## 🤝 Kontribusi

Tertarik untuk berkontribusi? Silakan baca panduan lengkap pengembangan, standar kode (uv & TDD), serta alur kerja Pull Request pada [CONTRIBUTING.md](CONTRIBUTING.md).
