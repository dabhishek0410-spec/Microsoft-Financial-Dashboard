import os
from pathlib import Path
from datetime import date, timedelta
import duckdb
import pandas as pd
import yfinance as yf
import requests
from dotenv import load_dotenv

# --------------------------------------------------
# Setup paths & environment
# --------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "database" / "finance.duckdb"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
load_dotenv(PROJECT_ROOT / ".env")

TICKER = "MSFT"
BENCHMARK_TICKER = "^GSPC"
CIK = "0000789019"
COMPANY_NAME = "Microsoft Corporation"

def get_sec_headers() -> dict:
    user_agent = os.getenv("SEC_USER_AGENT")
    if not user_agent:
        raise ValueError(
            "Missing SEC_USER_AGENT in .env. "
            "Example: SEC_USER_AGENT='Your Name your_email@example.com'"
        )
    return {
        "User-Agent": user_agent,
        "Accept-Encoding": "gzip, deflate",
        "Host": "data.sec.gov"
    }

def fetch_company_facts_from_sec(cik: str) -> dict:
    cik = str(cik).zfill(10)
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    response = requests.get(url, headers=get_sec_headers(), timeout=30)
    response.raise_for_status()
    return response.json()

def flatten_company_facts(data: dict) -> pd.DataFrame:
    rows = []
    cik = data.get("cik")
    entity_name = data.get("entityName")
    facts = data.get("facts", {})

    for taxonomy, concepts in facts.items():
        for concept, concept_data in concepts.items():
            label = concept_data.get("label")
            description = concept_data.get("description")
            units = concept_data.get("units", {})

            for unit, observations in units.items():
                for obs in observations:
                    rows.append({
                        "ticker": TICKER,
                        "company_name": COMPANY_NAME,
                        "cik": str(cik).zfill(10),
                        "entity_name": entity_name,
                        "taxonomy": taxonomy,
                        "concept": concept,
                        "label": label,
                        "description": description,
                        "unit": unit,
                        "fy": obs.get("fy"),
                        "fp": obs.get("fp"),
                        "form": obs.get("form"),
                        "filed": obs.get("filed"),
                        "start_date": obs.get("start"),
                        "end_date": obs.get("end"),
                        "value": obs.get("val"),
                        "accession": obs.get("accn"),
                        "frame": obs.get("frame")
                    })
    return pd.DataFrame(rows)

