from pathlib import Path
from datetime import date

import duckdb
import pandas as pd
import yfinance as yf


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
DB_PATH = PROJECT_ROOT / "database" / "finance.duckdb"

MSFT_TICKER = "MSFT"
BENCHMARK_TICKER = "^GSPC"   # S&P 500, useful later for beta
START_DATE = "2020-01-01"
END_DATE = date.today().isoformat()


def clean_yfinance_history(raw_df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """
    Convert yfinance price history into a clean table.
    """

    if raw_df.empty:
        raise ValueError(f"No market price data returned for {ticker}")

    df = raw_df.reset_index()

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    if "date" not in df.columns:
        raise ValueError(f"Date column not found for {ticker}")

    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["ticker"] = ticker

    required_columns = [
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "dividends",
        "stock_splits"
    ]

    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    # If adjusted close is unavailable, use close as fallback
    df["adj_close"] = df["adj_close"].fillna(df["close"])

    df = df[
        [
            "ticker",
            "date",
            "open",
            "high",
            "low",
            "close",
            "adj_close",
            "volume",
            "dividends",
            "stock_splits"
        ]
    ].copy()

    df["daily_return"] = df["adj_close"].pct_change()

    return df


def fetch_price_history(ticker: str) -> pd.DataFrame:
    """
    Fetch daily market price data from yfinance.
    """

    print(f"Fetching price history for {ticker}...")

    stock = yf.Ticker(ticker)

    raw_df = stock.history(
        start=START_DATE,
        end=END_DATE,
        auto_adjust=False,
        actions=True
    )

    return clean_yfinance_history(raw_df, ticker)


def safe_get(dictionary_like, key):
    """
    Safely get values from yfinance fast_info/info objects.
    """

    try:
        return dictionary_like.get(key)
    except Exception:
        return None


def fetch_market_summary(ticker: str) -> pd.DataFrame:
    """
    Fetch current market summary data.

    If yfinance does not provide market cap directly, calculate it as:
    market_cap = current_price * shares_outstanding
    """

    print(f"Fetching market summary for {ticker}...")

    stock = yf.Ticker(ticker)

    try:
        fast_info = stock.fast_info
    except Exception:
        fast_info = {}

    try:
        info = stock.info
    except Exception:
        info = {}

    def first_available(*values):
        """
        Return the first non-null, non-zero value.
        """
        for value in values:
            if value is not None and value != 0:
                return value
        return None

    current_price = first_available(
        safe_get(fast_info, "last_price"),
        info.get("currentPrice"),
        info.get("regularMarketPrice"),
        info.get("previousClose")
    )

    previous_close = first_available(
        safe_get(fast_info, "previous_close"),
        info.get("previousClose")
    )

    shares_outstanding = first_available(
        safe_get(fast_info, "shares"),
        info.get("sharesOutstanding"),
        info.get("impliedSharesOutstanding")
    )

    market_cap = first_available(
        safe_get(fast_info, "market_cap"),
        info.get("marketCap")
    )

    if market_cap is None and current_price is not None and shares_outstanding is not None:
        market_cap = current_price * shares_outstanding

    enterprise_value = first_available(
        info.get("enterpriseValue"),
        safe_get(fast_info, "enterprise_value")
    )

    summary = {
        "ticker": ticker,
        "as_of_date": END_DATE,

        "current_price": current_price,
        "previous_close": previous_close,
        "market_cap": market_cap,
        "shares_outstanding": shares_outstanding,
        "currency": first_available(
            safe_get(fast_info, "currency"),
            info.get("currency")
        ),

        "fifty_two_week_high": first_available(
            safe_get(fast_info, "year_high"),
            info.get("fiftyTwoWeekHigh")
        ),

        "fifty_two_week_low": first_available(
            safe_get(fast_info, "year_low"),
            info.get("fiftyTwoWeekLow")
        ),

        "beta": info.get("beta"),
        "trailing_pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "price_to_sales_ttm": info.get("priceToSalesTrailing12Months"),
        "enterprise_value": enterprise_value,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "long_name": info.get("longName")
    }

    return pd.DataFrame([summary])


def save_to_duckdb(price_df: pd.DataFrame, summary_df: pd.DataFrame) -> None:
    """
    Save market data into DuckDB.
    """

    con = duckdb.connect(str(DB_PATH))

    con.register("price_df", price_df)
    con.register("summary_df", summary_df)

    con.execute("""
        CREATE OR REPLACE TABLE market_prices AS
        SELECT *
        FROM price_df
    """)

    con.execute("""
        CREATE OR REPLACE TABLE market_summary AS
        SELECT *
        FROM summary_df
    """)

    con.close()


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    msft_prices = fetch_price_history(MSFT_TICKER)
    sp500_prices = fetch_price_history(BENCHMARK_TICKER)

    market_prices = pd.concat(
        [msft_prices, sp500_prices],
        ignore_index=True
    )

    market_summary = fetch_market_summary(MSFT_TICKER)

    msft_prices.to_csv(RAW_DIR / "msft_market_prices.csv", index=False)
    sp500_prices.to_csv(RAW_DIR / "sp500_market_prices.csv", index=False)
    market_summary.to_csv(RAW_DIR / "msft_market_summary.csv", index=False)

    save_to_duckdb(market_prices, market_summary)

    print("\nMarket data collection complete.")
    print(f"MSFT price rows:       {len(msft_prices):,}")
    print(f"S&P 500 price rows:    {len(sp500_prices):,}")
    print(f"Combined rows:         {len(market_prices):,}")
    print(f"Saved to database:     {DB_PATH}")

    print("\nLatest MSFT market summary:")
    print(market_summary.T.to_string())


if __name__ == "__main__":
    main()