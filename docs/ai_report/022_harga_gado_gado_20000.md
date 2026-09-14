# 022 — Ubah harga Gado-gado Rp 15.000 → Rp 20.000

**Tanggal:** 14 Sep 2026
**Pemohon:** Irzi (lewat WhatsApp)
**Status:** ✅ terpasang di produksi

## 1. Permintaan

Irzi mengirim pesan WhatsApp pada **14 Sep 2026, 10:40 WIB**:

> "mas kalo gado gado bisa dirubah enggak nominalnya mas"

Dilanjutkan pesan terima kasih pada 10:41 ("makasih banyak ya mas"), yang menandakan
permintaan disetujui. Nominal baru (**Rp 20.000**) berasal dari mas Mufid.

**Catatan kejujuran soal sumber:** basis data notifikasi (`notifications_db`) hanya
menyimpan **pesan masuk** dan sering terpotong (store WAHA dimatikan), sehingga
percakapan lengkap tidak tersedia. Isi catatan yang berhasil dibaca:

| Waktu (WIB) | Pengirim | Isi |
|---|---|---|
| 14 Sep 10:05 | Transfer berhasil | Rp15.000 udah dikirim ke TABUNGAN BY JAGO IRZI PANDU PANGESTU |
| 14 Sep 10:11 | Irzi Alamanda | siap mas |
| 14 Sep 10:40 | Irzi Alamanda | **mas kalo gado gado bisa dirubah enggak nominalnya mas** |
| 14 Sep 10:41 | Irzi Alamanda | makasih banyak ya mas |

Jadi permintaan mengubah nominal **terbukti ada di catatan**; angka **Rp 20.000
tidak ada** di catatan tersebut (hanya pesan masuk yang terekam). Angka itu dipakai
atas dasar instruksi mas Mufid.

## 2. Di mana harganya disimpan

| Pertanyaan | Jawaban | Bukti |
|---|---|---|
| Berapa tempat menyimpan harga? | **Satu**: `src/titip_makan/core/catalog.py` | `grep -rn "Gado" src/` → hanya satu hasil |
| Dibaca langsung atau disemai ke basis data? | **Dibaca langsung** | `order_service.get_suggestions()` dan `wheel_service` mengimpor `MASTER_CATALOG` |
| Pesanan lama ikut berubah? | **Tidak** | harga disimpan per pesanan (`order_repository.update_price`) |

Kesimpulan: satu perubahan saja cukup, dan riwayat pesanan tidak tersentuh.

## 3. Perubahan

```
src/titip_makan/core/catalog.py   Kantin/Gado-gado: 15000 -> 20000
tests/unit/test_catalog_harga.py  baru (26 baris)
```

Test baru berisi 3 penjaga:
1. Harga Gado-gado = 20000 (mengunci permintaan Irzi)
2. Menu lain di tenant Kantin tidak ikut berubah (Otak-otak tetap 10000)
3. Tidak ada harga nol/negatif/kebesaran di seluruh katalog

*Otak-otak Goreng Polosan* sengaja tidak diubah karena tidak diminta.

## 4. Alur kerja (mengikuti aturan repo)

| Langkah | Hasil |
|---|---|
| Branch | `fix/harga-gado-gado-20000` dari `main` |
| TDD | test ditulis dulu → **RED** (`assert 15000 == 20000`) → ubah harga → **GREEN** |
| Lokal | ruff bersih, **66 test** unit + integration lulus |
| PR | [#5](https://github.com/mufidhadi/titip-makan/pull/5) |
| CI (`test`) | **pass** dalam 12 detik |
| Merge | squash → `8fb2f7c`, branch dihapus |
| Push langsung ke `main` | tidak ada ✅ |

## 5. Deploy & verifikasi

| Langkah | Hasil |
|---|---|
| Cadangan basis data | `data/backup_pre_deploy_20260914_133645.db` |
| Baseline sebelum | 7 sesi, 61 pesanan |
| `docker compose up -d --build` | container Recreated → Started |
| Harga di API lokal | **20000** ✅ |
| Harga di domain publik `titip-irzi.masmuf.cloud` | **20000** ✅ |
| Data setelah deploy | 7 sesi, 61 pesanan (**utuh**) ✅ |

## 6. Yang belum dilakukan

- **Belum membalas WA Irzi.** Aturan yang berlaku: pesan WA masuk hanya dilaporkan,
  tidak dibalas otomatis. Balasan ke Irzi menunggu izin mas Mufid.
