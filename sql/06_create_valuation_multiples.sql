CREATE OR REPLACE TABLE valuation_multiples AS
WITH latest_financials AS (
    SELECT *
    FROM ratios_annual
    WHERE fy = (
        SELECT MAX(fy)
        FROM ratios_annual
    )
),

latest_price AS (
    SELECT
        ticker,
        date AS price_date,
        adj_close AS latest_price
    FROM market_prices
    WHERE ticker = 'MSFT'
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY ticker
        ORDER BY date DESC
    ) = 1
),

market_data AS (
    SELECT
        ms.ticker,
        ms.as_of_date,
        COALESCE(ms.current_price, lp.latest_price) AS current_price,
        ms.market_cap,
        ms.enterprise_value,
        ms.shares_outstanding,
        ms.trailing_pe,
        ms.forward_pe,
        ms.price_to_sales_ttm,
        ms.beta,
        ms.sector,
        ms.industry,
        ms.long_name
    FROM market_summary ms
    LEFT JOIN latest_price lp
        ON ms.ticker = lp.ticker
)

SELECT
    f.ticker,
    f.company_name,
    f.fy,
    m.as_of_date,

    m.current_price,
    m.market_cap,
    m.enterprise_value,
    m.shares_outstanding,

    f.revenue,
    f.net_income,
    f.operating_income,
    f.free_cash_flow,
    f.diluted_eps,
    f.diluted_shares,

    m.trailing_pe,
    m.forward_pe,
    m.price_to_sales_ttm,

    CASE
        WHEN f.diluted_eps IS NULL OR f.diluted_eps = 0 THEN NULL
        ELSE m.current_price / f.diluted_eps
    END AS calculated_pe,

    CASE
        WHEN f.net_income IS NULL OR f.net_income = 0 THEN NULL
        ELSE m.market_cap / f.net_income
    END AS market_cap_to_net_income,

    CASE
        WHEN f.revenue IS NULL OR f.revenue = 0 THEN NULL
        ELSE m.market_cap / f.revenue
    END AS price_to_sales,

    CASE
        WHEN f.revenue IS NULL OR f.revenue = 0 THEN NULL
        ELSE m.enterprise_value / f.revenue
    END AS ev_to_revenue,

    CASE
        WHEN f.operating_income IS NULL OR f.operating_income = 0 THEN NULL
        ELSE m.enterprise_value / f.operating_income
    END AS ev_to_operating_income,

    CASE
        WHEN f.free_cash_flow IS NULL OR f.free_cash_flow = 0 THEN NULL
        ELSE m.enterprise_value / f.free_cash_flow
    END AS ev_to_fcf,

    CASE
        WHEN m.market_cap IS NULL OR m.market_cap = 0 THEN NULL
        ELSE f.free_cash_flow / m.market_cap
    END AS fcf_yield,

    CASE
        WHEN m.market_cap IS NULL OR m.market_cap = 0 THEN NULL
        ELSE f.net_income / m.market_cap
    END AS earnings_yield,

    m.beta,
    m.sector,
    m.industry,
    m.long_name

FROM latest_financials f
LEFT JOIN market_data m
    ON f.ticker = m.ticker;