CREATE OR REPLACE TABLE fact_map AS
SELECT *
FROM (
    VALUES
        ('revenue', 'income_statement', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'USD', 1),
        ('revenue', 'income_statement', 'Revenues', 'USD', 2),
        ('revenue', 'income_statement', 'SalesRevenueNet', 'USD', 3),

        ('cost_of_revenue', 'income_statement', 'CostOfRevenue', 'USD', 1),
        ('gross_profit', 'income_statement', 'GrossProfit', 'USD', 1),
        ('operating_income', 'income_statement', 'OperatingIncomeLoss', 'USD', 1),
        ('income_before_tax', 'income_statement', 'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest', 'USD', 1),
        ('income_tax_expense', 'income_statement', 'IncomeTaxExpenseBenefit', 'USD', 1),
        ('net_income', 'income_statement', 'NetIncomeLoss', 'USD', 1),

        ('cash_and_equivalents', 'balance_sheet', 'CashAndCashEquivalentsAtCarryingValue', 'USD', 1),
        ('short_term_investments', 'balance_sheet', 'ShortTermInvestments', 'USD', 1),
        ('current_assets', 'balance_sheet', 'AssetsCurrent', 'USD', 1),
        ('total_assets', 'balance_sheet', 'Assets', 'USD', 1),

        ('current_liabilities', 'balance_sheet', 'LiabilitiesCurrent', 'USD', 1),
        ('total_liabilities', 'balance_sheet', 'Liabilities', 'USD', 1),
        ('stockholders_equity', 'balance_sheet', 'StockholdersEquity', 'USD', 1),
        ('stockholders_equity', 'balance_sheet', 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest', 'USD', 2),

        ('current_debt', 'balance_sheet', 'LongTermDebtCurrent', 'USD', 1),
        ('current_debt', 'balance_sheet', 'ShortTermBorrowings', 'USD', 2),
        ('long_term_debt', 'balance_sheet', 'LongTermDebtNoncurrent', 'USD', 1),
        ('long_term_debt', 'balance_sheet', 'LongTermDebt', 'USD', 2),

        ('operating_cash_flow', 'cash_flow', 'NetCashProvidedByUsedInOperatingActivities', 'USD', 1),
        ('capex', 'cash_flow', 'PaymentsToAcquirePropertyPlantAndEquipment', 'USD', 1),
        ('dividends_paid', 'cash_flow', 'PaymentsOfDividends', 'USD', 1),
        ('share_repurchases', 'cash_flow', 'PaymentsForRepurchaseOfCommonStock', 'USD', 1),

        ('diluted_eps', 'income_statement', 'EarningsPerShareDiluted', 'USD/shares', 1),
        ('diluted_shares', 'income_statement', 'WeightedAverageNumberOfDilutedSharesOutstanding', 'shares', 1)
) AS t(
    standard_metric,
    statement,
    concept,
    unit,
    priority
);