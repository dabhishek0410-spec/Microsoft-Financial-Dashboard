CREATE OR REPLACE TABLE clean_sec_facts AS
WITH standardized AS (
    SELECT
        ticker,
        company_name,
        cik,
        entity_name,
        taxonomy,
        concept,
        label,
        description,
        unit,
        TRY_CAST(fy AS INTEGER) AS reported_fy,
        fp,
        form,
        TRY_CAST(filed AS DATE) AS filed_date,
        TRY_CAST(start_date AS DATE) AS start_date,
        TRY_CAST(end_date AS DATE) AS end_date,
        TRY_CAST(value AS DOUBLE) AS value,
        accession,
        frame
    FROM raw_sec_facts
    WHERE value IS NOT NULL
),

filtered AS (
    SELECT
        *,
        EXTRACT(YEAR FROM end_date) AS fiscal_year,
        CASE
            WHEN start_date IS NULL THEN NULL
            ELSE DATE_DIFF('day', start_date, end_date)
        END AS period_days
    FROM standardized
    WHERE taxonomy = 'us-gaap'
      AND form IN ('10-K', '10-K/A')
      AND end_date IS NOT NULL
      AND EXTRACT(YEAR FROM end_date) BETWEEN 2021 AND 2025
),

mapped AS (
    SELECT
        f.ticker,
        f.company_name,
        f.cik,
        f.entity_name,
        m.standard_metric,
        m.statement,
        f.concept,
        f.label,
        f.unit,
        f.reported_fy,
        f.fiscal_year,
        f.fp,
        f.form,
        f.filed_date,
        f.start_date,
        f.end_date,
        f.period_days,
        f.value,
        f.accession,
        m.priority,

        ROW_NUMBER() OVER (
            PARTITION BY f.ticker, m.standard_metric, f.fiscal_year
            ORDER BY
                m.priority ASC,
                f.filed_date DESC,
                f.end_date DESC,
                f.accession DESC
        ) AS rn

    FROM filtered f
    INNER JOIN fact_map m
        ON f.concept = m.concept
       AND f.unit = m.unit

    WHERE
        (
            m.statement = 'balance_sheet'
            AND f.start_date IS NULL
        )
        OR
        (
            m.statement IN ('income_statement', 'cash_flow')
            AND f.start_date IS NOT NULL
            AND f.period_days BETWEEN 330 AND 390
        )
)

SELECT
    ticker,
    company_name,
    cik,
    entity_name,
    standard_metric,
    statement,
    concept,
    label,
    unit,
    fiscal_year,
    reported_fy,
    fp,
    form,
    filed_date,
    start_date,
    end_date,
    period_days,
    value,
    accession
FROM mapped
WHERE rn = 1;