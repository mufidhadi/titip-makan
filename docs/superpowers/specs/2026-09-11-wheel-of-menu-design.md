# Wheel of Menu — Design Spec

- **Tanggal:** 2026-09-11
- **Status:** Disetujui (brainstorming), menunggu review spec
- **Pendekatan:** A — kandidat disusun di backend, wheel diputar di klien

## 1. Tujuan

Membantu tim memilih "menu hari ini" dengan roda putar (wheel) di dua konteks:

1. **Mode tenant (koordinator):** memutar wheel berisi tenant/vendor untuk menentukan warung hari ini. Hasil mengisi field `#cs-vendors` di form "Buka Sesi". Koordinator tetap menekan tombol buka sesi sendiri.
2. **Mode item (anggota):** memutar wheel berisi item menu dari tenant sesi aktif. Hasil mengisi form pesanan (`#input-tenant`, `#input-menu`, `#input-price`).

Hasil spin **tidak disimpan** ke database. Wheel hanya membantu mengisi form (prefill).

## 2. Keputusan desain

| Topik | Keputusan |
|---|---|
| Penempatan | Modal di halaman yang sudah ada (`/coordinator` dan `/`), tanpa halaman atau entri navigasi baru |
| Hasil mode tenant | Prefill `#cs-vendors` (mengganti isi field dengan tenant pemenang) |
| Sumber item | Item `MASTER_CATALOG` dari vendor sesi aktif |
| Peluang | Seragam. Aturan hanya menyaring kandidat, tidak memberi bobot |
| Keacakan | Di klien (`crypto.getRandomValues`) |
| Aturan "hindari tenant kemarin" | Opsional, default **OFF** |
| Aturan "makanan berat saja" (harga ≥ Rp10.000) | Opsional, default **ON** (mode item saja) |
| Filter harga maksimum | Opsional, kosong = tanpa batas (mode item saja) |
| Exclude manual | Di klien (checklist irisan), tidak dikirim ke API |

## 3. Backend

### 3.1 Konstanta katalog

`src/titip_makan/core/catalog.py` mendapat konstanta baru:

```python
MAIN_DISH_MIN_PRICE = 10000  # batas inklusif untuk "makanan berat saja"
```

Katalog belum punya kategori, jadi "makanan berat" memakai heuristik harga. Omelette (Rp10.000) ikut. Minuman, sayur tambahan, dan telor (< Rp10.000) terbuang. Dengan aturan ini, Babun turun dari 45 menjadi 32 item.

### 3.2 Repository

`SessionRepository.get_latest_finished(now: datetime) -> Optional[PoolSession]` mengembalikan sesi terbaru (urut `created_at` desc) yang memenuhi `status == "CLOSED"` **atau** `cutoff_at <= now`. Syarat kedua perlu karena sesi yang cutoff-nya lewat baru ditutup secara lazy oleh `get_active_session()`, sehingga statusnya bisa masih `OPEN`.

Untuk menghitung order per vendor dipakai `OrderRepository.get_by_session()` yang sudah ada.

### 3.3 Service — `src/titip_makan/services/wheel_service.py`

```python
class NoActiveSessionError(ValueError): ...
class InvalidTenantError(ValueError): ...

class WheelService:
    def __init__(self, db: AsyncSession): ...
    async def get_tenant_candidates(self, avoid_last: bool = False) -> WheelCandidates: ...
    async def get_item_candidates(
        self,
        tenant: Optional[str] = None,
        max_price: Optional[int] = None,
        main_only: bool = True,
    ) -> WheelCandidates: ...
```

Semua pencocokan nama vendor **tidak peka huruf besar/kecil dan spasi di tepi** (`strip().casefold()`), karena field `vendor` pada order adalah teks bebas. Label yang dikembalikan selalu memakai ejaan key katalog.

**Mode tenant**
1. Kandidat dasar adalah key `MASTER_CATALOG`, diurutkan alfabetis. Setiap kandidat: `label = vendor = <nama tenant>`, `price = None`.
2. Jika `avoid_last=True`:
   - Ambil `get_latest_finished(now)`. Jika tidak ada sesi atau sesi itu tidak punya order, aturan tidak berpengaruh.
   - Hitung order per vendor. Tenant "kemarin" adalah vendor dengan jumlah order terbanyak. Kalau seri, semua vendor yang seri ikut.
   - Buang kandidat yang cocok. `excluded_last_tenants` berisi kandidat yang benar-benar terbuang.
   - Jika pembuangan membuat kandidat kosong, aturan diabaikan: kandidat dikembalikan utuh, `excluded_last_tenants = []`, `avoid_last_applied = False`.
   - `avoid_last_applied = True` hanya jika ada kandidat yang terbuang.

