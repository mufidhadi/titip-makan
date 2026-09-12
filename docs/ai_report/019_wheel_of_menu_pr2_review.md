# 019 — Review PR #2 `feat/wheel-of-menu` (titip-makan)

**Reviewer:** himiii (Hermes Agent) · **Tanggal:** 11 Sep 2026 · **Metode:** baca diff + jalankan test di worktree terpisah

| Item | Nilai |
|---|---|
| Repo | `github.com/mufidhadi/titip-makan` |
| PR | **#2 — "Feat/wheel of menu"** (OPEN, MERGEABLE) |
| Penulis | Xharf (Shazi Awaludin), commit dibantu Claude (Sonnet 5 / Opus 5) |
| Branch | `feat/wheel-of-menu` → `main` |
| Ukuran | **+3.195 / −5**, 17 file |
| Deskripsi PR | *(kosong — tidak ada penjelasan)* |

## Apa isinya

Fitur **"wheel of menu"** (roda undian menu) untuk aplikasi titip makan:

### Backend
- **`GET /api/v1/wheel/candidates`** (`src/titip_makan/api/v1/wheel.py`, 39 baris)
  - `mode=tenant|item` (wajib, divalidasi `Literal` → 422 kalau salah)
  - `avoid_last` (bool), `tenant` (str), `max_price` (int ≥ 0), `main_only` (bool, default true)
  - Pemetaan error: `NoActiveSessionError` → **409**, `InvalidTenantError` → **400**
- **`WheelService`** (`services/wheel_service.py`, 107 baris)
  - `get_tenant_candidates(avoid_last)`: kandidat = seluruh vendor di `MASTER_CATALOG` (diurut alfabetis). Kalau `avoid_last=true`, vendor dengan jumlah order **terbanyak di sesi terakhir yang sudah selesai** dikeluarkan (matching case-insensitive via `casefold()`), plus info `excluded_last_tenants` + `avoid_last_applied`.
  - `get_item_candidates(tenant, max_price, main_only)`: kandidat = item dari `MASTER_CATALOG` untuk vendor yang ada di `vendor_options` sesi aktif; filter `main_only` (harga ≥ ambang) dan `max_price` (inklusif).
  - Fallback aman: kalau semua vendor tereksekusi habis → kembalikan daftar penuh.
- **`SessionRepository.get_latest_finished(now)`** — ambil sesi terbaru yang berstatus `CLOSED` **atau** `cutoff_at <= now` (sesi OPEN yang sudah lewat cutoff dianggap selesai).
- **`schemas/wheel.py`** — `WheelCandidate{label,vendor,price?}`, `WheelCandidates{mode,candidates,vendors,excluded_last_tenants,avoid_last_applied}`.
- **`core/catalog.py`** — konstanta baru `MAIN_DISH_MIN_PRICE = 10000` (ambang "makanan berat", heuristik berbasis harga).

### Frontend
- **`static/js/wheel.js`** (426 baris) — render roda SVG dinamis (path/slice, label terpotong 14 char, palet warna), checkbox kandidat, tombol spin, animasi rotasi, integrasi dengan form.
- **`templates/partials/wheel_modal.html`** (62 baris) — modal.
- Wiring di `templates/index.html` (+14/−3) & `coordinator.html` (+11/−2), `static/js/app.js` (+23), `static/js/coordinator.js` (+12) — hasil roda mengisi field vendor (tenant mode) atau item order (item mode).

### Test (semua baru)
- `tests/unit/test_wheel_service.py` (262 baris, **16 test**)
- `tests/integration/test_wheel_api.py` (81 baris, **6 test**)
- `tests/e2e/test_wheel_e2e.py` (159 baris, **3 test** browser: roda di halaman coordinator, roda di form order index, disable spin kalau kandidat < 2)

### Dokumentasi
- `docs/superpowers/specs/2026-09-11-wheel-of-menu-design.md` (217 baris)
- `docs/superpowers/plans/2026-09-11-wheel-of-menu-plan.md` (**1.748 baris**)

## Verifikasi yang dijalankan (bukti, bukan klaim)

