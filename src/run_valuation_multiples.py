from pathlib import Path
import duckdb
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DB_PATH = PROJECT_ROOT / "database" / "finance.duckdb"
SQL_FILE = PROJECT_ROOT / "sql" / "06_create_valuation_multiples.sql"


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}. Run previous steps first."
        )

    if not SQL_FILE.exists():
        raise FileNotFoundError(
            f"SQL file not found: {SQL_FILE}"
        )

    con = duckdb.connect(str(DB_PATH))

    tables = con.execute("SHOW TABLES").df()["name"].tolist()

    required_tables = [
        "ratios_annual",
        "market_prices",
        "market_summary"
    ]

    for table in required_tables:
        if table not in tables:
            raise ValueError(
                f"{table} table not found. Complete the previous steps first."
            )

    print(f"Running: {SQL_FILE.name}")

    with open(SQL_FILE, "r", encoding="utf-8") as file:
        sql = file.read()

    con.execute(sql)

    pd.set_option("display.max_rows", None)
    pd.set_option("display.width", 250)

    df = con.execute("""
        SELECT
            ticker,
            fy,
            ROUND(current_price, 2) AS current_price,
            ROUND(market_cap / 1000000000, 2) AS market_cap_bn,
            ROUND(enterprise_value / 1000000000, 2) AS enterprise_value_bn,
            ROUND(calculated_pe, 2) AS calculated_pe,
            ROUND(price_to_sales, 2) AS price_to_sales,
            ROUND(ev_to_revenue, 2) AS ev_to_revenue,
            ROUND(ev_to_fcf, 2) AS ev_to_fcf,
            ROUND(fcf_yield * 100, 2) AS fcf_yield_pct,
            ROUND(earnings_yield * 100, 2) AS earnings_yield_pct,
            ROUND(beta, 2) AS beta
        FROM valuation_multiples;
    """).df()

    print("\nValuation multiples vertically:")
    print(df.T.to_string())

    con.close()

    print("\nvaluation_multiples table created successfully.")


if __name__ == "__main__":
    main()