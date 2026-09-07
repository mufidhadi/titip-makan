# Laporan Tugas: Deployment ke VPS Hostinger dengan Traefik Reverse Proxy

## Nama Tugas
Deployment aplikasi Titip Makan ke VPS Hostinger (`172.23.127.184` / `31.97.223.48`) menggunakan Docker Compose dan konfigurasi Traefik reverse proxy untuk domain `titip-irzi.masmuf.cloud` dengan sertifikat SSL Let's Encrypt otomatis.

---

## Histori Aksi
1. **Riset & Analisis Lingkungan VPS**:
   - Memeriksa konektivitas jaringan ZeroTier (`856127940ccd3db1`) ke VPS Hostinger (`172.23.127.184`).
   - Mencari kredensial SSH yang tersimpan di repo catatan pribadi mas mufid (`mufidhadi/catatan_pribadi`), meng-clone repo ke `~/Documents/mufid/catatan_pribadi`, dan membaca konfigurasi VPS dari catatan `00012_04_01_2026.md`.
   - Menginstall public key SSH lokal (`~/.ssh/id_ed25519_personal.pub`) ke `/root/.ssh/authorized_keys` di VPS Hostinger via script helper python aman (`uv run --with paramiko`), sehingga autentikasi SSH berikutnya berjalan native via SSH key tanpa interaksi manual.
2. **Inspeksi Arsitektur Traefik di VPS**:
   - Menginspeksi kontainer `traefik` dan service referensi yang sedang berjalan di VPS (`bimbel-naik-level`, `task-manager`).
   - Terverifikasi Traefik berjalan di network bridge `web_proxy`, entrypoint `websecure` (port 443), dan menggunakan ACME certresolver bernama `myresolver`.
   - Mengonfirmasi bahwa port 8080 pada host VPS digunakan oleh Traefik, sehingga container `titip_makan_app` perlu memetakan port host dinamis/berbeda (`PORT_BIND=8085`) agar tidak bertabrakan dengan Traefik.
3. **Konfigurasi Docker Compose & Traefik Labels**:
   - Menambahkan network `web_proxy` (external) ke `docker-compose.yml`.
   - Membuat network `web_proxy` secara lokal agar environment development lokal tetap berjalan identik dengan environment production VPS.
   - Menambahkan labels Traefik:
     ```yaml
     labels:
       - "traefik.enable=true"
       - "traefik.http.routers.titip-irzi.rule=Host(`titip-irzi.masmuf.cloud`)"
       - "traefik.http.routers.titip-irzi.entrypoints=websecure"
       - "traefik.http.routers.titip-irzi.tls.certresolver=myresolver"
       - "traefik.http.services.titip-irzi.loadbalancer.server.port=8080"
     ```
   - Mengatur environment variable `PORT_BIND` dengan default 8080.
4. **Verifikasi Pengujian Lokal (TDD & Regresi)**:
   - Menjalankan test suite unit, integrasi, dan browser E2E Playwright dengan `uv run pytest`. Seluruh 16 test berhasil lulus.
   - Menguji start/restart container lokal melalui `docker compose up -d` dan memverifikasi endpoint `/api/health`.
5. **Git Versioning**:
   - Membuat branch baru `feature/deploy-vps-traefik`.
   - Melakukan commit konfigurasi Traefik (`76ce8e1`) dan push branch ke private GitHub repo `git@github.com:mufidhadi/titip-makan.git`.
6. **Eksekusi Deployment di VPS Hostinger**:
   - Melakukan clone repository via SSH di VPS ke `/root/project/titip-makan` menggunakan branch `feature/deploy-vps-traefik`.
   - Membuat konfigurasi `/root/project/titip-makan/.env` untuk production dengan `ENVIRONMENT=production`, `DEBUG=false`, `PORT_BIND=8085`, dan integrasi WAHA.
   - Menjalankan `docker compose up -d --build` di VPS Hostinger.
   - Memantau log Uvicorn dan proses penerbitan sertifikat SSL oleh ACME Let's Encrypt pada Traefik.
7. **Verifikasi Publik Live**:
   - Melakukan curl HTTPS ke `https://titip-irzi.masmuf.cloud/api/health` dan halaman utama `https://titip-irzi.masmuf.cloud/`.
   - Memastikan handshake TLS 1.3 berhasil, sertifikat valid terbit dari Let's Encrypt (`CN=titip-irzi.masmuf.cloud`, issuer `Let's Encrypt`), dan response status `200 OK`.

---

## Commit & Repo
- **Commit Hash Konfigurasi Traefik**: `76ce8e1`
- **Branch**: `feature/deploy-vps-traefik`
- **Repo URL**: `git@github.com:mufidhadi/titip-makan.git` (Private GitHub)
- **Path di VPS Hostinger**: `/root/project/titip-makan`
- **Domain Publik Aktif**: `https://titip-irzi.masmuf.cloud`

