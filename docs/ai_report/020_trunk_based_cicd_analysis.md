# 020 — Analisa: Trunk-Based Development + CI/CD + Auto-Deploy VPS + Manajemen Secret (titip-makan)

**Status:** ANALISA (belum ada perubahan dieksekusi) · **Tanggal:** 12 Sep 2026 · **Penyusun:** himiii (Hermes Agent) untuk mas mufid

---

## 1. Ringkasan eksekutif

**Bisa, dan biayanya Rp0** — karena repo `titip-makan` **public**, maka branch protection dan GitHub Actions **gratis**. Bentuk yang saya rekomendasikan:

```
PR kecil & pendek  →  CI wajib lulus (lint+unit+integration)  →  squash-merge ke main (hanya kamu)
                                   ↓
                   build image di GitHub Runner (bukan di VPS!)  →  push ke GHCR
                                   ↓
        VPS: pull image baru → backup SQLite → recreate container → cek /api/health
                                   ↓
                    sehat? selesai + notifikasi WA  |  tidak? rollback otomatis ke image sebelumnya
```

Tiga hal yang paling menentukan sukses-tidaknya:
1. **Jangan build di VPS** — box 2 vCPU sudah sering load tinggi (kasus build mochi makan ~4,5 jam). Build di runner GitHub, VPS hanya **pull & recreate**.
2. **Healthcheck wajib ada sebelum auto-deploy** — compose `titip-makan` saat ini **tidak punya healthcheck**. Insiden mochi (domain 404 selama berjam-jam) terjadi tepat karena healthcheck rusak → Traefik menolak membuat router. Auto-deploy tanpa healthcheck = auto-deploy kerusakan.
3. **Vault = berlebihan untuk skala ini.** Rekomendasi: **GitHub Environments + SOPS/age**. Vault menambah beban operasional (Raft, *unseal* setiap reboot, backup, HCL) untuk 1 VPS dan beberapa app.

---

## 2. Kondisi saat ini (hasil audit, bukan asumsi)

### Repo GitHub
| Item | Nilai | Implikasi |
|---|---|---|
| Visibility | **PUBLIC** | ✅ Branch protection & Actions **gratis**; ⚠️ semua kode terlihat publik |
| Default branch | `main` | ✅ sudah jadi trunk (tak perlu pindah) |
| Branch protection | **BELUM ADA** (`Branch not protected`) | siapa pun dengan akses push bisa merusak `main` |
| CI/CD | **TIDAK ADA** — `.github/` tidak ada sama sekali | tidak ada gate otomatis |
| Collaborators | hanya `mufidhadi` (admin) | Shazi berkontribusi **via fork** |
| PR #2 | dari **fork** `Xharf/titip-makan-mtn` | PR dari fork **tidak mendapat secret** di CI (default aman) |
| Environments / Secrets | belum ada | perlu dibuat untuk deploy |
| Merge settings | merge commit, squash, rebase **semua aktif**; auto-delete branch **nonaktif** | perlu dirapikan untuk trunk-based |

### Branch (19 di remote) — ini yang bikin migrasi trunk-based gampang
- **15 branch sudah selesai/tertinggal** (ahead=0, behind 4–35): semua `feature/*`, `fix/e2e-bugs-and-improvements`, `release/vps-deployment-production` → **aman dihapus**
- **2 branch masih berisi kerjaan belum masuk**: `feature/session-temporary-reopen-timer` (ahead 3) dan `ops/delete-testing-history-session-vps` (ahead 1) → harus di-merge atau dibuang dulu
- **`master` masih ada dan identik dengan `main`** → duplikat warisan, perlu dipensiunkan (kalau tidak, orang bisa salah push ke sana)
- `task/merge-all-features-to-master` → branch sisa, hapus

