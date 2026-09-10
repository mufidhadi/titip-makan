# Laporan Tugas: Pembersihan Data Testing Riwayat Sesi #1 di VPS Hostinger

## Nama Tugas
Pembersihan data testing riwayat sesi titip makan `Sesi #1 • Sel, 8 Sep 2026, 05.33` (`Titip Makan 7/09/2026`) di database SQLite VPS Hostinger (`172.23.127.184` / `titip-irzi.masmuf.cloud/history`) beserta order items terkait agar tidak mengotori analitik dan riwayat sesi produksi.

---

## Histori Aksi
1. **Pemeriksaan Lingkungan & Repositori**:
   - Memeriksa repo lokal di `/Users/anb-0826014/project/mufid/titip-makan`.
   - Membuat branch baru `ops/delete-testing-history-session-vps` dari branch `release/vps-deployment-production` sesuai aturan isolasi branch.
   - Menguji konektivitas SSH ke VPS Hostinger `root@172.23.127.184` menggunakan private key `~/.ssh/id_ed25519_personal`. Koneksi berhasil (`srv1245657`).

2. **Riset Teknis & Best Practice Deletion SQLite**:
   - Menelusuri dokumentasi dan referensi web terkait `PRAGMA foreign_keys = ON;` dan mekanisme penghapusan cascading pada SQLite.
   - Mengidentifikasi bahwa SQLite secara default tidak mengaktifkan penegakan foreign key constraints per koneksi kecuali diaktifkan secara eksplisit, sehingga transaksi atomik harus menghapus child records (`order_items`) dan parent record (`pool_sessions`) secara eksplisit dan aman.

3. **Inspeksi Data Live & Verifikasi Identitas Record**:
   - Memeriksa endpoint API publik `https://titip-irzi.masmuf.cloud/api/v1/sessions/history`.
   - Mengonfirmasi bahwa `Sesi #1 • Sel, 8 Sep 2026, 05.33` adalah sesi dengan:
     - `id`: `1`
     - `title`: `"Titip Makan 7/09/2026"`
     - `created_at`: `2026-09-07T22:33:30.032894Z` (konversi UTC ke WIB: `05:33 WIB`, Selasa 8 September 2026).
     - Memiliki 2 pesanan testing: `id: 1` (user: `Mufid`, `nasi telor dobel`, Rp 13.000) dan `id: 2` (user: `Adrian`, `nasi goreng nanas`, Rp 16.000).
   - Memastikan sesi asli produksi adalah `id: 2` ("Titip Makan Siang") dengan 13 pesanan asli tim MTN CORE total Rp 241.000.

4. **Pembuatan Backup Database Pra-Eksekusi (Zero Risk)**:
   - Membuat salinan database SQLite sebelum perubahan:
     `/root/project/titip-makan/data/titip_makan.db.bak_20260908_pre_delete_session_1` (28.672 bytes).

5. **Eksekusi Penghapusan Transaksional**:
   - Menjalankan script Python transaksional dengan `PRAGMA foreign_keys = ON;` via SSH:
     - Menghapus 2 record `order_items` dengan `session_id = 1`.
     - Menghapus 1 record `pool_sessions` dengan `id = 1`.
     - Commit transaksi dan menjalankan `PRAGMA integrity_check;`.
   - Output eksekusi:
     ```text
     BEFORE: session 1 count = 1, orders count = 2
     DELETED: sessions deleted = 1, order_items deleted = 2
     INTEGRITY: [('ok',)]
     REMAINING SESSIONS: [(2, 'Titip Makan Siang', '2026-09-08 02:00:48.622520')]
     REMAINING ORDERS COUNT: 13
     ```