def clean_yfinance_history(raw_df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if raw_df.empty:
        return pd.DataFrame()

    df = raw_df.reset_index()
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["ticker"] = ticker

    required_cols = ["open", "high", "low", "close", "adj_close", "volume", "dividends", "stock_splits"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = None

    df["adj_close"] = df["adj_close"].fillna(df["close"])
    df = df[["ticker", "date", "open", "high", "low", "close", "adj_close", "volume", "dividends", "stock_splits"]].copy()
    df["daily_return"] = df["adj_close"].pct_change()
    return df

def incremental_refresh_sec(con) -> int:
    print("\n--- Starting SEC Incremental Refresh ---")
    tables = con.execute("SHOW TABLES").df()["name"].tolist()
    
    max_filed_date = None
    if "raw_sec_facts" in tables:
        res = con.execute("SELECT MAX(filed) FROM raw_sec_facts").fetchone()
        if res and res[0]:
            max_filed_date = res[0]
            print(f"Current maximum SEC filing date in database: {max_filed_date}")

    print("Fetching SEC company facts...")
    raw_data = fetch_company_facts_from_sec(CIK)
    print("Flattening SEC facts...")
    df = flatten_company_facts(raw_data)

    if max_filed_date:
        df["filed"] = df["filed"].astype(str)
        delta_df = df[df["filed"] > max_filed_date].copy()
        new_rows = len(delta_df)
        if new_rows > 0:
            print(f"Found {new_rows:,} new SEC observations to insert.")
            con.register("delta_sec_df", delta_df)
            con.execute("INSERT INTO raw_sec_facts SELECT * FROM delta_sec_df")
        else:
            print("No new SEC facts since last refresh.")
    else:
        print(f"No existing raw_sec_facts table found. Performing initial full load of {len(df):,} rows...")
        con.register("full_sec_df", df)
        con.execute("CREATE OR REPLACE TABLE raw_sec_facts AS SELECT * FROM full_sec_df")
        new_rows = len(df)

    return new_rows

def incremental_refresh_yfinance(con) -> int:
    print("\n--- Starting yfinance Incremental Refresh ---")
    tables = con.execute("SHOW TABLES").df()["name"].tolist()
    
    tickers = [TICKER, BENCHMARK_TICKER]
    total_new_rows = 0

    for ticker in tickers:
        max_date = None
        if "market_prices" in tables:
            res = con.execute("SELECT MAX(date) FROM market_prices WHERE ticker = ?", [ticker]).fetchone()
            if res and res[0]:
                max_date = pd.to_datetime(res[0]).date()
                print(f"Current maximum market price date for {ticker}: {max_date}")

        today = date.today()
        if max_date:
            start_date = max_date + timedelta(days=1)
        else:
            start_date = date(2020, 1, 1)

        if start_date >= today:
            print(f"Market prices for {ticker} are up to date.")
            continue

        print(f"Fetching {ticker} price history from {start_date} to {today}...")
        stock = yf.Ticker(ticker)
        raw_df = stock.history(
            start=start_date.isoformat(),
            end=today.isoformat(),
            auto_adjust=False,
            actions=True
        )

        if not raw_df.empty:
            clean_df = clean_yfinance_history(raw_df, ticker)
            new_count = len(clean_df)
            print(f"Retrieved {new_count} new price rows for {ticker}.")
            con.register("delta_price_df", clean_df)
            
            if "market_prices" in tables:
                con.execute("INSERT INTO market_prices SELECT * FROM delta_price_df")
            else:
                con.execute("CREATE TABLE market_prices AS SELECT * FROM delta_price_df")
                tables.append("market_prices")
                
            total_new_rows += new_count
        else:
            print(f"No new price updates available for {ticker}.")

    # Fetch live summary metadata unconditionally
    print(f"Updating market summary statistics for {TICKER}...")
    from fetch_market_data import fetch_market_summary
    market_summary = fetch_market_summary(TICKER)
    con.register("live_summary_df", market_summary)
    con.execute("CREATE OR REPLACE TABLE market_summary AS SELECT * FROM live_summary_df")
    
    return total_new_rows

def run_sql_pipeline_files(con):
    print("\n--- Re-Running Core In-Memory Aggregations ---")
    sql_files = [
        PROJECT_ROOT / "sql" / "01_create_fact_map.sql",
        PROJECT_ROOT / "sql" / "02_clean_sec_facts.sql",
        PROJECT_ROOT / "sql" / "03_build_financials_annual.sql",
        PROJECT_ROOT / "sql" / "04_create_ratios_annual.sql",
        PROJECT_ROOT / "sql" / "05_create_market_metrics.sql",
        PROJECT_ROOT / "sql" / "06_create_valuation_multiples.sql",
        PROJECT_ROOT / "sql" / "07_create_financial_health_score.sql",
    ]

    for sql_file in sql_files:
        if not sql_file.exists():
            print(f"Warning: Missing SQL file {sql_file.name}, skipping.")
            continue
        print(f"Executing: {sql_file.name}")
        with open(sql_file, "r", encoding="utf-8") as f:
            con.execute(f.read())

def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    
    try:
        new_sec = incremental_refresh_sec(con)
        new_mkt = incremental_refresh_yfinance(con)
        
        print(f"\n--- Refresh Summary ---")
        print(f"New SEC Facts Appended: {new_sec}")
        print(f"New Market Prices Appended: {new_mkt}")

        # Re-run aggregations only if new data was ingested or tables were rebuilt
        run_sql_pipeline_files(con)
        
        # Run static DCF model as well to keep the database fully aligned
        print("\n--- Updating Pre-calculated DCF Models ---")
        import sys
        sys.path.append(str(PROJECT_ROOT / "src"))
        from run_dcf_model import main as dcf_main
        dcf_main()
        
        print("\nIncremental Refresh Pipeline Execution Successfully Completed.")

    except Exception as e:
        print(f"\nError occurred during refresh: {e}")
        raise e
    finally:
        con.close()

if __name__ == "__main__":
    main()