### Deploy saat ini (VPS)
- `docker compose` di `/root/project/titip-makan` → container `titip_makan_app`, bind `${PORT_BIND}` → 8080, label Traefik untuk `titip-irzi.masmuf.cloud`, network `web_proxy`
- **Data = SQLite** di bind-mount `./data:/app/data` → **jangan sampai hilang/tertimpa saat deploy**
- `.env` di VPS (gitignored ✓) berisi: `DATABASE_URL`, `COORDINATOR_PIN`, `WAHA_API_KEY`, `WAHA_BASE_URL`, `DEFAULT_GROUP_CHAT_ID`, `PORT_BIND`, dll
- **Tidak ada healthcheck** di compose → gate keamanan auto-deploy belum tersedia
- Tidak ada migrasi DB terstruktur (tanpa Alembic; schema via SQLAlchemy) → perubahan schema berisiko

### Tooling test
`pytest 9` + `pytest-asyncio` + `playwright` (dev). Belum ada linter/formatter di dependency (`ruff` belum ada). E2E browser sudah ada (3 file) tapi berat dan butuh browser → tidak cocok jadi gate wajib setiap PR.

---

## 3. Keputusan yang perlu diambil (opsi + trade-off)

### 3.1 Repo public vs private
| | Public (sekarang) | Private |
|---|---|---|
| Branch protection | ✅ gratis (GitHub Free) | ❌ butuh Pro/Team |
| Actions menit | ✅ gratis tak terbatas | kuota terbatas (±1.500–2.000 menit/bulan) |
| Risiko | kode terlihat siapa pun (termasuk Shazi/kompetitor) | – |

**Rekomendasi:** **tetap public** (sudah jadi pilihanmu di report 006 — repo ini memang untuk portofolio/open). Konsekuensinya: **tidak boleh ada rahasia di repo/workflow** (SOPS aman karena ciphertext).

### 3.2 Runner: GitHub-hosted vs self-hosted
| | GitHub-hosted | Self-hosted (VPS) |
|---|---|---|
| Biaya | gratis (repo public) | gratis (public), tapi… |
| Keamanan | terisolasi, sekali pakai | **berbahaya di repo public**: PR dari fork bisa mengeksekusi kode di mesinmu (termasuk akses `web_proxy`, DB, `.env` app lain) |
| Kecepatan build | cukup | cepat (cache lokal) tapi **menambah beban VPS 2 vCPU** |
| Rekomendasi | ✅ **pakai ini** | ❌ jangan, kecuali butuh banget |

**Rekomendasi:** GitHub-hosted runner. VPS hanya menerima **hasil** (image), tidak menjalankan CI.

### 3.3 Mekanisme deploy
| Opsi | Cara kerja | Kelebihan | Kekurangan |
|---|---|---|---|
| **A. Push via SSH** (rekomendasi) | runner build → push GHCR → SSH ke VPS → `docker compose pull && up -d` | sederhana, langsung, log jelas di Actions | butuh SSH key di GitHub (harus di-scope ketat) |
| B. Pull-based | VPS punya timer/systemd yang cek tag baru di GHCR | tidak ada SSH masuk dari internet | latensi deploy, perlu bikin agen kecil |
| C. Webhook receiver | GH kirim webhook → receiver di VPS (kamu sudah punya platform webhook Hermes!) | elegan, tanpa SSH | lebih banyak komponen, perlu HMAC & rate-limit |
| D. Build di VPS (`git pull && compose up --build`) | paling simpel | nol infrastruktur | ❌ **build di VPS = risiko loading** (kasus mochi 4,5 jam) |

**Rekomendasi:** **A**, dengan catatan: deploy key khusus + user `deploy` non-root + registry **GHCR** supaya VPS tak perlu build.

### 3.4 Manajemen secret — bagian yang kamu tanyakan
Pisahkan **dua jenis** secret, jangan dicampur:

| Jenis | Dipakai oleh | Tempat yang tepat |
|---|---|---|
| (i) Kredensial deploy (SSH key/registry token) | CI/CD | GitHub **Environment secret** (`production`) |
| (ii) Secret aplikasi (`DATABASE_URL`, `WAHA_API_KEY`, `COORDINATOR_PIN`) | app di VPS | file terenkripsi **SOPS+age** di repo, didekripsi di VPS |

Perbandingan opsi (ii):