---

## Tech Stack
- **Web Framework**: FastAPI, Uvicorn, Pydantic v2
- **Database**: SQLite (WAL mode, persistent volume `/root/project/titip-makan/data`)
- **Package Manager**: Astral `uv`
- **Reverse Proxy & TLS**: Traefik v3 (Docker provider, ACME TLS Challenge, Let's Encrypt)
- **Containerization**: Docker & Docker Compose (Multi-stage build dengan Astral `uv`)
- **Networking**: ZeroTier VPN, Docker network `web_proxy`

---

## Kesulitan, Tantangan, Bug dan Solusi
| # | Tantangan / Masalah | Solusi |
|---|---|---|
| 1 | SSH ke VPS Hostinger via ZeroTier ditolak (`Permission denied (publickey,password)`) karena public key lokal belum didaftarkan di VPS | Mengambil catatan kredensial dari repo privat `catatan_pribadi` mas mufid, lalu memasang public key personal ke `/root/.ssh/authorized_keys` menggunakan skrip Python paramiko sementara yang dijalankan via `uv run` tanpa menyimpan password dalam file git. |
| 2 | Port 8080 di VPS Hostinger sudah digunakan oleh Traefik (`0.0.0.0:8080->8080/tcp`) | Menghindari bentrok port host dengan menambahkan parameter `PORT_BIND` di `docker-compose.yml` (`${PORT_BIND:-8080}:8080`), lalu di VPS diset `PORT_BIND=8085`. Routing utama Traefik tidak terpengaruh karena berkomunikasi langsung via network internal `web_proxy`. |
| 3 | Network `web_proxy` (external) di Docker Compose akan menyebabkan error saat dijalankan di komputer lokal jika network tersebut belum ada | Membuat network `web_proxy` di Docker lokal (`docker network create web_proxy`) dan mendaftarkan network `default` bersama `web_proxy` pada service, sehingga compose file tetap kompatibel 100% baik di lokal maupun VPS. |
| 4 | Sertifikat SSL awal menampilkan peringatan `ACME Challenge TEMP` saat pertama kali diakses | Menunggu Traefik menyelesaikan TLS challenge dengan Let's Encrypt via port 443; sertifikat resmi `CN=titip-irzi.masmuf.cloud` langsung aktif dalam hitungan detik. |

---

## List Test yang Dilakukan dan Hasil
1. **Automated Unit, Integration & E2E Test (`uv run pytest`)**:
   - **Hasil**: 16/16 passed (14.40s).
   - Meliputi: OrderService, SessionService, Web Routes, API endpoints, dan Browser Mobile E2E flow.
2. **Local Docker Compose Healthcheck**:
   - `curl http://localhost:8080/api/health` -> `{"status":"healthy","app":"Titip Makan MTN CORE","environment":"development"}` (HTTP 200 OK).
3. **VPS Container Healthcheck**:
   - Status container `titip_makan_app` di VPS: `Up (healthy)`.
   - Log Uvicorn: `Application startup complete` dan melayani internal healthcheck.
4. **Public HTTPS Verification**:
   - Command: `curl -Iv https://titip-irzi.masmuf.cloud/api/health`
   - Output:
     - `Server certificate: subject: CN=titip-irzi.masmuf.cloud`
     - `issuer: C=US; O=Let's Encrypt; CN=YR1`
     - `SSL certificate verify ok.`
   - Response Body: `{"status":"healthy","app":"Titip Makan MTN CORE","environment":"production"}` (HTTP 200 OK).
5. **Web Frontend Live Verification**:
   - Command: `curl -s https://titip-irzi.masmuf.cloud/`
   - Output: Render HTML halaman utama aplikasi Titip Makan MTN CORE lengkap dengan style Tailwind CSS dan Plus Jakarta Sans typography.

---

## Lesson Learned
1. **Pemisahan Port Host vs Container Port**: Mengandalkan port default seperti 8080 di server yang menjalankan banyak microservices/traefik berisiko menimbulkan collision. Menggunakan variabel lingkungan (`PORT_BIND`) dengan fallback memberikan fleksibilitas tinggi antara local developer machine dan production server.
2. **Desain Traefik Labels Modular**: Menggunakan nama router yang spesifik domain (`titip-irzi`) mencegah tumpang tindih routing rule dengan service-service lain yang berbagi reverse proxy Traefik yang sama di `web_proxy`.
3. **Automasi Autentikasi ZeroTier & SSH Key**: Mendaftarkan SSH key ed25519 ke server sekali memungkinkan proses deployment GitOps pull-and-compose berikutnya berjalan otomatis dan aman tanpa melibatkan kredensial interaktif.