**Mode item**
1. Ambil sesi aktif lewat `SessionService.get_active_session()`. Method ini sekaligus menutup sesi yang cutoff-nya lewat. Jika tidak ada sesi aktif, lempar `NoActiveSessionError`.
2. Vendor yang memenuhi syarat adalah `vendor_options` sesi ∩ key katalog, dengan urutan mengikuti `vendor_options`. Tenant di luar katalog (mis. "Nasi Goreng", "Dimsum") dilewati.
3. Jika `tenant` diberikan dan tidak cocok dengan vendor yang memenuhi syarat, lempar `InvalidTenantError`. Jika cocok, kandidat dibatasi ke tenant tersebut.
4. Kandidat adalah item katalog per vendor (urutan katalog): `label = nama item`, `vendor`, `price`.
5. Filter: `main_only` membuang item dengan `price < MAIN_DISH_MIN_PRICE`, lalu `max_price` membuang item dengan `price > max_price`.
6. Kandidat kosong bukan error, cukup dikembalikan sebagai list kosong.

### 3.4 Schema — `src/titip_makan/schemas/wheel.py`

```python
class WheelCandidate(BaseModel):
    label: str
    vendor: str
    price: Optional[int] = None

class WheelCandidates(BaseModel):
    mode: Literal["tenant", "item"]
    candidates: List[WheelCandidate] = Field(default_factory=list)
    vendors: List[str] = Field(default_factory=list)  # mode item: vendor yang memenuhi syarat SEBELUM filter tenant; mode tenant: []
    excluded_last_tenants: List[str] = Field(default_factory=list)
    avoid_last_applied: bool = False
```

### 3.5 API — `src/titip_makan/api/v1/wheel.py`

`GET /api/v1/wheel/candidates`

| Query | Tipe | Default | Berlaku |
|---|---|---|---|
| `mode` | `Literal["tenant","item"]` | wajib | — |
| `avoid_last` | bool | `false` | tenant |
| `tenant` | str | — | item |
| `max_price` | int, `ge=0` | — | item |
| `main_only` | bool | `true` | item |

Parameter yang tidak berlaku untuk mode yang dipilih diabaikan.

| Kondisi | Status |
|---|---|
| Sukses (termasuk kandidat kosong) | 200 `WheelCandidates` |
| Mode item tanpa sesi aktif | 409 `{"detail": "Tidak ada sesi aktif"}` |
| `tenant` tidak valid | 400 `{"detail": "..."}` |
| `mode` tidak valid / `max_price` negatif | 422 (validasi FastAPI) |

Endpoint hanya membaca data, jadi tidak perlu PIN koordinator. Router didaftarkan di `main.py` dengan `prefix="/api/v1"`, sama seperti router lain.

## 4. Frontend

### 4.1 File

- `src/titip_makan/templates/partials/wheel_modal.html`: markup modal, di-include di `index.html` dan `coordinator.html`.
- `src/titip_makan/static/js/wheel.js`: modul bersama `window.MenuWheel`, dimuat sebelum `app.js` / `coordinator.js`.

### 4.2 API modul

```js
MenuWheel.open({ mode: "tenant" | "item", onApply: (candidate) => void })
```

### 4.3 Perilaku

- **Buka modal:** fetch `/api/v1/wheel/candidates` dengan state filter saat itu.
- **Ubah filter:** fetch ulang. Input harga maksimum di-debounce 300 ms.
- **Exclude manual:** checklist kandidat. Kandidat yang di-uncheck disimpan per `label` dan tetap berlaku setelah fetch ulang, selama label itu masih ada.
- **Spin:**
  - Tombol spin nonaktif jika kandidat aktif < 2, dengan pesan "Minimal 2 pilihan untuk diputar".
  - Tombol juga nonaktif selama wheel berputar.
  - Index pemenang dipilih seragam dengan `crypto.getRandomValues`. Sudut akhir dihitung supaya jarum (di atas) berhenti di tengah irisan pemenang, ditambah ≥ 5 putaran penuh.
  - Animasi berupa transisi CSS `transform` ±4 detik dengan ease-out. Jika `prefers-reduced-motion: reduce`, rotasi langsung ke posisi akhir tanpa transisi.
- **Render wheel:** SVG `<path>` per irisan dengan palet warna berulang yang selaras dengan Tailwind (indigo/purple/emerald/amber/rose/sky). Label ditulis di irisan jika jumlah irisan ≤ 16. Jika lebih, irisan tanpa label, dan pemenang tampil besar di kartu hasil.
- **Kartu hasil:** menampilkan nama pemenang (plus vendor dan harga untuk mode item), tombol **"Pakai hasil ini"** (`onApply` lalu modal ditutup) dan **"Putar lagi"**.
- **Error fetch:** pesan inline di modal. Untuk 409: "Belum ada sesi aktif". Wheel dan tombol spin disembunyikan.

### 4.4 Integrasi halaman