| Cek | Hasil |
|---|---|
| `uv run pytest tests/unit/test_wheel_service.py tests/integration/test_wheel_api.py -q` | ✅ **22 passed** (1,54 s) |
| **App dijalankan langsung** (`uvicorn titip_makan.main:app`) lalu endpoint baru di-hit sungguhan | ✅ lihat tabel di bawah |
| E2E browser Playwright (`tests/e2e/test_wheel_e2e.py`) | ⚠️ tidak tuntas di VPS ini (>6 menit, dihentikan). Penyebab yang ditemukan: worktree tidak punya direktori `data/` sehingga SQLite gagal dibuka (`unable to open database file`) → app tidak start. Setelah `mkdir data` app langsung normal, jadi ini **artefak worktree, bukan cacat PR**. Disarankan: jalankan e2e di CI, bukan manual |
| XSS di frontend | ✅ aman — data dirender via `createElement` + `textContent`; `innerHTML` hanya dipakai untuk mengosongkan container/SVG |
| Parsing `vendor_options` | ✅ aman & terbukti live — sesi dibuat lewat API, `vendor_options` kembali sebagai list dan dipakai service tanpa error |
| Impor & dependensi modul baru | ✅ lengkap (`datetime, timezone` sudah diimpor di `session_repository.py`) |
| Halaman frontend ter-render | ✅ `/` dan `/coordinator` HTTP 200, memuat modal roda + `wheel.js` (15.679 byte) |

### Hasil uji langsung terhadap server yang berjalan

| Uji | Perintah/kondisi | Hasil |
|---|---|---|
| Tenant mode | `GET /api/v1/wheel/candidates?mode=tenant` | ✅ 4 vendor (Babun, Buah Potong, Kantin, Mie Ayam), `avoid_last_applied=false` |
| Tenant + avoid_last | `...&avoid_last=true` (tanpa riwayat sesi selesai) | ✅ tidak ada perubahan — sesuai desain |
| Item mode tanpa sesi aktif | `?mode=item` | ✅ **409** `{"detail":"Tidak ada sesi aktif"}` |
| Item mode + sesi aktif | sesi id 1 dengan vendor `["Mie Ayam","Babun"]` | ✅ 5 kandidat Mie Ayam, termurah Rp15.000 (semua ≥ ambang Rp10.000) |
| `main_only=false` | `?mode=item&main_only=false&tenant=Babun` | ✅ 45 item, termurah Rp4.000 → filter ambang terbukti bekerja |
| Tenant tak dikenal | `?mode=item&tenant=Warung Hantu` | ✅ **400** |
| Mode invalid | `?mode=xxx` | ✅ **422** |


## Temuan

### 🔴 Kritis
Tidak ada.

### ⚠️ Perlu diperhatikan

1. **`MAIN_DISH_MIN_PRICE = 10000` berbasis harga, bukan jenis item** (`core/catalog.py:3`).
   Item "makanan berat" murah (< Rp10.000) akan terbuang, dan minuman/side dish mahal (≥ Rp10.000) akan ikut masuk roda. Karena katalog ini data statis dan terkontrol, risikonya kecil — tapi lebih tepat kalau nanti ditambahkan penanda eksplisit di katalog (mis. `category: "main" | "drink" | "side"`).
   *Catatan:* sudah ada test batas (`main_only_excludes_below_threshold_keeps_exact_threshold`), jadi perilakunya sengaja dan terdokumentasi.

2. **`get_latest_finished()` mengambil seluruh baris sesi lalu menyaring di Python** (`session_repository.py:69-79`).
   Pola ini O(n) baris per pemanggilan roda. Untuk sekarang (data kecil) tidak masalah, tapi mudah dijadikan SQL: `WHERE status='CLOSED' OR cutoff_at <= :now ORDER BY created_at DESC LIMIT 1`. Ini juga jalur yang dipanggil tiap spin dengan `avoid_last=true`.

3. **Semantik "avoid last" saat seri (tie).** Kalau sesi terakhir punya beberapa vendor dengan jumlah order sama-sama tertinggi, **semua** vendor tersebut dikeluarkan (bukan hanya satu yang terakhir dipilih). Ada test eksplisit untuk ini (`tie_excludes_all_tied_vendors`), jadi kemungkinan memang disengaja — tapi perlu dipastikan itu perilaku yang diinginkan produk.

4. **Tidak ada CI** (`.github/workflows/` tidak ada). Test E2E hanya jalan kalau dijalankan manual dan **butuh browser Playwright** (di VPS ini `~/.cache/ms-playwright` awalnya kosong, jadi `pytest` penuh akan gagal/hang). Saran: tambahkan workflow CI (unit+integration) dan tandai e2e sebagai marker terpisah (`-m e2e`) supaya tidak memblokir test cepat.

