CREATE OR REPLACE TABLE ratios_annual AS
WITH base AS (
    SELECT
        *,
        LAG(revenue) OVER (PARTITION BY ticker ORDER BY fy) AS previous_revenue,
        LAG(net_income) OVER (PARTITION BY ticker ORDER BY fy) AS previous_net_income,
        LAG(total_assets) OVER (PARTITION BY ticker ORDER BY fy) AS previous_total_assets,
        LAG(stockholders_equity) OVER (PARTITION BY ticker ORDER BY fy) AS previous_equity
    FROM financials_annual
),

calculated AS (
    SELECT
        ticker,
        company_name,
        fy,

        revenue,
        gross_profit,
        operating_income,
        income_before_tax,
        income_tax_expense,
        net_income,

        total_assets,
        total_liabilities,
        stockholders_equity,
        current_assets,
        current_liabilities,

        cash_and_equivalents,
        short_term_investments,
        current_debt,
        long_term_debt,

        operating_cash_flow,
        capex,
        free_cash_flow,
        dividends_paid,
        share_repurchases,

        diluted_eps,
        diluted_shares,

        previous_revenue,
        previous_net_income,
        previous_total_assets,
        previous_equity,

        CASE
            WHEN previous_revenue IS NULL OR previous_revenue = 0 THEN NULL
            ELSE revenue / previous_revenue - 1
        END AS revenue_growth_yoy,

        CASE
            WHEN previous_net_income IS NULL OR previous_net_income = 0 THEN NULL
            ELSE net_income / previous_net_income - 1
        END AS net_income_growth_yoy,

        CASE
            WHEN revenue IS NULL OR revenue = 0 THEN NULL
            ELSE gross_profit / revenue
        END AS gross_margin,

        CASE
            WHEN revenue IS NULL OR revenue = 0 THEN NULL
            ELSE operating_income / revenue
        END AS operating_margin,

        CASE
            WHEN revenue IS NULL OR revenue = 0 THEN NULL
            ELSE net_income / revenue
        END AS net_margin,

        CASE
            WHEN revenue IS NULL OR revenue = 0 THEN NULL
            ELSE free_cash_flow / revenue
        END AS fcf_margin,

        CASE
            WHEN revenue IS NULL OR revenue = 0 THEN NULL
            ELSE capex / revenue
        END AS capex_to_revenue,

        CASE
            WHEN net_income IS NULL OR net_income = 0 THEN NULL
            ELSE operating_cash_flow / net_income
        END AS cash_conversion_ratio,

        CASE
            WHEN income_before_tax IS NULL OR income_before_tax = 0 THEN NULL
            ELSE income_tax_expense / income_before_tax
        END AS effective_tax_rate,

        CASE
            WHEN previous_total_assets IS NULL THEN NULL
            ELSE net_income / ((total_assets + previous_total_assets) / 2)
        END AS roa_avg_assets,

        CASE
            WHEN previous_equity IS NULL THEN NULL
            ELSE net_income / ((stockholders_equity + previous_equity) / 2)
        END AS roe_avg_equity,

        CASE
            WHEN total_assets IS NULL OR total_assets = 0 THEN NULL
            ELSE net_income / total_assets
        END AS roa_ending_assets,

        CASE
            WHEN stockholders_equity IS NULL OR stockholders_equity = 0 THEN NULL
            ELSE net_income / stockholders_equity
        END AS roe_ending_equity,

        CASE
            WHEN current_liabilities IS NULL OR current_liabilities = 0 THEN NULL
            ELSE current_assets / current_liabilities
        END AS current_ratio,

        COALESCE(current_debt, 0) + COALESCE(long_term_debt, 0) AS total_debt,

        CASE
            WHEN stockholders_equity IS NULL OR stockholders_equity = 0 THEN NULL
            ELSE (COALESCE(current_debt, 0) + COALESCE(long_term_debt, 0)) / stockholders_equity
        END AS debt_to_equity,

        COALESCE(cash_and_equivalents, 0)
            + COALESCE(short_term_investments, 0)
            - COALESCE(current_debt, 0)
            - COALESCE(long_term_debt, 0) AS net_cash,

        CASE
            WHEN operating_income IS NULL OR operating_income = 0 THEN NULL
            ELSE free_cash_flow / operating_income
        END AS fcf_to_operating_income

    FROM base
)

SELECT *
FROM calculated
ORDER BY fy;