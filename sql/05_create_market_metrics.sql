CREATE OR REPLACE TABLE market_metrics AS
WITH price_base AS (
    SELECT
        ticker,
        CAST(date AS DATE) AS price_date,
        CAST(adj_close AS DOUBLE) AS adj_close,
        CAST(daily_return AS DOUBLE) AS daily_return
    FROM market_prices
    WHERE adj_close IS NOT NULL
),

start_end AS (
    SELECT
        ticker,
        MIN(price_date) AS start_date,
        MAX(price_date) AS end_date
    FROM price_base
    GROUP BY ticker
),

start_end_prices AS (
    SELECT
        s.ticker,
        s.start_date,
        s.end_date,
        p1.adj_close AS start_price,
        p2.adj_close AS end_price
    FROM start_end s
    LEFT JOIN price_base p1
        ON s.ticker = p1.ticker
       AND s.start_date = p1.price_date
    LEFT JOIN price_base p2
        ON s.ticker = p2.ticker
       AND s.end_date = p2.price_date
),

return_stats AS (
    SELECT
        ticker,
        COUNT(daily_return) AS trading_days,
        AVG(daily_return) AS avg_daily_return,
        STDDEV_SAMP(daily_return) AS daily_volatility
    FROM price_base
    WHERE daily_return IS NOT NULL
    GROUP BY ticker
),

drawdown_base AS (
    SELECT
        ticker,
        price_date,
        adj_close,
        MAX(adj_close) OVER (
            PARTITION BY ticker
            ORDER BY price_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS running_peak
    FROM price_base
),

drawdown_stats AS (
    SELECT
        ticker,
        MIN((adj_close / running_peak) - 1) AS max_drawdown
    FROM drawdown_base
    GROUP BY ticker
),

benchmark_returns AS (
    SELECT
        m.price_date,
        m.daily_return AS msft_return,
        b.daily_return AS benchmark_return
    FROM price_base m
    INNER JOIN price_base b
        ON m.price_date = b.price_date
    WHERE m.ticker = 'MSFT'
      AND b.ticker = '^GSPC'
      AND m.daily_return IS NOT NULL
      AND b.daily_return IS NOT NULL
),

beta_stats AS (
    SELECT
        'MSFT' AS ticker,
        COVAR_SAMP(msft_return, benchmark_return)
            / NULLIF(VAR_SAMP(benchmark_return), 0) AS beta_vs_sp500,
        CORR(msft_return, benchmark_return) AS correlation_vs_sp500
    FROM benchmark_returns
)

SELECT
    se.ticker,
    se.start_date,
    se.end_date,
    DATE_DIFF('day', se.start_date, se.end_date) AS calendar_days,
    rs.trading_days,
    se.start_price,
    se.end_price,

    CASE
        WHEN se.start_price IS NULL OR se.start_price = 0 THEN NULL
        ELSE se.end_price / se.start_price - 1
    END AS total_return,

    CASE
        WHEN se.start_price IS NULL
          OR se.start_price = 0
          OR DATE_DIFF('day', se.start_date, se.end_date) = 0
        THEN NULL
        ELSE POWER(
            se.end_price / se.start_price,
            365.25 / DATE_DIFF('day', se.start_date, se.end_date)
        ) - 1
    END AS annualized_return,

    rs.daily_volatility * SQRT(252) AS annualized_volatility,
    ds.max_drawdown,
    rs.avg_daily_return * 252 AS average_annualized_daily_return,
    bs.beta_vs_sp500,
    bs.correlation_vs_sp500

FROM start_end_prices se
LEFT JOIN return_stats rs
    ON se.ticker = rs.ticker
LEFT JOIN drawdown_stats ds
    ON se.ticker = ds.ticker
LEFT JOIN beta_stats bs
    ON se.ticker = bs.ticker
ORDER BY se.ticker;