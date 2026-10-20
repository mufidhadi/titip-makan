"""Test harga katalog master.

Permintaan Irzi (WA, 14 Sep 2026 10:40): "mas kalo gado gado bisa dirubah enggak
nominalnya mas" — harga Gado-gado naik dari Rp 15.000 ke Rp 20.000. Test ini mengunci
harga tersebut supaya perubahan berikutnya disengaja, bukan tidak sengaja.
"""

from titip_makan.core.catalog import MASTER_CATALOG


def test_harga_gado_gado_naik_jadi_20000():
    assert MASTER_CATALOG["Kantin"]["Gado-gado"] == 20000


def test_menu_kantin_tidak_ikut_berubah():
    """Perubahan hanya untuk Gado-gado — menu lain di tenant yang sama tetap."""
    assert MASTER_CATALOG["Kantin"]["Otak-otak Goreng Polosan"] == 10000


def test_semua_harga_masih_angka_wajar():
    """Penjaga umum: tidak ada harga nol/negatif/kebesaran di seluruh katalog."""
    for vendor, items in MASTER_CATALOG.items():
        for nama, harga in items.items():
            assert isinstance(harga, int), f"{vendor}/{nama} bukan bilangan bulat"
            assert 1000 <= harga <= 100000, f"{vendor}/{nama} = {harga} di luar kewajaran"


def test_menu_padang_salero_datuak_mamas_lengkap():
    """Menu Padang Salero Datuak Mamas (foodcourt): 32 items, prices per the shared menu list."""
    padang = MASTER_CATALOG["Padang"]
    assert len(padang) == 32
    assert padang["Padang Nasi Rendang"] == 23000
    assert padang["Padang Nasi Tunjang"] == 30000
    assert padang["Padang Nasi Ikan Tongkol Balado"] == 20000
    assert padang["Padang Ikan Bawal Bakar"] == 14000
    assert padang["Padang Perkedel"] == 4000
    assert padang["Padang Tunjang"] == 22000


def test_normalize_vendor_padang_salero_datuak():
    from titip_makan.core.catalog import normalize_vendor
    assert normalize_vendor("Kantin Mamas") == "Padang"
    assert normalize_vendor("Padang Salero Datuak") == "Padang"
    assert normalize_vendor("salero datuak") == "Padang"
    assert normalize_vendor("padang salero datuak mamas") == "Padang"
    assert normalize_vendor("mamas") == "Padang"
    assert normalize_vendor("babu") == "Babun"
    assert normalize_vendor("Mie ayam") == "Mie Ayam"


def test_menu_dapoer_bumbu_lengkap():
    """Menu Dapoer Bumbu lengkap sesuai foto daftar menu fisik."""
    assert "Dapoer Bumbu" in MASTER_CATALOG
    db = MASTER_CATALOG["Dapoer Bumbu"]
    
    # Makanan Utama / Olahan Ayam & Ikan
    assert db["Dapoer Bumbu Nasi Ayam Penyet"] == 20000
    assert db["Dapoer Bumbu Nasi Ayam Kremes"] == 20000
    assert db["Dapoer Bumbu Nasi Ayam Bakar"] == 20000
    assert db["Dapoer Bumbu Ayam Bakar (Tanpa Nasi)"] == 15000
    assert db["Dapoer Bumbu Ayam Kremes (Tanpa Nasi)"] == 15000
    assert db["Dapoer Bumbu Ayam Penyet (Tanpa Nasi)"] == 15000
    assert db["Dapoer Bumbu Nasi Ayam Goreng Asam Manis"] == 20000
    assert db["Dapoer Bumbu Nasi Ayam Goreng Tauco"] == 20000
    assert db["Dapoer Bumbu Ayam Asam Manis (Tanpa Nasi)"] == 15000
    assert db["Dapoer Bumbu Ayam Tauco (Tanpa Nasi)"] == 15000
    assert db["Dapoer Bumbu Ayam Garang Asam (Tanpa Nasi)"] == 15000
    assert db["Dapoer Bumbu Nasi Ayam Garang Asam"] == 20000
    assert db["Dapoer Bumbu Nasi Timbel Komplit"] == 27000
    assert db["Dapoer Bumbu Nasi Sop Ikan Asam Manis Pedas"] == 18000
    assert db["Dapoer Bumbu Nasi Gurame Asam Manis"] == 18000
    assert db["Dapoer Bumbu Nasi Gurame Tauco"] == 18000
    assert db["Dapoer Bumbu Nasi Capcay"] == 18000
    assert db["Dapoer Bumbu Nasi Capcay + Telor Ceplok"] == 23000
    assert db["Dapoer Bumbu Nasi Goreng Teri"] == 15000
    assert db["Dapoer Bumbu Nasi Goreng Bakso"] == 15000
    assert db["Dapoer Bumbu Nasi Goreng Mawut (Campur Mie)"] == 18000
    assert db["Dapoer Bumbu Mie Goreng"] == 15000
    assert db["Dapoer Bumbu Mie Rebus"] == 15000
    assert db["Dapoer Bumbu Bihun Goreng"] == 15000
    assert db["Dapoer Bumbu Bihun Rebus"] == 15000
    assert db["Dapoer Bumbu Kwetiau Goreng"] == 15000
    assert db["Dapoer Bumbu Kwetiau Rebus"] == 15000
    assert db["Dapoer Bumbu Capcay (Tanpa Nasi)"] == 14000
    assert db["Dapoer Bumbu Sop Ikan (Tanpa Nasi)"] == 14000
    assert db["Dapoer Bumbu Gurame Asam Manis (Tanpa Nasi)"] == 14000
    assert db["Dapoer Bumbu Gurame Tauco (Tanpa Nasi)"] == 14000

    # Menu Tambahan
    assert db["Dapoer Bumbu Nasi Putih"] == 5000
    assert db["Dapoer Bumbu Tumis Toge"] == 8000
    assert db["Dapoer Bumbu Tumis Kangkung"] == 8000
    assert db["Dapoer Bumbu Tumis Sawi Putih"] == 8000
    assert db["Dapoer Bumbu Tumis Sawi Ijo"] == 8000
    assert db["Dapoer Bumbu Sayur Asem"] == 8000
    assert db["Dapoer Bumbu Terong Penyet"] == 5000
    assert db["Dapoer Bumbu Telor Dadar"] == 5000
    assert db["Dapoer Bumbu Telor Ceplok"] == 5000
    assert db["Dapoer Bumbu Tahu Goreng"] == 2000
    assert db["Dapoer Bumbu Tempe Goreng"] == 2000
    assert db["Dapoer Bumbu Tahu Penyet"] == 3000
    assert db["Dapoer Bumbu Tempe Penyet"] == 3000
    assert db["Dapoer Bumbu Kerupuk"] == 2000

    # Minuman
    assert db["Dapoer Bumbu Es Jeruk"] == 8000
    assert db["Dapoer Bumbu Es Lemon Tea"] == 8000
    assert db["Dapoer Bumbu Wedang Jahe"] == 5000
    assert db["Dapoer Bumbu Es Teh Tarik"] == 6000
    assert db["Dapoer Bumbu Es Indocafe"] == 5000
    assert db["Dapoer Bumbu Kopi Tubruk"] == 5000
    assert db["Dapoer Bumbu Air Mineral"] == 4000
    assert db["Dapoer Bumbu Teh Manis Panas"] == 4000
    assert db["Dapoer Bumbu Es Teh Manis"] == 5000
    assert db["Dapoer Bumbu Es Teh Tawar"] == 3000
    assert db["Dapoer Bumbu Air Putih Es"] == 2000
    assert db["Dapoer Bumbu Teh Tawar Panas"] == 1000


