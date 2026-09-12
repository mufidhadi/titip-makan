# 021 — Trunk-Based + CI/CD Fase 1 + Deploy main ke VPS (titip-makan)

**Tanggal:** 12 Sep 2026 · **Status:** SELESAI · **Pelaksana:** himiii (Hermes Agent) untuk mas mufid

---

## 1. Ringkasan yang dikerjakan

| # | Pekerjaan | Status |
|---|---|---|
| 1 | Komentar konfirmasi review di PR #2 (dua temuan sudah diperbaiki) | ✅ |
| 2 | Merge PR #2 (wheel of menu) ke `main` | ✅ squash, `09ca3d1` |
| 3 | Merge 2 branch berisi kerjaan yang belum masuk `main` | ✅ |
| 4 | **Fase 1 CI/CD**: workflow CI + ruff + aturan trunk-based di CONTRIBUTING | ✅ PR #3, CI pass 12s |
| 5 | Proteksi branch `main` | ✅ aktif |
| 6 | Bersih-bersih branch (20 branch + `master` dihapus) | ✅ tinggal `main` |
| 7 | Deploy `main` ke VPS produksi | ✅ sehat, data utuh |
| 8 | Verifikasi pasca-deploy | ✅ |

## 2. Konsolidasi `main` (main jadi paling terdepan)

Sebelum: 21 branch di remote, 2 di antaranya berisi pekerjaan yang belum masuk `main`.

- `feature/session-temporary-reopen-timer` (3 commit) → **squash merge** ke `main` (`530a75f`)
- `ops/delete-testing-history-session-vps` (1 commit) → isinya sudah ada di `main` (no-op)
- 20 branch sisa + `master` (duplikat `main`) → **dihapus**
- Hasil: hanya `origin/main` yang tersisa; `main` lokal == `origin/main`; tidak ada branch yang ahead

Verifikasi isi sebelum hapus: `git diff` membuktikan file khas branch (mis. `tests/unit/test_reopen_session.py`) sudah ada di `main`.

## 3. Fase 1 — CI/CD & aturan trunk

**`.github/workflows/ci.yml`** (baru):
- Job `test` = `ruff check` + `pytest tests/unit tests/integration`
- Trigger: `pull_request` + `push` ke `main`
- `permissions: contents: read`, action **di-pin ke commit SHA**, `concurrency` cancel-in-progress
- E2E browser sengaja tidak diikutkan (berat; akan dijadwalkan terpisah)
- Bukti jalan: **CI pass 12 detik** di PR #3

**Tooling:** `ruff>=0.9` sebagai dev dependency, ruleset `E,F` (E501 diabaikan, `tests/**` dikecualikan dari E402), plus perbaikan temuan lint di kode lama (import/variabel tak terpakai, `l` → `page_size`, import `text` duplikat, `noqa: E402` untuk import circular) dan satu assertion tambahan di test.

**`CONTRIBUTING.md`:** bagian *Trunk-Based Development* — branch < 1 hari, squash merge, CI wajib hijau, tidak ada push langsung ke `main`, feature flag untuk pekerjaan belum selesai, aturan hotfix.

## 4. Proteksi `main` (aktif)

| Aturan | Nilai |
|---|---|
| Require pull request | ✅ (tanpa approval wajib — solo admin tidak boleh approve PR sendiri) |
| Required status check | ✅ `test`, **strict** (harus up-to-date dengan `main`) |
| Dismiss stale reviews | ✅ |
| Required linear history | ✅ (squash-only) |
| Block force push / deletion | ✅ |
| Require conversation resolution | ✅ |
| Merge method repo | squash only; merge commit & rebase dimatikan; auto-delete branch; auto-merge aktif |

**Temuan/batasan penting:** opsi **"Restrict who can push"** ditolak API — *"Only organization repositories can have users and team restrictions"*. Repo ini milik akun personal, jadi pembatasan push tidak tersedia. Kontrol yang berlaku: **hanya `mufidhadi` yang punya akses write** + semua perubahan wajib lewat PR. `enforce_admins=false` dipertahankan agar pemilik tetap bisa melakukan perbaikan darurat langsung (didokumentasikan sebagai keputusan sadar).

## 5. Deploy `main` ke VPS

| Langkah | Hasil |
|---|---|
| Backup SQLite (`sqlite3.backup` online, aman saat app jalan) | ✅ `data/backup_pre_deploy_20260912_082032.db` |
| Baseline data sebelum deploy | 5 sesi, 48 order |
| `docker compose up -d --build` | ✅ image `titip-makan-app` dibangun, container **Recreated** |
| Health lokal `http://127.0.0.1:8085/api/health` | ✅ 200 `{"status":"healthy",...}` |
| Health publik `https://titip-irzi.masmuf.cloud/api/health` | ✅ 200 |
| Data setelah deploy | ✅ **5 sesi, 48 order (utuh, tidak berubah)** |
| Sesi terakhir via API | ✅ `id 6 — Titip Makan Siang - Jumat, 11 September 2026` |
| Fitur wheel live | ✅ `GET /api/v1/wheel/candidates` mengembalikan kandidat vendor |
| Fitur reopen sesi live | ✅ route `/api/v1/sessions/{session_id}/reopen` terdaftar |
| Commit ter-deploy | `c549d9d` (tip `main`) |

## 6. Catatan & langkah berikutnya (Fase 2)

1. **Auto-deploy belum aktif** — deploy kali ini masih manual. Fase 2: workflow `cd.yml` (build image di GitHub Runner → GHCR → VPS pull → health verify → rollback otomatis → notifikasi). Ini juga menghilangkan kebutuhan build di VPS (2 vCPU).
2. **Healthcheck compose belum ada** — disarankan ditambahkan sebelum auto-deploy, karena insiden "traefik tidak membuat router" (kasus mochi) berakar pada healthcheck. Untuk sekarang verifikasi masih manual via `/api/health`.
3. **PR dari fork** (seperti PR #2 milik Shazi) perlu approval maintainer agar workflow CI-nya berjalan — perilaku default GitHub untuk kontributor baru.
4. Proteksi main sudah membuktikan dirinya: laporan ini pun dikirim lewat PR + menunggu CI hijau.
