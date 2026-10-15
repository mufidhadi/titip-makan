import sqlite3
import pytest
from pathlib import Path
from titip_makan.tools.data_cleansing import clean_database, DatabaseCleaner


@pytest.fixture
def dirty_db_path(tmp_path: Path) -> Path:
    db_file = tmp_path / "test_titip.db"
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE pool_sessions (
            id INTEGER PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            coordinator_name VARCHAR(100) NOT NULL,
            coordinator_phone VARCHAR(50),
            vendor_options TEXT NOT NULL,
            payment_info TEXT,
            status VARCHAR(20) NOT NULL,
            cutoff_at DATETIME,
            created_at DATETIME NOT NULL,
            closed_at DATETIME
        );
    """)
    c.execute("""
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY,
            session_id INTEGER NOT NULL,
            user_name VARCHAR(100) NOT NULL,
            vendor VARCHAR(100) NOT NULL,
            item_name VARCHAR(150) NOT NULL,
            variant VARCHAR(100),
            notes TEXT,
            price INTEGER NOT NULL,
            is_paid BOOLEAN NOT NULL,
            created_at DATETIME NOT NULL,
            payment_status VARCHAR(50) DEFAULT 'UNPAID'
        );
    """)
    # Insert dirty records
    c.execute("""
        INSERT INTO order_items (id, session_id, user_name, vendor, item_name, price, is_paid, created_at)
        VALUES
        (40, 5, 'Andre', 'Andrean', 'Mie Ayam Pangsit Rebus', 15000, 0, '2026-09-10 03:25:27'),
        (59, 8, 'Diky', 'gado-gado', 'Gado-gado', 15000, 0, '2026-09-14 03:05:05'),
        (77, 9, 'Repka', 'Babun', 'Nasi + telor dadar bakar double', 0, 1, '2026-09-15 03:13:55'),
        (78, 9, 'Raka', 'Kantin Parkiran', 'Nasi Tongseng Ayam', 0, 1, '2026-09-15 03:14:17'),
        (80, 9, 'Amal', 'babu', 'Nasi + telor dadar bakar double', 13000, 0, '2026-09-15 03:19:28'),
        (91, 10, 'Rayhan', 'Mie ayam', 'Mie Ayam Bakso (Pangsit Goreng)', 18000, 1, '2026-09-16 03:20:32'),
        (97, 11, 'Agung', 'Mie ayam', 'Mie ayam bakso pangsit rebus', 18000, 0, '2026-09-17 03:02:52'),
        (205, 20, 'Shazi', 'Babun', 'Nasi telor double', 0, 0, '2026-09-30 03:43:13'),
        (209, 21, 'Harist', 'Babun', 'Mie Ayam Pangsit Rebus', 15000, 0, '2026-10-01 03:04:52'),
        (297, 28, 'Diky', 'Babun', 'Nasi Telor + Tahu + Tempe', 0, 0, '2026-10-12 03:14:46'),
        (321, 30, 'Raka', 'Kantin Mamas', 'Nasi Padang Rendang', 0, 0, '2026-10-14 03:15:59');
    """)
    conn.commit()
    conn.close()
    return db_file


def test_dry_run_does_not_modify(dirty_db_path: Path):
    cleaner = DatabaseCleaner(str(dirty_db_path))
    report = cleaner.clean(dry_run=True, backup=False)

    assert report.total_fixes > 0

    # Verify DB still has dirty records
    conn = sqlite3.connect(dirty_db_path)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM order_items WHERE vendor = 'babu'")
    assert c.fetchone()[0] == 1
    c.execute("SELECT COUNT(*) FROM order_items WHERE price = 0")
    assert c.fetchone()[0] == 5
    conn.close()


def test_clean_fixes_all_anomalies(dirty_db_path: Path):
    cleaner = DatabaseCleaner(str(dirty_db_path))
    report = cleaner.clean(dry_run=False, backup=True)

    assert report.total_fixes > 0
    assert report.backup_path is not None
    assert Path(report.backup_path).exists()

    conn = sqlite3.connect(dirty_db_path)
    c = conn.cursor()

    # 1. No typo vendors
    c.execute("SELECT COUNT(*) FROM order_items WHERE vendor IN ('babu', 'Mie ayam', 'Andrean', 'gado-gado')")
    assert c.fetchone()[0] == 0

    # 2. Check Andrean -> Mie Ayam
    c.execute("SELECT vendor FROM order_items WHERE id = 40")
    assert c.fetchone()[0] == "Mie Ayam"

    # 3. Check Babun with Mie Ayam item -> vendor Mie Ayam
    c.execute("SELECT vendor FROM order_items WHERE id = 209")
    assert c.fetchone()[0] == "Mie Ayam"

    # 4. Check gado-gado -> Kantin
    c.execute("SELECT vendor, item_name FROM order_items WHERE id = 59")
    row = c.fetchone()
    assert row[0] == "Kantin"
    assert row[1] == "Gado-gado"

    # 5. Check babu -> Babun
    c.execute("SELECT vendor FROM order_items WHERE id = 80")
    assert c.fetchone()[0] == "Babun"

    # 6. Check menu normalization
    c.execute("SELECT item_name FROM order_items WHERE id IN (77, 80, 205)")
    for r in c.fetchall():
        assert r[0] == "Babun Nasi Telor Dobel"

    c.execute("SELECT item_name FROM order_items WHERE id = 97")
    assert c.fetchone()[0] == "Mie Ayam Bakso (Pangsit Rebus)"

    # 7. No price == 0
    c.execute("SELECT COUNT(*) FROM order_items WHERE price <= 0")
    assert c.fetchone()[0] == 0

    c.execute("SELECT price FROM order_items WHERE id = 77")
    assert c.fetchone()[0] == 13000

    c.execute("SELECT price FROM order_items WHERE id = 78")
    assert c.fetchone()[0] == 25000

    c.execute("SELECT price FROM order_items WHERE id = 205")
    assert c.fetchone()[0] == 13000

    c.execute("SELECT price FROM order_items WHERE id = 297")
    assert c.fetchone()[0] == 15000

    c.execute("SELECT price FROM order_items WHERE id = 321")
    assert c.fetchone()[0] == 23000

    # Check Kantin Mamas -> Padang & Nasi Padang Rendang -> Padang Nasi Rendang
    c.execute("SELECT vendor, item_name FROM order_items WHERE id = 321")
    row = c.fetchone()
    assert row[0] == "Padang"
    assert row[1] == "Padang Nasi Rendang"

    conn.close()

