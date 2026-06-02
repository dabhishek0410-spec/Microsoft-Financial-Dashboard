CREATE OR REPLACE TABLE financial_health_score AS
WITH score_inputs AS (
    SELECT
        ticker,
        company_name,
        fy,

        revenue_growth_yoy,
        gross_margin,
        operating_margin,
        net_margin,
        fcf_margin,
        capex_to_revenue,
        cash_conversion_ratio,
        roe_avg_equity,
        roa_avg_assets,
        current_ratio,
        debt_to_equity,
        net_cash,
        free_cash_flow,
        total_debt
    FROM ratios_annual
),

category_scores AS (
    SELECT
        *,

        /* ----------------------------
           Profitability score
           ---------------------------- */
        (
            CASE
                WHEN operating_margin >= 0.35 THEN 100
                WHEN operating_margin >= 0.25 THEN 85
                WHEN operating_margin >= 0.15 THEN 70
                WHEN operating_margin >= 0.05 THEN 45
                ELSE 20
            END * 0.40
            +
            CASE
                WHEN net_margin >= 0.30 THEN 100
                WHEN net_margin >= 0.20 THEN 85
                WHEN net_margin >= 0.10 THEN 65
                WHEN net_margin >= 0.05 THEN 45
                ELSE 20
            END * 0.35
            +
            CASE
                WHEN roe_avg_equity IS NULL THEN 70
                WHEN roe_avg_equity >= 0.30 THEN 100
                WHEN roe_avg_equity >= 0.20 THEN 85
                WHEN roe_avg_equity >= 0.10 THEN 65
                WHEN roe_avg_equity >= 0.05 THEN 45
                ELSE 20
            END * 0.25
        ) AS profitability_score,

        /* ----------------------------
           Growth score
           ---------------------------- */
        CASE
            WHEN revenue_growth_yoy IS NULL THEN 70
            WHEN revenue_growth_yoy >= 0.15 THEN 100
            WHEN revenue_growth_yoy >= 0.10 THEN 85
            WHEN revenue_growth_yoy >= 0.05 THEN 70
            WHEN revenue_growth_yoy >= 0.00 THEN 50
            ELSE 25
        END AS growth_score,

        /* ----------------------------
           Liquidity score
           ---------------------------- */
        (
            CASE
                WHEN current_ratio >= 1.50 THEN 100
                WHEN current_ratio >= 1.20 THEN 85
                WHEN current_ratio >= 1.00 THEN 70
                WHEN current_ratio >= 0.80 THEN 45
                ELSE 20
            END * 0.60
            +
            CASE
                WHEN net_cash > 0 THEN 100
                WHEN net_cash = 0 THEN 70
                ELSE 40
            END * 0.40
        ) AS liquidity_score,

        /* ----------------------------
           Leverage score
           ---------------------------- */
        (
            CASE
                WHEN debt_to_equity IS NULL THEN 80
                WHEN debt_to_equity <= 0.25 THEN 100
                WHEN debt_to_equity <= 0.50 THEN 85
                WHEN debt_to_equity <= 1.00 THEN 65
                WHEN debt_to_equity <= 2.00 THEN 40
                ELSE 20
            END * 0.70
            +
            CASE
                WHEN net_cash > 0 THEN 100
                WHEN net_cash = 0 THEN 70
                ELSE 40
            END * 0.30
        ) AS leverage_score,

        /* ----------------------------
           Cash-flow quality score
           ---------------------------- */
        (
            CASE
                WHEN fcf_margin >= 0.25 THEN 100
                WHEN fcf_margin >= 0.15 THEN 85
                WHEN fcf_margin >= 0.08 THEN 65
                WHEN fcf_margin >= 0.03 THEN 45
                ELSE 20
            END * 0.45
            +
            CASE
                WHEN cash_conversion_ratio >= 1.20 THEN 100
                WHEN cash_conversion_ratio >= 1.00 THEN 85
                WHEN cash_conversion_ratio >= 0.80 THEN 65
                WHEN cash_conversion_ratio >= 0.50 THEN 45
                ELSE 20
            END * 0.35
            +
            CASE
                WHEN capex_to_revenue <= 0.10 THEN 100
                WHEN capex_to_revenue <= 0.18 THEN 80
                WHEN capex_to_revenue <= 0.25 THEN 60
                WHEN capex_to_revenue <= 0.35 THEN 40
                ELSE 20
            END * 0.20
        ) AS cash_flow_quality_score

    FROM score_inputs
),

final_scores AS (
    SELECT
        *,

        (
            profitability_score * 0.25
            + growth_score * 0.20
            + liquidity_score * 0.15
            + leverage_score * 0.15
            + cash_flow_quality_score * 0.25
        ) AS financial_health_score

    FROM category_scores
)

SELECT
    ticker,
    company_name,
    fy,

    revenue_growth_yoy,
    operating_margin,
    net_margin,
    fcf_margin,
    capex_to_revenue,
    cash_conversion_ratio,
    roe_avg_equity,
    roa_avg_assets,
    current_ratio,
    debt_to_equity,
    net_cash,
    free_cash_flow,

    profitability_score,
    growth_score,
    liquidity_score,
    leverage_score,
    cash_flow_quality_score,
    financial_health_score,

    CASE
        WHEN financial_health_score >= 85 THEN 'Excellent'
        WHEN financial_health_score >= 75 THEN 'Strong'
        WHEN financial_health_score >= 65 THEN 'Healthy'
        WHEN financial_health_score >= 50 THEN 'Moderate'
        ELSE 'Weak'
    END AS financial_health_rating,

    CASE
        WHEN financial_health_score >= 85 THEN 'Microsoft shows excellent financial health, supported by high profitability, strong cash generation, and low balance sheet risk.'
        WHEN financial_health_score >= 75 THEN 'Microsoft shows strong financial health, with solid profitability, cash-flow quality, and manageable financial risk.'
        WHEN financial_health_score >= 65 THEN 'Microsoft appears financially healthy, though some areas should be monitored.'
        WHEN financial_health_score >= 50 THEN 'Microsoft has moderate financial health, with visible strengths but also material concerns.'
        ELSE 'Microsoft shows weak financial health based on the selected scoring framework.'
    END AS analyst_commentary

FROM final_scores
ORDER BY fy;