"""Build a small SQLite star schema from the original synthetic sales CSV."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
REQUIRED_COLUMNS = ("date", "product", "category", "price", "quantity", "region")


def load_sales(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = df.loc[:, REQUIRED_COLUMNS].copy()
    if df.isnull().any().any():
        raise ValueError("The sales file contains missing values")

    dates = pd.to_datetime(df["date"], errors="raise")
    df["date"] = dates.dt.strftime("%Y-%m-%d")

    for column in ("product", "category", "region"):
        df[column] = df[column].astype(str).str.strip()
        if df[column].eq("").any():
            raise ValueError(f"Empty values in {column}")

    for column in ("price", "quantity"):
        df[column] = pd.to_numeric(df[column], errors="raise")
        if (df[column] <= 0).any():
            raise ValueError(f"{column} must be positive")

    if (df["quantity"] % 1 != 0).any():
        raise ValueError("Quantities must be integers")

    df["price"] = df["price"].astype(float)
    df["quantity"] = df["quantity"].astype(int)
    df.insert(0, "sale_id", range(1, len(df) + 1))
    return df


def build_warehouse(csv_path: Path, db_path: Path) -> dict[str, float | int]:
    df = load_sales(csv_path)

    # The original synthetic data includes inconsistent product/category pairings.
    # Keep each unique pair instead of silently changing existing source data.
    products = (
        df[["product", "category"]]
        .drop_duplicates()
        .sort_values(["product", "category"])
        .reset_index(drop=True)
    )
    products.insert(0, "product_key", range(1, len(products) + 1))

    regions = df[["region"]].drop_duplicates().sort_values("region").reset_index(drop=True)
    regions.insert(0, "region_key", range(1, len(regions) + 1))

    dates = pd.DataFrame({"date": sorted(df["date"].unique())})
    parsed_dates = pd.to_datetime(dates["date"])
    dates.insert(0, "date_key", parsed_dates.dt.strftime("%Y%m%d").astype(int))
    dates["year"] = parsed_dates.dt.year
    dates["month"] = parsed_dates.dt.month
    dates["quarter"] = parsed_dates.dt.quarter

    fact = df.merge(products, on=["product", "category"], validate="many_to_one")
    fact = fact.merge(regions, on="region", validate="many_to_one")
    fact = fact.merge(dates[["date", "date_key"]], on="date", validate="many_to_one")
    fact = fact[["sale_id", "date_key", "product_key", "region_key", "price", "quantity"]].copy()
    fact["revenue"] = (fact["price"] * fact["quantity"]).round(2)
    fact = fact.sort_values("sale_id")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript("""
            DROP TABLE IF EXISTS fact_sales;
            DROP TABLE IF EXISTS dim_date;
            DROP TABLE IF EXISTS dim_product;
            DROP TABLE IF EXISTS dim_region;

            CREATE TABLE dim_product (
                product_key INTEGER PRIMARY KEY,
                product TEXT NOT NULL,
                category TEXT NOT NULL,
                UNIQUE(product, category)
            );
            CREATE TABLE dim_region (
                region_key INTEGER PRIMARY KEY,
                region TEXT NOT NULL UNIQUE
            );
            CREATE TABLE dim_date (
                date_key INTEGER PRIMARY KEY,
                date TEXT NOT NULL UNIQUE,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                quarter INTEGER NOT NULL
            );
            CREATE TABLE fact_sales (
                sale_id INTEGER PRIMARY KEY,
                date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
                product_key INTEGER NOT NULL REFERENCES dim_product(product_key),
                region_key INTEGER NOT NULL REFERENCES dim_region(region_key),
                price REAL NOT NULL CHECK(price > 0),
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                revenue REAL NOT NULL CHECK(revenue >= 0)
            );
            CREATE INDEX idx_fact_date ON fact_sales(date_key);
            CREATE INDEX idx_fact_product ON fact_sales(product_key);
            CREATE INDEX idx_fact_region ON fact_sales(region_key);
        """)

        products.to_sql("dim_product", connection, if_exists="append", index=False)
        regions.to_sql("dim_region", connection, if_exists="append", index=False)
        dates.to_sql("dim_date", connection, if_exists="append", index=False)
        fact.to_sql("fact_sales", connection, if_exists="append", index=False)

        summary = {
            "sales": connection.execute("SELECT COUNT(*) FROM fact_sales").fetchone()[0],
            "products": connection.execute("SELECT COUNT(*) FROM dim_product").fetchone()[0],
            "regions": connection.execute("SELECT COUNT(*) FROM dim_region").fetchone()[0],
            "dates": connection.execute("SELECT COUNT(*) FROM dim_date").fetchone()[0],
            "revenue": round(connection.execute("SELECT SUM(revenue) FROM fact_sales").fetchone()[0] or 0, 2),
        }
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(f"Foreign key errors: {violations}")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=BASE_DIR / "sales.csv")
    parser.add_argument("--db", type=Path, default=BASE_DIR / "warehouse.db")
    args = parser.parse_args()

    summary = build_warehouse(args.csv, args.db)
    print("Warehouse created:", args.db)
    for key, value in summary.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