**Coordinator** (`coordinator.html` + `coordinator.js`)
- Tombol 🎡 `data-testid="wheel-open-tenant"` di samping `#cs-vendors`.
- Modal mode tenant menampilkan toggle "Hindari tenant kemarin" (`wheel-avoid-last`, default OFF). Jika `avoid_last_applied`, tampilkan info "Tidak termasuk: <excluded_last_tenants>".
- `onApply`: `#cs-vendors.value = candidate.label`.

**Index** (`index.html` + `app.js`)
- Tombol 🎡 `data-testid="wheel-open-item"` di form pesanan, dirender hanya jika `session` ada (kondisi Jinja).
- Modal mode item menampilkan dropdown tenant ("Semua" + isi field `vendors` dari respons, jadi opsinya tidak menyusut setelah difilter), input harga maksimum (`wheel-max-price`), dan toggle "Makanan berat saja" (`wheel-main-only`, default ON).
- `onApply`: isi `#input-tenant` (vendor), `#input-menu` (label), `#input-price` (price), lalu kirim event `input` dan `change` ke masing-masing field supaya logika autocomplete/autofill di `app.js` ikut berjalan.

### 4.5 Aksesibilitas

- Modal memakai `role="dialog"`, `aria-modal="true"`, dan `aria-labelledby`.
- Esc dan klik backdrop menutup modal. Fokus kembali ke tombol pemicu.
- Pemenang diumumkan lewat region `aria-live="polite"`.
- Semua kontrol bisa diakses keyboard.

### 4.6 `data-testid`

`wheel-open-tenant`, `wheel-open-item`, `wheel-modal`, `wheel-close`, `wheel-svg`, `wheel-spin`, `wheel-result`, `wheel-apply`, `wheel-respin`, `wheel-avoid-last`, `wheel-main-only`, `wheel-max-price`, `wheel-tenant-filter`, `wheel-candidate` (satu per item checklist), `wheel-error`.

## 5. Testing

Mengikuti TDD dan konvensi repo (pytest + pytest-asyncio, SQLite in-memory dari `tests/conftest.py`, E2E dengan Python Playwright).

**Unit — `tests/unit/test_wheel_service.py`**
- Tenant: kandidat = key katalog, urut alfabetis, `price=None`.
- Tenant + `avoid_last`:
  - vendor teratas sesi selesai terakhir terbuang
  - seri → semua vendor yang seri terbuang
  - pencocokan vendor tidak peka huruf besar/kecil
  - belum ada riwayat → tidak berpengaruh
  - semua kandidat terbuang → fallback (`avoid_last_applied=False`)
  - sesi `OPEN` yang cutoff-nya lewat dianggap selesai
- Item:
  - tanpa sesi aktif → `NoActiveSessionError`
  - vendor = `vendor_options` ∩ katalog
  - `tenant` valid membatasi kandidat, `tenant` tidak valid → `InvalidTenantError`
  - `max_price` inklusif
  - `main_only` membuang < 10.000 dan mempertahankan tepat 10.000
  - `main_only=False` mempertahankan semua item
  - kandidat kosong → list kosong
- Repository: `get_latest_finished` memilih sesi yang benar.

**Integration — `tests/integration/test_wheel_api.py`**
- 200 untuk kedua mode (bentuk respons), 409, 400, 422 (`mode` tidak valid, `max_price` negatif).

**E2E — `tests/e2e/test_wheel_e2e.py`**
- Viewport 390×844 dan `reduced_motion="reduce"`, supaya animasi tidak perlu ditunggu.
- Coordinator: buka wheel → spin → hasil tampil → "Pakai" → `#cs-vendors` berisi pemenang.
- Index (dengan sesi aktif): buka wheel → spin → "Pakai" → `#input-tenant`, `#input-menu`, `#input-price` terisi dan konsisten dengan katalog.
- Exclude manual: uncheck sampai tersisa 1 kandidat → tombol spin nonaktif.

## 6. Di luar cakupan

- Menyimpan riwayat spin dan broadcast hasil spin ke WhatsApp.
- Probabilitas berbobot.
- Halaman `/wheel` dan entri navigasi baru.
- Menambah kategori pada `MASTER_CATALOG`.
- Kandidat tenant dari riwayat order (hanya key katalog).

## 7. Risiko & catatan

- Heuristik "makanan berat" berbasis harga bisa salah untuk item murah yang sebenarnya makanan utama. Mitigasinya: toggle bisa dimatikan.
- Mode item pada Babun tetap ±32 irisan meski `main_only` aktif. Wheel beralih ke mode tanpa label, dan pengguna bisa mempersempit dengan filter tenant, harga, atau exclude manual.
- `vendor_options` default di form koordinator berisi tenant di luar katalog. Tenant itu tidak menghasilkan item di mode item.
