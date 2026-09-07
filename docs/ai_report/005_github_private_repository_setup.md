# Laporan Pengerjaan: Setup Private Repository GitHub & Sinkronisasi Cloud

## 1. Informasi Tugas
* **Nama Tugas:** Pengecekan Eksistensi Cloud Repo, Pembuatan Private Repository di GitHub, Konfigurasi Remote SSH, dan Push Seluruh Branch
* **Tanggal Pengerjaan:** 07 September 2026
* **Nama Branch:** `feature/seamless-order-flow` (dan `main`)
* **Nomor Hash Commit:** `491dcb8`
* **Nama dan URL Repo:**
  * **Nama Repo:** `mufidhadi/titip-makan`
  * **Web URL:** `https://github.com/mufidhadi/titip-makan`
  * **SSH Remote URL:** `git@github.com:mufidhadi/titip-makan.git`
  * **Status Visibilitas:** `Private`

---

## 2. Tech Stack
* **VCS & Cloud Hosting:** Git & GitHub (Private Repository via SSH)
* **CLI Tooling:** GitHub CLI (`gh`) 2.x
* **Security & Auth:** SSH Public Key Authentication (ZeroTier ecosystem ready)
* **Application Stack:** FastAPI, SQLAlchemy Async, Python 3.12 (`uv`), Docker Compose, Playwright

---

## 3. Histori Aksi
1. **Verifikasi Status Awal Repositori di Cloud:**
   * Menjalankan perintah `git remote -v` untuk memeriksa apakah sudah ada remote URL yang terdaftar. Hasilnya kosong (belum ada remote terpasang).
   * Menjalankan `gh repo view mufidhadi/titip-makan` untuk memastikan apakah repository sudah ada sebelumnya di akun GitHub `mufidhadi`.
   * Hasil membuktikan bahwa repository belum ada di cloud:
     `GraphQL: Could not resolve to a Repository with the name 'mufidhadi/titip-makan'.`
2. **Pemeriksaan Keamanan File Sensitif (.gitignore):**
   * Memeriksa konfigurasi `.gitignore` untuk memastikan kredensial rahasia (`.env`), database SQLite lokal (`data/`, `*.db`), dan virtual environment (`.venv/`) tidak ikut terlacak oleh Git.
   * Memastikan hanya template konfigurasi non-sensitif (`.env.example`) yang terlacak.
3. **Pembuatan Private Repository GitHub via SSH:**
   * Menggunakan GitHub CLI dengan protokol SSH (`gh repo create`):
     ```bash
     gh repo create titip-makan --private --source=. --remote=origin --description="Platform Titip Makan MTN CORE (Internal Order Coordination)"
     ```
   * Memverifikasi visibilitas repository disetel ke `Private` (`isPrivate: true`) dan URL remote terhubung ke `git@github.com:mufidhadi/titip-makan.git`.
4. **Pembentukan Default Branch & Sinkronisasi Branch ke Cloud:**
   * Membuat branch utama `main` dari commit stabil terakhir.
   * Mendorong (`push`) branch `main` ke remote `origin` sebagai default branch:
     ```bash
     git push -u origin main
     ```
   * Mendorong seluruh histori branch fitur dan perbaikan ke GitHub:
     ```bash
     git push --all origin
     ```
   * Seluruh branch berhasil tersinkronisasi ke GitHub:
     * `main` (default)
     * `feature/seamless-order-flow`
     * `fix/e2e-bugs-and-improvements`
     * `feature/custom-tenant-and-variant`
     * `feature/titip-makan-platform`

---

## 4. List Kesulitan, Tantangan, Bug dan Solusi

| No | Masalah / Tantangan | Penyebab | Solusi |
|---|---|---|---|
| 1 | Memastikan protokol Git menggunakan SSH, bukan HTTPS | Sesuai aturan kerja mas mufid, seluruh interaksi remote antardevice dan server harus menggunakan SSH key yang sudah terdaftar. | Memverifikasi `gh auth status` dikonfigurasi dengan `Git operations protocol: ssh`, dan memastikan remote URL menggunakan skema `git@github.com:...`. |
| 2 | Menjaga database lokal dan file `.env` agar tidak bocor ke cloud | Folder `data/` dan file `.env` berisi database runtime aktif. | Melakukan audit git tracking dengan `git ls-files` sebelum inisialisasi remote untuk memverifikasi hanya `.env.example` yang dikirim ke remote. |

---

## 5. Bukti Data dan Verifikasi Nyata

### Output Pengecekan Repository GitHub:
```json
{
  "defaultBranchRef": {
    "name": "main"
  },
  "isPrivate": true,
  "sshUrl": "git@github.com:mufidhadi/titip-makan.git",
  "url": "https://github.com/mufidhadi/titip-makan"
}
```

### Output Status Git Remote:
```text
origin	git@github.com:mufidhadi/titip-makan.git (fetch)
origin	git@github.com:mufidhadi/titip-makan.git (push)
```

### Output Push Seluruh Branch:
```text
To github.com:mufidhadi/titip-makan.git
 * [new branch]      main -> main
 * [new branch]      feature/custom-tenant-and-variant -> feature/custom-tenant-and-variant
 * [new branch]      feature/seamless-order-flow -> feature/seamless-order-flow
 * [new branch]      feature/titip-makan-platform -> feature/titip-makan-platform
 * [new branch]      fix/e2e-bugs-and-improvements -> fix/e2e-bugs-and-improvements
```

---

## 6. Lesson Learned
* Selalu lakukan validasi eksistensi remote dan audit file terlacak (`git ls-files`) sebelum mempublikasikan repositori lokal ke cloud, guna menjamin tidak ada kebocoran file lingkungan (*environment secrets*) atau database produksi.
* Konfigurasi SSH yang konsisten di semua remote mempermudah proses automasi deployment ke home server maupun VPS melalui terminal secara aman tanpa kendala prompt token berkala.
