"""Check warehouse consistency against the original CSV."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from build_warehouse import build_warehouse, load_sales

ROOT = Path(__file__).resolve().parents[1]


class WarehouseTests(unittest.TestCase):
    def test_source_and_warehouse_reconcile(self):
        source = load_sales(ROOT / "sales.csv")
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "warehouse.db"
            summary = build_warehouse(ROOT / "sales.csv", database)
            with sqlite3.connect(database) as connection:
                self.assertEqual(summary["sales"], len(source))
                self.assertEqual(
                    summary["revenue"],
                    round(float((source.price * source.quantity).sum()), 2),
                )
                self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM dim_region").fetchone()[0],
                    source.region.nunique(),
                )
                joined_rows = connection.execute("""
                    SELECT COUNT(*)
                    FROM fact_sales AS f
                    JOIN dim_product AS p ON p.product_key = f.product_key
                    JOIN dim_region AS r ON r.region_key = f.region_key
                    JOIN dim_date AS d ON d.date_key = f.date_key
                """).fetchone()[0]
                self.assertEqual(joined_rows, len(source))

    def test_invalid_dates_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "invalid.csv"
            pd.DataFrame([{
                "date": "invalid", "product": "Mouse", "category": "Accessories",
                "price": 30, "quantity": 1, "region": "South",
            }]).to_csv(csv_path, index=False)
            with self.assertRaises(ValueError):
                load_sales(csv_path)


if __name__ == "__main__":
    unittest.main()
