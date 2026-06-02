from pathlib import Path
import duckdb
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DB_PATH = PROJECT_ROOT / "database" / "finance.duckdb"
SQL_DIR = PROJECT_ROOT / "sql"


def run_sql_file(con, sql_file: Path) -> None:
    print(f"Running: {sql_file.name}")

    with open(sql_file, "r", encoding="utf-8") as file:
        sql = file.read()

    con.execute(sql)


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}. "
            "Run src/collect_msft_sec_data.py first."
        )

    sql_files = [
        SQL_DIR / "01_create_fact_map.sql",
        SQL_DIR / "02_clean_sec_facts.sql",
        SQL_DIR / "03_build_financials_annual.sql",
        SQL_DIR / "04_create_ratios_annual.sql",
    ]

    con = duckdb.connect(str(DB_PATH))

    for sql_file in sql_files:
        if not sql_file.exists():
            raise FileNotFoundError(f"Missing SQL file: {sql_file}")

        run_sql_file(con, sql_file)

    print("\nTables created:")

    tables = con.execute("SHOW TABLES").df()
    print(tables)

    print("\nRatios annual preview:")

    preview = con.execute("""
        SELECT
            ticker,
            fy,
            ROUND(revenue / 1000000000, 2) AS revenue_bn,
            ROUND(revenue_growth_yoy * 100, 2) AS revenue_growth_pct,
            ROUND(gross_margin * 100, 2) AS gross_margin_pct,
            ROUND(operating_margin * 100, 2) AS operating_margin_pct,
            ROUND(net_margin * 100, 2) AS net_margin_pct,
            ROUND(fcf_margin * 100, 2) AS fcf_margin_pct,
            ROUND(roe_avg_equity * 100, 2) AS roe_pct,
            ROUND(roa_avg_assets * 100, 2) AS roa_pct,
            ROUND(current_ratio, 2) AS current_ratio,
            ROUND(debt_to_equity, 2) AS debt_to_equity,
            ROUND(net_cash / 1000000000, 2) AS net_cash_bn
        FROM ratios_annual
        ORDER BY fy;
    """).df()

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)

    print(preview.to_string(index=False))

    print("\nMissing value check:")

    missing_check = con.execute("""
        SELECT
            fy,
            CASE WHEN revenue IS NULL THEN 'Missing revenue' ELSE 'OK' END AS revenue_check,
            CASE WHEN net_income IS NULL THEN 'Missing net income' ELSE 'OK' END AS net_income_check,
            CASE WHEN total_assets IS NULL THEN 'Missing total assets' ELSE 'OK' END AS assets_check,
            CASE WHEN operating_cash_flow IS NULL THEN 'Missing operating cash flow' ELSE 'OK' END AS ocf_check,
            CASE WHEN capex IS NULL THEN 'Missing capex' ELSE 'OK' END AS capex_check
        FROM financials_annual
        ORDER BY fy;
    """).df()

    print(missing_check.to_string(index=False))

    con.close()

    print("\nSQL pipeline complete.")


if __name__ == "__main__":
    main()