| Solusi | Beban operasional | Cocok untuk | Catatan |
|---|---|---|---|
| **SOPS + age** ⭐ | **nol** (tak ada service) | solo dev, beberapa app | secret ikut Git (terenkripsi), diff & riwayat rapi, kunci age hanya di VPS/laptop |
| Infisical (self-host) | sedang (1 container + DB) | kalau mau UI, rotasi, banyak app | DX bagus, ringan dibanding Vault |
| Doppler / SaaS | nol (managed) | tim kecil | data keluar ke pihak ke-3 |
| **HashiCorp Vault** | **tinggi**: Raft, *unseal* tiap reboot, backup, HCL, TLS | butuh dynamic secret/PKI, multi-tenant | lisensi BUSL (2023) → fork komunitas: OpenBao |
| GitHub Secrets saja | nol | hanya untuk CI | ❌ jangan untuk secret app produksi (`COORDINATOR_PIN` dsb) |

**Rekomendasi:** **Fase awal SOPS+age** (nol service, aman, gratis). Kalau nanti app-nya sudah 5+ dan butuh rotasi otomatis → baru pertimbangkan **Infisical self-hosted**. **Vault jangan** untuk sekarang: kamu akan menghabiskan waktu memelihara Vault, bukan memelihara produk.

> Catatan penting: kalau nanti memakai Vault/Infisical, saat VPS reboot Vault harus di-*unseal* manual (kecuali auto-unseal dengan cloud KMS) — kalau lupa, **seluruh deploy dan app yang butuh rahasia ikut mati**. Ini penyebab paling umum "Vault bikin ribet".

### 3.5 Proteksi trunk — "cuma aku yang bisa merge"
Aturan untuk `main`:
- ✅ **Require a pull request before merging** (tidak ada push langsung)
- ✅ **Require status checks to pass** (`ci` wajib hijau) + *require branches to be up to date*
- ✅ **Require linear history** (trunk-based: squash/rebase, bukan merge commit)
- ✅ **Block force pushes** & **block deletions**
- ✅ **Restrict who can push** → hanya `mufidhadi`
- ✅ **Require conversation resolution** (komentar review harus selesai)
- ✅ **Automatically delete head branches** setelah merge
- Merge method: **squash only** (matikan merge commit; rebase opsional)

⚠️ **Jebakan solo-admin:** fitur *require 1 approving review* akan **mengunci kamu sendiri** — GitHub tidak mengizinkan menyetujui PR sendiri. Pilihan:
1. `required_approving_review_count = 0` (gate-nya status checks + kamu satu-satunya yang bisa push/merge) ← **rekomendasi untuk sekarang**
2. Tambah 1 reviewer tetap (mis. Shazi) dengan syarat approval 1 → lebih kuat, tapi kamu bergantung orang lain untuk merge PR sendiri
3. Pakai **Rulesets** dengan *bypass* khusus untukmu (kamu tetap harus lulus status checks, tapi boleh merge tanpa approval)

---

## 4. Yang harus disiapkan (checklist)

### A. Repo & aturan
- [ ] Ruleset/branch protection `main` (daftar di §3.5)
- [ ] Squash-only + auto-delete head branch; matikan merge commit
- [ ] Hapus 15 branch selesai + `master` + `task/merge-all-features-to-master`
- [ ] Putuskan 2 branch berisi kerjaan: merge ke `main` atau buang
- [ ] `CODEOWNERS` (biar review otomatis tertuju ke kamu)
- [ ] Template PR + `CONTRIBUTING.md` sudah ada → tambahkan aturan trunk-based (PR < 1 hari, squash, wajib CI hijau)

### B. CI (gate wajib lulus sebelum merge)
- [ ] `ci.yml`: `uv sync` → **ruff** (tambah sebagai dev dep) → `pytest tests/unit tests/integration`
- [ ] E2E Playwright **jangan** jadi gate wajib: jalankan malam (`schedule`) atau manual (`workflow_dispatch`)
- [ ] `permissions: contents: read` (least privilege), pin action pihak-3 ke commit SHA
- [ ] `concurrency` untuk membatalkan run lama
- [ ] Tambah `ruff` + coverage sederhana (opsional)

