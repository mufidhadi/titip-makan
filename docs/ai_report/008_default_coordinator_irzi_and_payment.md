# Laporan Tugas: Konfigurasi Default Koordinator Irzi dan Pembayaran Gopay

## Nama Tugas
Pengaturan nilai default nama koordinator menjadi **Irzi**, informasi pembayaran default ke **gopay ke +62 815-1382-5480**, nomor WhatsApp koordinator default ke **+62 815-1382-5480**, serta deployment pembaruan ke VPS Hostinger di domain `titip-irzi.masmuf.cloud`.

---

## Histori Aksi
1. **Perencanaan & Penerapan Test-Driven Development (TDD)**:
   - Membuat branch git baru `feature/default-coordinator-irzi`.
   - Menambahkan test baru `test_create_session_with_defaults` di `tests/unit/test_session_service.py` untuk memverifikasi bahwa pembuatan sesi tanpa parameter opsional akan otomatis menggunakan koordinator `Irzi`, pembayaran `gopay ke +62 815-1382-5480`, dan nomor telepon `+62 815-1382-5480`.
   - Menjalankan `uv run pytest tests/unit/test_session_service.py` untuk memastikan test gagal terlebih dahulu (*Red phase*).
2. **Implementasi Kode Sumber**:
   - **Schema Pydantic** (`src/titip_makan/schemas/session.py`):
     - `coordinator_name`: default diubah menjadi `"Irzi"`.
     - `payment_info`: default diubah menjadi `"gopay ke +62 815-1382-5480"`.
     - `coordinator_phone`: default diubah menjadi `"+62 815-1382-5480"`.
   - **Model SQLAlchemy** (`src/titip_makan/models/session.py`):
     - Kolom `coordinator_name`: default `"Irzi"`.
     - Kolom `payment_info`: default `"gopay ke +62 815-1382-5480"`.
     - Kolom `coordinator_phone`: default `"+62 815-1382-5480"`.
   - **Frontend Template** (`src/titip_makan/templates/coordinator.html`):
     - Form input `#cs-coordinator`: `value="Irzi"`.
     - Form input `#cs-payment`: `value="gopay ke +62 815-1382-5480"`.
     - Form input `#cs-phone`: `value="+62 815-1382-5480"`.
     - Form input `#cs-title`: `value="Titip Makan Siang"`.
3. **Verifikasi Pengujian & Regresi**:
   - Menjalankan `uv run pytest` (*Green phase*): 17/17 passed (0.05s unit, 14.04s full suite termasuk browser E2E Playwright).
   - Membangun ulang dan me-restart container Docker lokal (`docker compose up -d --build`).
   - Melakukan commit awal (`dc9a547`) dan push ke branch `feature/default-coordinator-irzi`.
4. **Deployment ke VPS & Pemecahan Masalah Multi-Network Traefik**:
   - Menghubungkan ke VPS Hostinger via SSH, checkout branch `feature/default-coordinator-irzi`, dan pull commit terbaru.
   - Mengidentifikasi issue `504 Gateway Timeout` saat container terhubung ke dua network (`titip-makan_default` dan `web_proxy`). Traefik secara acak memilih IP internal yang tidak terjangkau.
   - Menambahkan label `traefik.docker.network=web_proxy` di `docker-compose.yml` agar Traefik secara deterministik melakukan proxy melalui network `web_proxy`.
   - Melakukan commit perbaikan (`79edcbf`), push ke GitHub, dan deploy ulang di VPS.
5. **Verifikasi Live Produksi**:
   - Endpoint `https://titip-irzi.masmuf.cloud/` menghasilkan `200 OK`.
   - Endpoint `https://titip-irzi.masmuf.cloud/coordinator` menghasilkan `200 OK` dengan elemen input default terverifikasi (`Irzi`, `gopay ke +62 815-1382-5480`, `+62 815-1382-5480`).

---

## Commit & Repo
- **Commit Hash**:
  - `dc9a547`: `feat(coordinator): set default coordinator name to Irzi and payment info to gopay +62 815-1382-5480`
  - `79edcbf`: `fix(traefik): specify traefik.docker.network=web_proxy for multi-network container routing`
- **Branch**: `feature/default-coordinator-irzi`
- **Repo URL**: `git@github.com:mufidhadi/titip-makan.git` (Private GitHub)
- **Path di VPS**: `/root/project/titip-makan`
- **Live URL**: [https://titip-irzi.masmuf.cloud/coordinator](https://titip-irzi.masmuf.cloud/coordinator)

---

## Tech Stack
- **Backend**: FastAPI, SQLAlchemy 2.0, Pydantic v2
- **Frontend**: Jinja2, Tailwind CSS, Vanilla JS
- **Reverse Proxy**: Traefik v3 (dengan SSL Let's Encrypt otomatis)
- **Testing**: pytest, pytest-asyncio, Playwright
- **Package Manager & Runtime**: Astral `uv`, Python 3.12, Docker Compose

---

## Kesulitan, Tantangan, Bug dan Solusi
| # | Masalah | Solusi |
|---|---|---|
| 1 | `504 Gateway Timeout` di Traefik setelah recreate container di VPS | Kontainer terhubung ke `titip-makan_default` dan `web_proxy`. Traefik mencoba meroute trafik ke IP `default` yang berada di luar jangkauan network Traefik. Solusinya adalah menambahkan label deklaratif `traefik.docker.network=web_proxy` di `docker-compose.yml`. |
| 2 | Format nomor telepon koordinator untuk integrasi WhatsApp | Nomor default diset `+62 815-1382-5480` yang secara otomatis disanitasi oleh fungsi `app.js` (`replace(/[^0-9]/g, "")` -> `6281513825480`) sehingga tombol 1-klik notif WA pemesan langsung mengarah ke chat WhatsApp Irzi tanpa error format. |

---

## List Test yang Dilakukan dan Hasil
1. **Unit Test Baru (`tests/unit/test_session_service.py`)**:
   - `test_create_session_with_defaults`: Memastikan inisialisasi default menggunakan `Irzi`, `gopay ke +62 815-1382-5480`, dan `+62 815-1382-5480`. (Passed)
2. **Full Test Suite (`uv run pytest`)**:
   - 17 passed dalam 14.04s.
3. **Local Docker Verification**:
   - `curl -s http://localhost:8080/coordinator | grep -E "(cs-coordinator|cs-payment|cs-phone)"` -> Berhasil mencetak input default yang sesuai.
4. **Live VPS Production Verification**:
   - `curl -s https://titip-irzi.masmuf.cloud/coordinator | grep -E "(cs-coordinator|cs-payment|cs-phone)"` -> Terverifikasi `Irzi` dan `gopay ke +62 815-1382-5480`.

---

## Lesson Learned
1. **Ketegasan Deklarasi Network Traefik**: Bila sebuah container Docker Compose terhubung ke lebih dari 1 network (misalnya network internal service dan network reverse proxy eksternal), **wajib** menyertakan label `traefik.docker.network=<nama_network_proxy>`. Mengabaikan label ini akan menyebabkan Traefik memilih network secara acak dan memicu `504 Gateway Timeout`.
2. **Konsistensi Default di Seluruh Layer (Pydantic, Model, UI)**: Nilai default aplikasi harus dideklarasikan secara koheren mulai dari database model, schema request validation Pydantic, hingga atribut `value` pada form template HTML agar pengalaman pengguna seamless baik via API maupun web dashboard.
