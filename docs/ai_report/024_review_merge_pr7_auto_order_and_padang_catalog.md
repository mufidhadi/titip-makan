# 024 — Review, Merge PR #7 (Auto Pesan Random & Katalog Padang), dan Deploy VPS

**Tanggal:** 15 Oktober 2026  
**Status:** SELESAI  
**Pelaksana:** Antigravity untuk mas mufid  

---

## 1. Identitas Tugas & Repository

- **Nama Tugas:** Review, Approval, Merge PR #7, dan Deployment ke VPS Produksi Titip Makan
- **Repository:** `mufidhadi/titip-makan` (https://github.com/mufidhadi/titip-makan)
- **Pull Request:** [PR #7 — feat: weekday auto random order per user + Padang menu catalog](https://github.com/mufidhadi/titip-makan/pull/7)
- **Kontributor PR:** Rayhan Aswiansyah (`syahrayhan:feat/weekday-auto-random-order`)
- **Target Branch:** `main`
- **Commit PR:** `2a1d0247c4b36efac0a41e691288888331221453`
- **Squash Merge Commit (main):** `fe59813083cf4c3bbf44018809ff44f2ef1572df`
- **Branch Laporan:** `docs/ai-report-024-review-merge-pr7`
- **Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (Async SQLite / aiosqlite), Uvicorn, UV, Pytest, Playwright, Tailwind CSS, Docker Compose, Traefik Reverse Proxy, ZeroTier VPN (172.23.127.184).

---

## 2. Histori Aksi

1. **Penerimaan & Analisis Request:**
   - Membaca pesan Rayhan dari MS Teams yang diteruskan oleh mas mufid.
   - Menginspeksi isi PR #7: penambahan fitur *Auto Pesan Random* per-user tiap Senin–Jumat jam 10:00 WIB, tabel baru `weekday_auto_orders`, endpoint `/api/v1/auto-order`, komponen UI di halaman utama, dan penambahan katalog 32 menu Padang Salero Datuak Mamas.
2. **Pengambilan Branch & Pengujian Lokal:**
   - Fetch PR ke local branch review: `git fetch origin pull/7/head:review/pr-7-auto-order-padang`.
   - Menjalankan linter: `uv run ruff check .` → **All checks passed**.
   - Menjalankan full test suite lokal: `uv run pytest` → **83 passed in 32.69s** (76 unit/integration test + 7 E2E Playwright test).
3. **Approval GitHub Actions CI Run:**
   - Karena PR berasal dari fork kontributor baru (`syahrayhan`), GitHub Actions menahan pipeline dengan status `action_required`.
   - Menggunakan GitHub API via GH CLI untuk menyetujui run:
     `gh api --method POST /repos/mufidhadi/titip-makan/actions/runs/38676949918/approve`
   - Memantau proses CI: Job `test` (ID `116240956081`) sukses dalam 14 detik (**green**).
4. **Approval & Merge PR:**
   - Submit approval review: `gh pr review 7 --approve -b "LGTM! Ruff check passed, all 83 tests passed locally and GitHub Actions CI passed."`
   - Squash merge PR ke `main`: `gh pr merge 7 --squash`. Terbentuk commit `fe59813` di `origin/main`.
5. **Deployment ke VPS Produksi (Hostinger 172.23.127.184 via ZeroTier):**
   - Menghubungkan ke VPS via SSH.
   - Backup database SQLite sebelum perubahan:
     `sqlite3 /root/project/titip-makan/data/titip_makan.db ".backup /root/project/titip-makan/data/backup_pre_deploy_20261015_110752.db"`
     (ukuran backup: 72 KB).
   - Baseline data sebelum deploy: 30 `pool_sessions`, 329 `order_items`.
   - Checkout branch `main` di VPS dan pull commit terbaru (`fe59813`).
   - Eksekusi rebuild & restart: `docker compose up -d --build`.
   - Container `titip_makan_app` berhasil di-recreate dan running.
   - Startup aplikasi secara otomatis mengeksekusi `init_db()` dan membentuk tabel baru `weekday_auto_orders`.
6. **Verifikasi Pasca-Deploy di Produksi:**
   - Verifikasi keutuhan data: 30 `pool_sessions`, 329 `order_items`, 0 `weekday_auto_orders` (data riwayat 100% aman).
   - Verifikasi internal VPS (`http://127.0.0.1:8085`):
     - `GET /api/health` → `200 OK`
     - `GET /api/v1/auto-order?user_name=Rayhan` → `200 OK`
     - `GET /api/v1/sessions/suggestions` → memuat tenant `"Padang"`
   - Verifikasi publik domain (`https://titip-irzi.masmuf.cloud`):
     - `GET /api/health` → `{"status":"healthy","app":"Titip Makan MTN CORE","environment":"production"}`
     - `GET /api/v1/auto-order?user_name=Rayhan` → `{"user_name":"Rayhan","enabled":false,"candidates":[]}`
     - Verifikasi HTML frontend: card `Auto Pesan Random` terpasang.

---

## 3. Hasil Pengujian & Bukti Nyata

### A. Pengujian Lokal
```text
uv run ruff check .
All checks passed!

uv run pytest
============================= 83 passed in 32.69s ==============================
- tests/e2e/test_auto_order_e2e.py: PASSED
- tests/integration/test_auto_order_api.py: PASSED
- tests/unit/test_auto_order_service.py: PASSED
- tests/unit/test_catalog_harga.py: PASSED
- Serta seluruh unit, integration, dan E2E test yang ada sebelumnya: PASSED
```

### B. GitHub Actions CI (Run 38676949918)
```text
✓ test in 14s (ID 116240956081)
  ✓ Set up job
  ✓ Run actions/checkout
  ✓ Run astral-sh/setup-uv
  ✓ Sync dependencies
  ✓ Lint (ruff)
  ✓ Unit + integration tests
```

### C. VPS SQLite Verification
```text
Tabel sebelum deploy:
order_items    pool_sessions

Tabel sesudah deploy:
order_items    pool_sessions    weekday_auto_orders

Jumlah baris:
pool_sessions       : 30 (utuh)
order_items         : 329 (utuh)
weekday_auto_orders : 0 (tabel baru siap digunakan)
```

### D. Production Endpoint Verification
```text
$ curl -s https://titip-irzi.masmuf.cloud/api/health
{"status":"healthy","app":"Titip Makan MTN CORE","environment":"production"}

$ curl -s "https://titip-irzi.masmuf.cloud/api/v1/auto-order?user_name=Rayhan"
{"user_name":"Rayhan","enabled":false,"candidates":[]}
```

---

## 4. Tantangan, Kesulitan & Solusi

1. **GitHub Actions Workflow Approval dari Fork PR:**
   - *Tantangan:* PR yang berasal dari public fork memerlukan persetujuan manual administrator repository sebelum CI diizinkan berjalan.
   - *Solusi:* Menjalankan endpoint API GitHub Actions REST via `gh api --method POST /repos/mufidhadi/titip-makan/actions/runs/38676949918/approve` secara langsung dari CLI.
2. **SQLite `.backup` Path Expansion:**
   - *Tantangan:* Sintaks path tilde (`~`) tidak dievaluasi oleh parser SQLite CLI ketika dieksekusi melalui non-interactive SSH remote command string.
   - *Solusi:* Menggunakan absolute path `/root/project/titip-makan/data/...` untuk menjamin backup database tercipta dengan benar dan terverifikasi ukuran filenya.

---

## 5. Lesson Learned

1. Menjalankan verifikasi lokal secara komprehensif (`ruff` + `pytest` unit/integration/E2E) sebelum meng-approve PR memastikan workflow CI di remote GitHub Actions langsung lulus dalam 1 kali percobaan tanpa delay perbaikan.
2. Mekanisme `init_db()` FastAPI pada startup memudahkan pembuatan tabel SQLite baru secara non-destruktif tanpa memerlukan migration runner eksternal untuk arsitektur single-node SQLite.
3. Prosedur online backup SQLite sebelum container recreation memberikan garansi integritas data bagi sistem produksi yang aktif dipakai tim.
