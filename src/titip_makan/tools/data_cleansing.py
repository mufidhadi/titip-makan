"""Database data cleansing module for Titip Makan SQLite database.
Follows SOLID principles:
- CleansingReport: Data Transfer Object (SRP)
- DatabaseCleaner: Orchestrates backup, rule execution, and transactional updates (SRP / DIP)
"""

import os
import shutil
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class CleansingReport:
    total_fixes: int = 0
    vendor_fixes: int = 0
    menu_fixes: int = 0
    price_fixes: int = 0
    backup_path: Optional[str] = None
    details: List[str] = field(default_factory=list)


class DatabaseCleaner:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path).resolve()
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found at {self.db_path}")

    def create_backup(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{self.db_path.name}.backup_pre_clean_{timestamp}"
        backup_path = self.db_path.parent / backup_filename
        shutil.copy2(self.db_path, backup_path)
        return backup_path

    def clean(self, dry_run: bool = False, backup: bool = True) -> CleansingReport:
        report = CleansingReport()

        if backup and not dry_run:
            backup_file = self.create_backup()
            report.backup_path = str(backup_file)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 1. Clean Vendors
            vendor_logs = self._clean_vendors(cursor)
            report.vendor_fixes = len(vendor_logs)
            report.details.extend(vendor_logs)

            # 2. Clean Menus
            menu_logs = self._clean_menus(cursor)
            report.menu_fixes = len(menu_logs)
            report.details.extend(menu_logs)

            # 3. Clean Zero / Null Prices
            price_logs = self._clean_prices(cursor)
            report.price_fixes = len(price_logs)
            report.details.extend(price_logs)

            report.total_fixes = report.vendor_fixes + report.menu_fixes + report.price_fixes

            if dry_run:
                conn.rollback()
            else:
                conn.commit()

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

        return report

    def _clean_vendors(self, cursor: sqlite3.Cursor) -> List[str]:
        logs = []

        # 1.1 Typo 'babu' -> 'Babun'
        cursor.execute("SELECT id, user_name, item_name FROM order_items WHERE vendor = 'babu'")
        for row_id, user_name, item in cursor.fetchall():
            logs.append(f"[Vendor Fix] ID {row_id} ({user_name}): 'babu' -> 'Babun'")
            cursor.execute("UPDATE order_items SET vendor = 'Babun' WHERE id = ?", (row_id,))

        # 1.2 Casing 'Mie ayam' -> 'Mie Ayam'
        cursor.execute("SELECT id, user_name, item_name FROM order_items WHERE vendor = 'Mie ayam'")
        for row_id, user_name, item in cursor.fetchall():
            logs.append(f"[Vendor Fix] ID {row_id} ({user_name}): 'Mie ayam' -> 'Mie Ayam'")
            cursor.execute("UPDATE order_items SET vendor = 'Mie Ayam' WHERE id = ?", (row_id,))

        # 1.3 Misplaced vendor 'Andrean' -> 'Mie Ayam'
        cursor.execute("SELECT id, user_name, item_name FROM order_items WHERE vendor = 'Andrean'")
        for row_id, user_name, item in cursor.fetchall():
            logs.append(f"[Vendor Fix] ID {row_id} ({user_name}): 'Andrean' -> 'Mie Ayam'")
            cursor.execute("UPDATE order_items SET vendor = 'Mie Ayam' WHERE id = ?", (row_id,))

        # 1.4 Misplaced vendor 'Babun' on 'Mie Ayam Pangsit Rebus' -> 'Mie Ayam'
        cursor.execute("SELECT id, user_name, item_name FROM order_items WHERE vendor = 'Babun' AND item_name = 'Mie Ayam Pangsit Rebus'")
        for row_id, user_name, item in cursor.fetchall():
            logs.append(f"[Vendor Fix] ID {row_id} ({user_name}): Babun with Mie Ayam item -> vendor 'Mie Ayam'")
            cursor.execute("UPDATE order_items SET vendor = 'Mie Ayam' WHERE id = ?", (row_id,))

        # 1.5 'gado-gado' as vendor -> vendor 'Kantin'
        cursor.execute("SELECT id, user_name, item_name FROM order_items WHERE vendor = 'gado-gado'")
        for row_id, user_name, item in cursor.fetchall():
            logs.append(f"[Vendor Fix] ID {row_id} ({user_name}): vendor 'gado-gado' -> 'Kantin'")
            cursor.execute("UPDATE order_items SET vendor = 'Kantin' WHERE id = ?", (row_id,))

        # 1.6 'Kantin Mamas' / 'Padang Salero Datuak' / 'Padang Salero Datuak Mamas' -> 'Padang'
        cursor.execute("SELECT id, user_name, item_name FROM order_items WHERE vendor IN ('Kantin Mamas', 'Padang Salero Datuak', 'Padang Salero Datuak Mamas')")
        for row_id, user_name, item in cursor.fetchall():
            logs.append(f"[Vendor Fix] ID {row_id} ({user_name}): vendor '{item}' -> 'Padang'")
            cursor.execute("UPDATE order_items SET vendor = 'Padang' WHERE id = ?", (row_id,))

        # 1.7 'dapur bumbu', 'dapoer', 'dapur' -> 'Dapoer Bumbu'
        cursor.execute("SELECT id, user_name, vendor FROM order_items WHERE LOWER(vendor) IN ('dapur bumbu', 'dapoer', 'dapur')")
        for row_id, user_name, v in cursor.fetchall():
            logs.append(f"[Vendor Fix] ID {row_id} ({user_name}): vendor '{v}' -> 'Dapoer Bumbu'")
            cursor.execute("UPDATE order_items SET vendor = 'Dapoer Bumbu' WHERE id = ?", (row_id,))

        return logs

    def _clean_menus(self, cursor: sqlite3.Cursor) -> List[str]:
        logs = []

        # Mapping variations to canonical names per vendor
        menu_mappings = [
            # Babun
            ("Babun", "Nasi + telor dadar bakar double", "Babun Nasi Telor Dobel"),
            ("Babun", "Nasi telor double", "Babun Nasi Telor Dobel"),
            ("Babun", "Ayam bakar", "Babun Nasi Ayam Bakar"),
            ("Babun", "Nasi Ayam bakar", "Babun Nasi Ayam Bakar"),
            ("Babun", "Nasi ayam bakar", "Babun Nasi Ayam Bakar"),
            ("Babun", "Nasi goreng ayam", "Babun Nasi Goreng Ayam"),
            ("Babun", "Nasi goreng rendang", "Babun Nasi Goreng Rendang"),
            # Mie Ayam
            ("Mie Ayam", "Mie ayam bakso pangsit rebus", "Mie Ayam Bakso (Pangsit Rebus)"),
            # Padang (Salero Datuak Mamas)
            ("Padang", "Nasi Padang Ayam Bakar", "Padang Nasi Ayam Bakar"),
            ("Padang", "Nasi Padang Ayam Gulai", "Padang Nasi Ayam Gulai"),
            ("Padang", "Nasi Padang Rendang", "Padang Nasi Rendang"),
            ("Padang", "Nasi ayam bakar", "Padang Nasi Ayam Bakar"),
            ("Padang", "Nasi rendang", "Padang Nasi Rendang"),
            # Dapoer Bumbu
            ("Dapoer Bumbu", "Nasi Capcay", "Dapoer Bumbu Nasi Capcay"),
            ("Dapoer Bumbu", "Nasi Cap Cay", "Dapoer Bumbu Nasi Capcay"),
            ("Dapoer Bumbu", "Nasi Goreng Bakso", "Dapoer Bumbu Nasi Goreng Bakso"),
            ("Dapoer Bumbu", "Nasi Capcay + Telor Ceplok", "Dapoer Bumbu Nasi Capcay + Telor Ceplok"),
        ]


        for vendor, dirty_name, clean_name in menu_mappings:
            cursor.execute(
                "SELECT id, user_name, price FROM order_items WHERE vendor = ? AND item_name = ?",
                (vendor, dirty_name)
            )
            for row_id, user_name, price in cursor.fetchall():
                logs.append(f"[Menu Fix] ID {row_id} ({user_name}) [{vendor}]: '{dirty_name}' -> '{clean_name}'")
                cursor.execute(
                    "UPDATE order_items SET item_name = ? WHERE id = ?",
                    (clean_name, row_id)
                )

        return logs

    def _clean_prices(self, cursor: sqlite3.Cursor) -> List[str]:
        logs = []

        # Price fixes for known items with price <= 0
        specific_price_fixes = {
            77: 13000,   # Repka: Babun Nasi Telor Dobel
            78: 25000,   # Raka: Kantin Parkiran Nasi Tongseng Ayam (matches session 9 Yosef price)
            205: 13000,  # Shazi: Babun Nasi Telor Dobel
            297: 15000,  # Diky: Babun Nasi Telor + Tahu + Tempe
            321: 23000,  # Raka: Kantin Mamas Nasi Padang Rendang
        }

        for row_id, correct_price in specific_price_fixes.items():
            cursor.execute("SELECT id, user_name, vendor, item_name, price FROM order_items WHERE id = ?", (row_id,))
            row = cursor.fetchone()
            if row and (row[4] is None or row[4] <= 0):
                logs.append(f"[Price Fix] ID {row_id} ({row[1]}) [{row[2]} - {row[3]}]: Rp {row[4]} -> Rp {correct_price:,}")
                cursor.execute("UPDATE order_items SET price = ? WHERE id = ?", (correct_price, row_id))

        # Fallback for any other order with price <= 0: check if item has other orders with price > 0
        cursor.execute("SELECT id, user_name, vendor, item_name, price FROM order_items WHERE price IS NULL OR price <= 0")
        remaining_zeroes = cursor.fetchall()
        for row_id, user_name, vendor, item, price in remaining_zeroes:
            cursor.execute(
                "SELECT price, COUNT(*) as cnt FROM order_items WHERE vendor = ? AND item_name = ? AND price > 0 GROUP BY price ORDER BY cnt DESC LIMIT 1",
                (vendor, item)
            )
            inferred = cursor.fetchone()
            if inferred and inferred[0] > 0:
                new_price = inferred[0]
                logs.append(f"[Price Auto-Infer] ID {row_id} ({user_name}) [{vendor} - {item}]: Rp {price} -> Rp {new_price:,}")
                cursor.execute("UPDATE order_items SET price = ? WHERE id = ?", (new_price, row_id))

        return logs


def clean_database(db_path: str, dry_run: bool = False, backup: bool = True) -> CleansingReport:
    cleaner = DatabaseCleaner(db_path)
    return cleaner.clean(dry_run=dry_run, backup=backup)


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "./data/titip_makan.db"
    dry_run = "--dry-run" in sys.argv
    print(f"Running database cleaner on: {target} (dry_run={dry_run})")
    rep = clean_database(target, dry_run=dry_run, backup=True)
    print(f"Total fixes: {rep.total_fixes}")
    print(f"  Vendor fixes: {rep.vendor_fixes}")
    print(f"  Menu fixes:   {rep.menu_fixes}")
    print(f"  Price fixes:  {rep.price_fixes}")
    if rep.backup_path:
        print(f"Backup created at: {rep.backup_path}")
    print("Fix details:")
    for d in rep.details:
        print(f" - {d}")