### C. CD (auto-deploy dari trunk)
- [ ] `cd.yml`: trigger `push` ke `main` **saja** (bukan PR/fork)
- [ ] Build image dengan tag unik (mis. `sha-<short>`), push ke **GHCR**
- [ ] `environment: production` (kalau nanti mau approval manual, tinggal aktifkan)
- [ ] SSH ke VPS sebagai user `deploy` (key khusus, bukan root) → `docker compose pull && up -d`
- [ ] **Backup SQLite sebelum recreate** (`sqlite3 .backup` — aman saat app jalan)
- [ ] Tunggu `healthy` → cek `https://titip-irzi.masmuf.cloud/api/health`
- [ ] Gagal? **rollback otomatis** ke image tag sebelumnya (`IMAGE_TAG` env)
- [ ] Kirim notifikasi hasil deploy (WA/Telegram lewat himiii)
- [ ] `concurrency: deploy-production` (jangan ada 2 deploy bersamaan)

### D. VPS
- [ ] Tambah **healthcheck** di `docker-compose.yml` (belum ada!): `curl -sf http://127.0.0.1:8080/api/health`
- [ ] Buat user `deploy` + sudoer **terbatas** (hanya perintah compose/pull). Catatan: grup `docker` ≈ akses root — batasi dengan sudoers spesifik atau docker rootless
- [ ] Pastikan volume `./data` tidak pernah terhapus & **nama direktori project jangan diubah** (mengubahnya = compose project baru = volume baru = data terlihat "hilang")
- [ ] Cek ruang disk & load sebelum deploy (box 2 vCPU)
- [ ] Backup rutin SQLite (harian, retensi 7 hari)
- [ ] Simpan kunci age SOPS di VPS + backup offline (jangan di repo)

### E. Secret
- [ ] GitHub Environment `production` → isi kredensial deploy (SSH key, token GHCR bila perlu)
- [ ] SOPS+age untuk secret aplikasi (`deploy/secrets/production.enc.yaml`)
- [ ] Dokumentasi rotasi `WAHA_API_KEY` & `COORDINATOR_PIN`
- [ ] Pastikan `.env` tetap gitignored (sudah ✓)

---

## 5. Risiko & mitigasi

| # | Risiko | Dampak | Kemungkinan | Mitigasi |
|---|---|---|---|---|
| 1 | Auto-deploy merilis kode rusak | **Tinggi** | Sedang | CI wajib hijau, smoke test, health check pasca-deploy, rollback otomatis ke image sebelumnya |
| 2 | Deploy key bocor (repo public, log) | **Tinggi** | Rendah | Key khusus user `deploy`, scope minimal, masking, rotasi berkala, jangan pernah `echo` secret |
| 3 | PR dari fork mengeksekusi kode di mesinmu | **Tinggi** | Rendah (kalau hindari self-hosted runner) | Pakai GitHub-hosted runner; jangan `pull_request_target` + secret; approval untuk kontributor baru |
| 4 | Data SQLite hilang/rusak saat deploy | **Tinggi** | Sedang | Backup pra-deploy, volume mount benar, jangan ganti nama project, uji restore 1× |
| 5 | VPS kewalahan (build/CI di VPS) | Sedang | Sedang | Build di runner GitHub, VPS hanya pull image |
| 6 | Rollback gagal karena migrasi schema tidak kompatibel | Tinggi | Sedang | Backup + policy expand-contract; hindari perubahan destruktif; pertimbangkan Alembic |
| 7 | Deploy ganda/tumpang tindih | Sedang | Tinggi (kalau banyak push) | `concurrency` cancel-in-progress |
| 8 | Supply-chain dari action pihak-3 | Sedang | Rendah | Pin ke commit SHA, minimalkan action pihak-3 |
| 9 | Branch protection tak bisa dipakai di masa depan | Sedang | Rendah | Kalau repo dijadikan private, butuh GitHub Pro/Team |
| 10 | Tidak ada uji rollback → panik saat insiden | Sedang | Sedang | Uji rollback minimal sekali, tulis runbook di repo |
| 11 | Secret app tersimpan sebagai GitHub Secret | Sedang | Sedang | Pisahkan: GitHub hanya kredensial deploy; secret app di SOPS |
| 12 | Downtime singkat saat recreate container | Rendah | **Pasti** | Terima saja (beberapa detik). Kalau perlu nol downtime → blue-green (bahas sebelumnya) |

