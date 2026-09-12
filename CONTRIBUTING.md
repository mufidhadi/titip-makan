# Panduan Kontribusi Titip Makan MTN CORE 🍜

Terima kasih atas ketertarikan Anda untuk berkontribusi pada **Titip Makan MTN CORE**! Dokumen ini memuat standar, alur kerja, dan pedoman pengembangan yang wajib diikuti oleh setiap kontributor untuk menjaga kualitas kode, reliabilitas, dan keamanan aplikasi.

---

## 🧭 Prinsip Utama Pengembangan

Setiap kode yang masuk ke repositori ini harus memenuhi standar berikut:

1. **Eksklusif Menggunakan `uv` (No `pip` & No `python <script>.py`):**
   - Repositori ini sepenuhnya dikelola menggunakan runtime dan package manager modern [`uv`](https://github.com/astral-sh/uv).
   - **DILARANG** menggunakan perintah `pip`, `pip install`, `pip-tools`, atau menjalankan script python secara manual dengan `python <file>.py`.
   - Selalu gunakan `uv`:
     - Sinkronisasi dependensi: `uv sync`
     - Menambah dependensi: `uv add <package>`
     - Menghapus dependensi: `uv remove <package>`
     - Menjalankan script/perintah: `uv run <command>` (contoh: `uv run pytest`, `uv run uvicorn ...`)
2. **Strict Test-Driven Development (TDD):**
   - **DILARANG** mengubah kode atau menambah fitur tanpa pengujian (*no test = no merge*).
   - Terapkan siklus *Red-Green-Refactor*: buat/perbarui unit test di folder `tests/` terlebih dahulu sebelum mengimplementasikan perubahan kode.
   - Semua test wajib dijalankan dengan `pytest` melalui:
     ```bash
     uv run pytest
     ```
3. **Arsitektur Modular & Prinsip SOLID:**
   - Struktur kode berlandaskan pemisahan tanggung jawab yang bersih (*Clean Architecture*):
     - `src/core/`: Konfigurasi global dan database engine.
     - `src/models/`: Definisi tabel basis data (SQLAlchemy models).
     - `src/schemas/`: Validasi payload request dan response DTO (Pydantic schemas).
     - `src/repositories/`: Operasi query dan persistensi data (Repository Pattern).
     - `src/services/`: Logika bisnis murni (Service Layer).
     - `src/api/`: Endpoint routing HTTP FastAPI.
   - Hindari penulisan kode panjang dalam satu file; utamakan modularitas dan *single-responsibility principle*.
4. **Disiplin Branching (No Direct Push to Protected Branches):**
   - **DILARANG KERAS** melakukan push langsung ke branch `main`, `master`, `development`, atau `release/*`.
   - Semua perubahan wajib dibuat melalui branch terpisah dan diajukan lewat **Pull Request (PR)**.

---

## 🛠️ Persyaratan Lingkungan (Prerequisites)

Pastikan perangkat Anda telah terpasang:
- **Git** (versi terbaru)
- **Python 3.12+**
- **uv** (Astral):
  - macOS / Linux:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
    atau via Homebrew: `brew install uv`
  - Windows:
    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```
- **Docker & Docker Compose** (opsional, untuk pengujian kontainerisasi lokal)

---

## 🚀 Langkah Memulai Pengembangan (Local Setup)

Ikuti langkah-langkah berikut untuk mengatur repositori lokal:

### 1. Fork & Clone Repositori

Jika Anda kontributor eksternal, lakukan **Fork** repositori ini ke akun GitHub Anda, lalu clone:

```bash
git clone https://github.com/<username-anda>/titip-makan.git
cd titip-makan
```

Tambahkan upstream repository:

```bash
git remote add upstream https://github.com/mufidhadi/titip-makan.git
```

### 2. Setup Environment Variables

Salin file template `.env.example` menjadi `.env`:

```bash
cp .env.example .env
```

Sesuaikan nilai variabel jika diperlukan (konfigurasi default sudah siap pakai untuk *local development* menggunakan SQLite).

### 3. Install Dependensi dengan `uv`

Jalankan perintah berikut untuk menginstal seluruh dependensi development secara deterministik:

```bash
uv sync
```

### 4. Jalankan Pengujian (Testing)

Sebelum mulai menulis kode, pastikan seluruh test yang ada berjalan sukses:

```bash
uv run pytest -v
```

### 5. Jalankan Server Lokal

Jalankan FastAPI dengan *auto-reload* aktif:

```bash
uv run uvicorn titip_makan.main:app --host 0.0.0.0 --port 8080 --reload
```

Aplikasi dapat diakses pada browser di:
- **Pemesanan Anggota:** `http://localhost:8080/`
- **Dashboard Koordinator:** `http://localhost:8080/coordinator` (PIN Default: `1234`)
- **Dokumentasi API Swagger:** `http://localhost:8080/docs`

---

## 🌿 Alur Kerja Git & Standar Pull Request (PR)

### 1. Buat Branch Baru dari `main`

Pastikan branch `main` lokal Anda sinkron dengan `upstream/main`:

```bash
git checkout main
git pull upstream main
git checkout -b <tipe>/<deskripsi-singkat>
```

Format penamaan branch yang diizinkan:
- `feat/<nama-fitur>`: Penambahan fitur baru
- `fix/<nama-bug>`: Perbaikan bug atau galat
- `refactor/<nama-komponen>`: Refaktor kode tanpa mengubah fungsionalitas
- `test/<nama-pengujian>`: Penambahan atau perbaikan pengujian
- `docs/<nama-dokumen>`: Pembaruan atau penambahan dokumentasi

Contoh:
```bash
git checkout -b feat/tambah-filter-vendor
```

### 2. Terapkan Standar Commit Message (Conventional Commits)

Tuliskan pesan commit yang deskriptif dan terstruktur:

- `feat: tambah filter pencarian katalog berdasarkan vendor`
- `fix: tangani nilai nol pada kalkulasi total tagihan koordinator`
- `test: tambah unit test untuk validasi batas waktu cut-off`
- `refactor: pisahkan logika parsing format wa ke service terpisah`

### 3. Checklist Sebelum Mengajukan Pull Request (PR)

Sebelum melakukan `git push` dan membuka Pull Request, verifikasi hal-hal berikut:

- [ ] Seluruh unit test berjalan dan lulus 100%: `uv run pytest tests/unit tests/integration`
- [ ] Lint bersih: `uv run ruff check .`
- [ ] CI (job `test`) **hijau** — wajib sebelum merge (lihat bagian Trunk-Based)
- [ ] Branch berumur pendek (idealnya < 1 hari kerja); kalau lebih, pecah jadi PR kecil
- [ ] Kode baru memiliki unit test yang memadai
- [ ] Arsitektur kode mematuhi prinsip SOLID dan pola modular
- [ ] Tidak ada file sensitif/kredensial yang ter-commit (file `.env` atau API keys)
- [ ] Tidak ada sisa kode debug atau `print()` yang tidak relevan

### 4. Buat Pull Request

1. Push branch Anda ke remote fork:
   ```bash
   git push origin <nama-branch>
   ```
2. Buka GitHub dan klik tombol **Compare & pull request**.
3. Berikan judul yang jelas serta deskripsi ringkas mengenai:
   - Masalah atau kebutuhan yang diselesaikan.
   - Perubahan apa saja yang dilakukan.
   - Bukti pengujian (`pytest` output).
4. Tunggu review dari maintainer repository.

---

## 🌳 Trunk-Based Development (aturan wajib)

Repo ini memakai **trunk-based development**: `main` adalah **trunk**, dan trunk
harus **selalu dalam keadaan siap deploy**.

1. **Branch hidup pendek** — idealnya < 1 hari kerja. PR kecil dan sering, bukan satu PR raksasa yang menggantung berhari-hari.
2. Selalu branch **dari `main` terbaru**; sinkronkan (`git pull --rebase upstream main`) sebelum merge.
3. **Merge squash saja** → riwayat `main` linear. Branch otomatis dihapus setelah merge.
4. **CI wajib hijau** sebelum merge (job `test`: `ruff check` + unit + integration).
5. **Tidak ada push langsung ke `main`** — semua lewat Pull Request, dan hanya maintainer yang boleh merge.
6. Pekerjaan yang belum selesai tapi harus masuk: pakai **feature flag / default mati**, jangan branch panjang.
7. **Hotfix** ikut aturan yang sama: branch pendek → PR → CI hijau → merge.
8. Test **E2E browser tidak dijalankan di CI utama** (berat: butuh Playwright + server hidup). Jalankan lokal sebelum membuka PR yang menyentuh UI, atau tunggu workflow nightly.

**Konsekuensi:** setiap merge ke `main` = siap deploy. Jangan merge PR yang belum kamu yakini jalan di produksi.

---

## 🛡️ Keamanan & Kredensial

- **Jangan pernah melakukan commit terhadap API key, password, token, atau file `.env` ke dalam repositori.**
- Jika Anda menemukan celah keamanan, laporkan langsung ke pemilik repositori secara privat sebelum mempublikasikan issue publik.

Selamat berkontribusi! 🚀
