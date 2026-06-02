from pathlib import Path
import duckdb
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DB_PATH = PROJECT_ROOT / "database" / "finance.duckdb"
SQL_FILE = PROJECT_ROOT / "sql" / "07_create_financial_health_score.sql"


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

    if "ratios_annual" not in tables:
        raise ValueError(
            "ratios_annual table not found. Run src/run_sql_pipeline.py first."
        )

    print(f"Running: {SQL_FILE.name}")

    with open(SQL_FILE, "r", encoding="utf-8") as file:
        sql = file.read()

    con.execute(sql)

    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 250)

    print("\nFinancial health score preview:")

    preview = con.execute("""
        SELECT
            ticker,
            fy,
            ROUND(profitability_score, 2) AS profitability_score,
            ROUND(growth_score, 2) AS growth_score,
            ROUND(liquidity_score, 2) AS liquidity_score,
            ROUND(leverage_score, 2) AS leverage_score,
            ROUND(cash_flow_quality_score, 2) AS cash_flow_quality_score,
            ROUND(financial_health_score, 2) AS financial_health_score,
            financial_health_rating
        FROM financial_health_score
        ORDER BY fy;
    """).df()

    print(preview.to_string(index=False))

    print("\nLatest year financial health score vertically:")

    latest = con.execute("""
        SELECT
            ticker,
            fy,
            ROUND(operating_margin * 100, 2) AS operating_margin_pct,
            ROUND(net_margin * 100, 2) AS net_margin_pct,
            ROUND(fcf_margin * 100, 2) AS fcf_margin_pct,
            ROUND(capex_to_revenue * 100, 2) AS capex_to_revenue_pct,
            ROUND(roe_avg_equity * 100, 2) AS roe_pct,
            ROUND(current_ratio, 2) AS current_ratio,
            ROUND(debt_to_equity, 2) AS debt_to_equity,
            ROUND(net_cash / 1000000000, 2) AS net_cash_bn,
            ROUND(profitability_score, 2) AS profitability_score,
            ROUND(growth_score, 2) AS growth_score,
            ROUND(liquidity_score, 2) AS liquidity_score,
            ROUND(leverage_score, 2) AS leverage_score,
            ROUND(cash_flow_quality_score, 2) AS cash_flow_quality_score,
            ROUND(financial_health_score, 2) AS financial_health_score,
            financial_health_rating,
            analyst_commentary
        FROM financial_health_score
        WHERE fy = (
            SELECT MAX(fy)
            FROM financial_health_score
        );
    """).df()

    print(latest.T.to_string())

    con.close()

    print("\nfinancial_health_score table created successfully.")


if __name__ == "__main__":
    main()