---

## 6. Rekomendasi & rencana eksekusi bertahap

**Fase 1 — Proteksi + CI (aman, tanpa dampak produksi)**
1. Buat ruleset `main` (PR + status checks + linear history + restrict push + squash-only + auto-delete)
2. Tambah `ruff` ke dev dep + `ci.yml` (lint + unit + integration) dan jadikan **required check**
3. Rapikan branch: merge 2 branch berisi kerjaan, hapus 15+1 branch sisa & `master`, matikan branch sisa
4. Update `CONTRIBUTING.md` dengan aturan trunk-based (PR < 1 hari, squash, wajib hijau)

**Fase 2 — CD auto-deploy (mulai otomatis ketika Fase 1 hijau)**
5. Tambah **healthcheck** ke compose + verifikasi `/api/health`
6. Workflow `cd.yml`: build → GHCR → deploy via SSH user `deploy` → health verify → rollback otomatis → notifikasi WA
7. Uji 1×: merge kecil → pastikan deploy jalan; lalu **uji rollback** dengan sengaja (deploy tag lama)
8. Backup SQLite otomatis sebelum setiap deploy + harian

**Fase 3 — Secret management**
9. SOPS + age untuk secret aplikasi + Environment `production` untuk kredensial deploy
10. Dokumentasi rotasi + runbook insiden (`docs/runbook/deploy.md`)

**Fase 4 — Opsional (kalau sudah nyaman)**
11. Nightly E2E Playwright, coverage gate, uptime monitor, dan (kalau perlu) Alembic untuk migrasi terstruktur

**Yang sengaja TIDAK direkomendasikan sekarang:** Vault self-hosted, self-hosted runner, `pull_request_target` dengan secret, build image di VPS, blue-green penuh.

---

## 7. Lampiran — draf file (belum dipasang)

### `.github/workflows/ci.yml` (draf)
```yaml
name: CI
on:
  pull_request:
  push: { branches: [main] }
permissions:
  contents: read
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --group dev
      - run: uv run ruff check .
      - run: uv run pytest tests/unit tests/integration -q
```

### `.github/workflows/cd.yml` (draf, inti)
```yaml
name: Deploy production
on:
  push: { branches: [main] }
  workflow_dispatch:
permissions:
  contents: read
  packages: write
concurrency:
  group: deploy-production
  cancel-in-progress: true
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - name: Build & push image
        run: |
          echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin
          TAG=sha-${GITHUB_SHA::7}
          docker build -t ghcr.io/mufidhadi/titip-makan:$TAG .
          docker push ghcr.io/mufidhadi/titip-makan:$TAG
      - name: Deploy on VPS
        run: |
          install -m700 -D /dev/null ~/.ssh/id_ed25519 <<< "${{ secrets.DEPLOY_SSH_KEY }}"
          printf '%s\n' "${{ secrets.VPS_HOST_KEY }}" > ~/.ssh/known_hosts
          ssh deploy@${{ secrets.VPS_HOST }} "cd /root/project/titip-makan && \
            sqlite3 data/titip_makan.db \".backup 'data/backup-$(date +%F-%H%M).db'\" && \
            IMAGE_TAG=sha-${GITHUB_SHA::7} docker compose pull app && \
            IMAGE_TAG=sha-${GITHUB_SHA::7} docker compose up -d app"
      - name: Health check
        run: |
          for i in $(seq 1 30); do
            code=$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: titip-irzi.masmuf.cloud' http://${{ secrets.VPS_HOST }}/api/health || true)
            [ "$code" = "200" ] && exit 0; sleep 5
          done; exit 1
```

### Ruleset `main` (draf, via API)
```
required_status_checks : ["test"]        # nama job di ci.yml
required_pull_request_reviews : count=0  # solo-admin: 0 approval (lihat §3.5)
required_linear_history : true
allow_force_pushes : false
allow_deletions : false
restrict_pushes : [mufidhadi]
merge_method : squash
auto_delete_head_branch : true
```
