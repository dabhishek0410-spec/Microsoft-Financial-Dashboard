from pathlib import Path
import duckdb
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DB_PATH = PROJECT_ROOT / "database" / "finance.duckdb"
SQL_FILE = PROJECT_ROOT / "sql" / "05_create_market_metrics.sql"


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}. Run the previous steps first."
        )

    if not SQL_FILE.exists():
        raise FileNotFoundError(
            f"SQL file not found: {SQL_FILE}"
        )

    con = duckdb.connect(str(DB_PATH))

    existing_tables = con.execute("SHOW TABLES").df()["name"].tolist()

    if "market_prices" not in existing_tables:
        raise ValueError(
            "market_prices table not found. Run src/fetch_market_data.py first."
        )

    print(f"Running: {SQL_FILE.name}")

    with open(SQL_FILE, "r", encoding="utf-8") as file:
        sql = file.read()

    con.execute(sql)

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 250)

    print("\nMarket metrics preview:")

    preview = con.execute("""
        SELECT
            ticker,
            start_date,
            end_date,
            trading_days,
            ROUND(start_price, 2) AS start_price,
            ROUND(end_price, 2) AS end_price,
            ROUND(total_return * 100, 2) AS total_return_pct,
            ROUND(annualized_return * 100, 2) AS annualized_return_pct,
            ROUND(annualized_volatility * 100, 2) AS annualized_volatility_pct,
            ROUND(max_drawdown * 100, 2) AS max_drawdown_pct,
            ROUND(beta_vs_sp500, 2) AS beta_vs_sp500,
            ROUND(correlation_vs_sp500, 2) AS correlation_vs_sp500
        FROM market_metrics
        ORDER BY ticker;
    """).df()

    print(preview.to_string(index=False))

    print("\nMSFT market metrics vertically:")

    msft_vertical = con.execute("""
        SELECT
            ticker,
            start_date,
            end_date,
            trading_days,
            ROUND(start_price, 2) AS start_price,
            ROUND(end_price, 2) AS end_price,
            ROUND(total_return * 100, 2) AS total_return_pct,
            ROUND(annualized_return * 100, 2) AS annualized_return_pct,
            ROUND(annualized_volatility * 100, 2) AS annualized_volatility_pct,
            ROUND(max_drawdown * 100, 2) AS max_drawdown_pct,
            ROUND(beta_vs_sp500, 2) AS beta_vs_sp500,
            ROUND(correlation_vs_sp500, 2) AS correlation_vs_sp500
        FROM market_metrics
        WHERE ticker = 'MSFT';
    """).df()

    vertical = msft_vertical.T.reset_index()
    vertical.columns = ["metric", "value"]

    print(vertical.to_string(index=False))

    con.close()

    print("\nMarket metrics table created successfully.")


if __name__ == "__main__":
    main()