6. **Verifikasi Publik & Integritas Sistem**:
   - Melakukan query langsung ke endpoint live `https://titip-irzi.masmuf.cloud/api/v1/sessions/history`:
     - Total sesi sekarang adalah `1` (hanya Sesi #2 "Titip Makan Siang").
     - Sesi #1 beserta 2 item testing sudah hilang sepenuhnya.
   - Memverifikasi endpoint analitik `https://titip-irzi.masmuf.cloud/api/v1/analytics/overview`:
     - `total_sessions`: 1
     - `total_orders`: 13
     - `total_spend`: Rp 241.000 (tidak lagi tercemar pesanan testing Rp 29.000).
   - Memverifikasi endpoint leaderboard `https://titip-irzi.masmuf.cloud/api/v1/analytics/leaderboard`:
     - Seluruh ranking dan badge terhitung murni dari data pesanan riil.
   - Menjalankan seluruh test suite lokal `uv run pytest`: 37 passed dalam 8.77 detik.

---

## Nomor Hash Commit, Branch, dan Repo
- **Branch**: `ops/delete-testing-history-session-vps`
- **Repo URL**: `git@github.com:mufidhadi/titip-makan.git` (Private GitHub)
- **Path di VPS Hostinger**: `/root/project/titip-makan`

---

## Tech Stack
- **Database**: SQLite (WAL mode, file: `/root/project/titip-makan/data/titip_makan.db`)
- **Backend**: FastAPI, SQLAlchemy Async, Uvicorn, Python 3.12
- **Environment & Dependency Manager**: Astral `uv`
- **Reverse Proxy & TLS**: Traefik v3, Docker Compose
- **Network**: ZeroTier (`856127940ccd3db1`, VPS IP `172.23.127.184`)

---

## List Kesulitan, Tantangan, Bug dan Solusi
1. **CLI `sqlite3` tidak tersedia di VPS Host**:
   - *Tantangan*: Command `sqlite3` tidak terpasang langsung di sistem host VPS Hostinger (`command not found`).
   - *Solusi*: Menggunakan modul bawaan `python3 -c "import sqlite3..."` di VPS host, yang memiliki modul SQLite versi 3.45.1 dan dapat mengakses file database secara native dan aman.
2. **Karakter Escape & Multi-line String pada SSH**:
   - *Tantangan*: Script python multi-baris yang dijalankan via perintah inline SSH dapat mengalami masalah quoting jika tidak hati-hati.
   - *Solusi*: Menyusun perintah Python satu baris ringkas terstruktur dengan penanganan error dan pengecekan integritas langsung, sehingga eksekusi tuntas tanpa hang.

---

## List Test yang Dilakukan dan Hasil
1. **Verifikasi Identifikasi Record Sebelum Hapus**:
   - Query: `SELECT id, title, created_at FROM pool_sessions WHERE id = 1` -> Ditemukan `(1, 'Titip Makan 7/09/2026', '2026-09-07 22:33:30.032894')`
   - Query: `SELECT count(*) FROM order_items WHERE session_id = 1` -> Ditemukan 2 pesanan testing.
   - Status: **VALID**
2. **Pemeriksaan Integritas Database Pra & Pasca Penghapusan**:
   - Perintah: `PRAGMA integrity_check;`
   - Hasil: `[('ok',)]`
   - Status: **PASSED**
3. **Pemeriksaan API Publik Live**:
   - `GET https://titip-irzi.masmuf.cloud/api/v1/sessions/history`
     - Response: Total 1 sesi (`id: 2`), Sesi #1 tidak ada lagi.
   - `GET https://titip-irzi.masmuf.cloud/api/v1/analytics/overview`
     - Response: Total 1 sesi, 13 pesanan, total belanja Rp 241.000.
   - Status: **PASSED**
4. **Regresi Lokal Suite**:
   - Perintah: `uv run pytest`
   - Hasil: `37 passed in 8.77s`
   - Status: **PASSED**

---

## Lesson Learned
- Selalu lakukan backup snapshot bertanggal sebelum memanipulasi database produksi, sekecil apa pun perubahannya.
- Saat menggunakan SQLite, foreign key enforcement wajib diperhatikan (`PRAGMA foreign_keys = ON;`) atau lakukan penghapusan child-parent secara eksplisit dalam satu blok transaksi database (`conn.commit()`).
- Data analitik yang dihitung secara agregatif langsung dari database akan otomatis kembali akurat seketika data testing dibersihkan.
