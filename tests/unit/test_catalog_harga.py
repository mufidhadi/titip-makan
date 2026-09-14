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
