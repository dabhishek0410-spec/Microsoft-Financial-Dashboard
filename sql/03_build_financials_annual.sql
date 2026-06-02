CREATE OR REPLACE TABLE financials_annual AS
SELECT
    ticker,
    company_name,
    fiscal_year AS fy,

    MAX(CASE WHEN standard_metric = 'revenue' THEN value END) AS revenue,
    MAX(CASE WHEN standard_metric = 'cost_of_revenue' THEN value END) AS cost_of_revenue,
    MAX(CASE WHEN standard_metric = 'gross_profit' THEN value END) AS gross_profit,
    MAX(CASE WHEN standard_metric = 'operating_income' THEN value END) AS operating_income,
    MAX(CASE WHEN standard_metric = 'income_before_tax' THEN value END) AS income_before_tax,
    MAX(CASE WHEN standard_metric = 'income_tax_expense' THEN value END) AS income_tax_expense,
    MAX(CASE WHEN standard_metric = 'net_income' THEN value END) AS net_income,

    MAX(CASE WHEN standard_metric = 'cash_and_equivalents' THEN value END) AS cash_and_equivalents,
    MAX(CASE WHEN standard_metric = 'short_term_investments' THEN value END) AS short_term_investments,
    MAX(CASE WHEN standard_metric = 'current_assets' THEN value END) AS current_assets,
    MAX(CASE WHEN standard_metric = 'total_assets' THEN value END) AS total_assets,

    MAX(CASE WHEN standard_metric = 'current_liabilities' THEN value END) AS current_liabilities,
    MAX(CASE WHEN standard_metric = 'total_liabilities' THEN value END) AS total_liabilities,
    MAX(CASE WHEN standard_metric = 'stockholders_equity' THEN value END) AS stockholders_equity,

    MAX(CASE WHEN standard_metric = 'current_debt' THEN value END) AS current_debt,
    MAX(CASE WHEN standard_metric = 'long_term_debt' THEN value END) AS long_term_debt,

    MAX(CASE WHEN standard_metric = 'operating_cash_flow' THEN value END) AS operating_cash_flow,
    ABS(MAX(CASE WHEN standard_metric = 'capex' THEN value END)) AS capex,
    ABS(MAX(CASE WHEN standard_metric = 'dividends_paid' THEN value END)) AS dividends_paid,
    ABS(MAX(CASE WHEN standard_metric = 'share_repurchases' THEN value END)) AS share_repurchases,

    MAX(CASE WHEN standard_metric = 'diluted_eps' THEN value END) AS diluted_eps,
    MAX(CASE WHEN standard_metric = 'diluted_shares' THEN value END) AS diluted_shares,

    MAX(CASE WHEN standard_metric = 'operating_cash_flow' THEN value END)
        - ABS(MAX(CASE WHEN standard_metric = 'capex' THEN value END)) AS free_cash_flow

FROM clean_sec_facts
GROUP BY
    ticker,
    company_name,
    fiscal_year
ORDER BY
    fiscal_year;