5. **Deskripsi PR kosong.** PR 3.195 baris tanpa deskripsi menyulitkan reviewer dan jejak sejarah. Minimal: ringkas fitur + cara uji.

6. **Dokumentasi sangat berat** (1.965 baris dokumen vs ~1.400 baris kode). Tidak salah, tapi pertimbangkan memangkas `plans/*.md` yang panjang agar repo tetap ringkas (catatan hasil kerja sudah punya jalur `docs/ai_report/`).

### 💡 Saran

- Endpoint baru tanpa autentikasi — konsisten dengan endpoint lain di aplikasi ini (tool internal), tapi kalau nanti diekspos publik, tambahkan proteksi.
- `avoid_last` hanya relevan untuk `mode=tenant`; pertimbangkan menolak kombinasi `mode=item` + `avoid_last=true` (atau dokumentasikan bahwa parameter diabaikan).
- Frontend `wheel.js` 426 baris masih kohesif; tidak perlu dipecah sekarang.
- Test sudah bagus: cakupan edge case (tanpa sesi aktif, tenant invalid, tie, case-insensitive, fallback penuh, cutoff lewat, batas harga inklusif) di atas rata-rata.

## Verdict

**Layak merge (dengan catatan ringan).** Tidak ada masalah keamanan atau kritis; arsitektur rapi (service/repository/schema terpisah, SOLID-ish), test unit+integration lulus, frontend aman dari XSS. Tiga hal yang paling layak dibereskan sebelum/atau segera setelah merge: pemakaian SQL di `get_latest_finished`, deskripsi PR, dan keputusan sadar soal semantik tie di `avoid_last`.

---

## TINDAK LANJUT — review commit `07eef15` (12 Sep 2026)

Penulis merespons dua temuan di atas lewat commit **`07eef15` — "perf: filter get_latest_finished in SQL instead of loading all sessions"** (+15/−10, 2 file). PR tetap OPEN, mergeable, `main` belum bersih dari temuan.

### Apa yang dikerjakan
1. **Temuan #2 (performa) — SELESAI.** `SessionRepository.get_latest_finished()` sekarang memfilter di SQL:
   `WHERE (status='CLOSED' OR (cutoff_at IS NOT NULL AND cutoff_at <= :now)) ORDER BY created_at DESC LIMIT 1` — persis pola yang disarankan (pakai `or_` / `and_` + `limit(1)`).
2. **Temuan #3 (semantik tie) — SELESAI.** Ditambahkan komentar 4 baris di `WheelService.get_tenant_candidates()` yang menyatakan bahwa saat seri **semua** vendor dengan jumlah order tertinggi memang sengaja dikeluarkan, merujuk ke spec §3.3 dan `test_tenant_avoid_last_tie_excludes_all_tied_vendors`. Perilaku jadi terdokumentasi, bukan ambigu.

### Verifikasi ulang (dijalankan sendiri)
| Cek | Hasil |
|---|---|
| `uv run pytest tests/unit/test_wheel_service.py tests/integration/test_wheel_api.py -q` | ✅ **22 passed** (2,81 s) |
| Uji banding **implementasi lama (Python) vs baru (SQL)**, 6 kasus (skrip: `catatan/pribadi/titip-makan-review/verify_latest_finished.py`) | ✅ **identik di semua kasus** |
| Kasus legacy `cutoff_at` **naive** (kekhawatiran utama pada review pertama) | ✅ tetap terdeteksi — tidak ada regresi |

Detail 6 kasus: (1) OPEN + cutoff lewat → ditemukan; (2) OPEN + cutoff depan → `None`; (3) CLOSED tanpa cutoff → ditemukan; (4) OPEN tanpa cutoff → `None`; (5) legacy naive cutoff lewat → ditemukan; (6) dua sesi memenuhi → yang `created_at` terbaru menang.

### Sisa catatan (tidak blocking)
- Deskripsi PR masih kosong.
- `MAIN_DISH_MIN_PRICE` masih heuristik berbasis harga (saran: penanda `category` di katalog).
- Belum ada CI, jadi tidak ada gate otomatis yang membuktikan test hijau — manual (lihat analisa di `020_trunk_based_cicd_analysis.md`).
- Tidak ada balasan teks di thread inline comment (hanya commit) — pantas dikonfirmasi sebagai reviewer.