def test_normalize_vendor_dapoer_bumbu():
    from titip_makan.core.catalog import normalize_vendor
    assert normalize_vendor("dapoer bumbu") == "Dapoer Bumbu"
    assert normalize_vendor("Dapoer Bumbu") == "Dapoer Bumbu"
    assert normalize_vendor("dapur bumbu") == "Dapoer Bumbu"
    assert normalize_vendor("Dapur Bumbu") == "Dapoer Bumbu"
    assert normalize_vendor("dapoer") == "Dapoer Bumbu"
    assert normalize_vendor("dapur") == "Dapoer Bumbu"


def test_dapoer_bumbu_catalog_tidak_ada_menu_terdobel():
    """Memastikan katalog Dapoer Bumbu bersih dari item terdobel (komposit garis miring & ejaan ganda)."""
    db = MASTER_CATALOG["Dapoer Bumbu"]
    # 1. Komposit garis miring yang menduplikasi menu individual tidak boleh ada di katalog
    slash_composites = [
        "Dapoer Bumbu Nasi Ayam Penyet / Kremes / Bakar",
        "Dapoer Bumbu Ayam Bakar / Kremes / Penyet (Tanpa Nasi)",
        "Dapoer Bumbu Nasi Ayam Goreng Asam Manis / Tauco",
        "Dapoer Bumbu Ayam Asam Manis / Tauco / Garang Asam (Tanpa Nasi)",
        "Dapoer Bumbu Nasi Gurame Asam Manis / Tauco",
        "Dapoer Bumbu Nasi Goreng Teri / Nasi Goreng Bakso",
        "Dapoer Bumbu Mie / Bihun / Kwetiau Goreng / Rebus",
        "Dapoer Bumbu Cap Cay / Sop Ikan / Gurame Asam Manis / Tauco (Tanpa Nasi)",
        "Dapoer Bumbu Tumis Toge / Kangkung",
        "Dapoer Bumbu Tumis Sawi Putih / Ijo",
        "Dapoer Bumbu Telor Dadar / Ceplok",
        "Dapoer Bumbu Tahu / Tempe Goreng",
        "Dapoer Bumbu Tahu / Tempe Penyet",
        "Dapoer Bumbu Es Jeruk / Es Lemon Tea",
        "Dapoer Bumbu Es Indocafe / Kopi Tubruk",
    ]
    for composite in slash_composites:
        assert composite not in db, f"Menu komposit terdobel ditemukan: {composite}"

    # 2. Ejaan ganda / variasi duplikat tidak boleh ada
    duplicate_spellings = [
        "Dapoer Bumbu Nasi Cap Cay",  # Duplikat dari Nasi Capcay
        "Dapoer Bumbu Cap Cay (Tanpa Nasi)",  # Duplikat dari Capcay (Tanpa Nasi)
        "Dapoer Bumbu Kwitiaw Goreng",  # Duplikat dari Kwetiau Goreng
        "Dapoer Bumbu Kwitiaw Rebus",  # Duplikat dari Kwetiau Rebus
        "Dapoer Bumbu Nasi Goreng Mawut",  # Duplikat dari Nasi Goreng Mawut (Campur Mie)
        "Dapoer Bumbu Teh Manis",  # Duplikat dari Teh Manis Panas
        "Dapoer Bumbu Teh Tawar",  # Duplikat dari Teh Tawar Panas
        "Dapoer Bumbu Teh Tarik",  # Duplikat dari Es Teh Tarik
        "Dapoer Bumbu Lemon Tea",  # Duplikat dari Es Lemon Tea
    ]
    for dup in duplicate_spellings:
        assert dup not in db, f"Ejaan/varian duplikat ditemukan: {dup}"

    # 3. Jumlah menu Dapoer Bumbu terdaftar tepat 59 item unik
    assert len(db) == 59



