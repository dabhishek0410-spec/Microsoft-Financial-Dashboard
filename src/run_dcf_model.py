from pathlib import Path
import duckdb
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DB_PATH = PROJECT_ROOT / "database" / "finance.duckdb"
ASSUMPTIONS_PATH = PROJECT_ROOT / "data" / "raw" / "dcf_assumptions.csv"


def load_latest_financials(con) -> dict:
    """
    Load latest Microsoft financials from ratios_annual.
    """

    df = con.execute("""
        SELECT *
        FROM ratios_annual
        WHERE fy = (
            SELECT MAX(fy)
            FROM ratios_annual
        )
    """).df()

    if df.empty:
        raise ValueError("No data found in ratios_annual.")

    return df.iloc[0].to_dict()


def load_market_data(con) -> dict:
    """
    Load current market price and valuation data.
    """

    df = con.execute("""
        SELECT *
        FROM valuation_multiples
        LIMIT 1
    """).df()

    if df.empty:
        raise ValueError("No data found in valuation_multiples.")

    return df.iloc[0].to_dict()


def load_assumptions(con) -> pd.DataFrame:
    """
    Load DCF assumptions from CSV and save them into DuckDB.
    """

    if not ASSUMPTIONS_PATH.exists():
        raise FileNotFoundError(
            f"DCF assumptions file not found: {ASSUMPTIONS_PATH}"
        )

    assumptions = pd.read_csv(ASSUMPTIONS_PATH)

    con.register("assumptions_df", assumptions)

    con.execute("""
        CREATE OR REPLACE TABLE dcf_assumptions AS
        SELECT *
        FROM assumptions_df
    """)

    return assumptions


def run_single_dcf(base_financials: dict, market_data: dict, assumptions: dict) -> tuple[pd.DataFrame, dict]:
    """
    Run one DCF scenario.
    """

    scenario = assumptions["scenario"]

    base_year = int(base_financials["fy"])
    revenue = float(base_financials["revenue"])

    cash_and_equivalents = float(base_financials.get("cash_and_equivalents") or 0)
    short_term_investments = float(base_financials.get("short_term_investments") or 0)
    current_debt = float(base_financials.get("current_debt") or 0)
    long_term_debt = float(base_financials.get("long_term_debt") or 0)

    net_cash = (
        cash_and_equivalents
        + short_term_investments
        - current_debt
        - long_term_debt
    )

    diluted_shares = base_financials.get("diluted_shares")

    if diluted_shares is None or diluted_shares == 0:
        diluted_shares = market_data.get("shares_outstanding")

    diluted_shares = float(diluted_shares)

    current_price = float(market_data.get("current_price") or 0)

    growth_rates = [
        float(assumptions["revenue_growth_y1"]),
        float(assumptions["revenue_growth_y2"]),
        float(assumptions["revenue_growth_y3"]),
        float(assumptions["revenue_growth_y4"]),
        float(assumptions["revenue_growth_y5"]),
    ]

    operating_margin = float(assumptions["operating_margin"])
    tax_rate = float(assumptions["tax_rate"])
    da_pct_revenue = float(assumptions["da_pct_revenue"])
    capex_pct_revenue = float(assumptions["capex_pct_revenue"])
    nwc_pct_revenue = float(assumptions["nwc_pct_revenue"])
    wacc = float(assumptions["wacc"])
    terminal_growth = float(assumptions["terminal_growth"])

    forecast_rows = []

    for year_number, growth in enumerate(growth_rates, start=1):
        forecast_year = base_year + year_number

        revenue = revenue * (1 + growth)
        ebit = revenue * operating_margin
        nopat = ebit * (1 - tax_rate)

        depreciation_amortization = revenue * da_pct_revenue
        capex = revenue * capex_pct_revenue
        change_in_working_capital = revenue * nwc_pct_revenue

        free_cash_flow = (
            nopat
            + depreciation_amortization
            - capex
            - change_in_working_capital
        )

        discount_factor = 1 / ((1 + wacc) ** year_number)
        pv_fcf = free_cash_flow * discount_factor

        forecast_rows.append({
            "scenario": scenario,
            "forecast_year": forecast_year,
            "year_number": year_number,
            "revenue": revenue,
            "revenue_growth": growth,
            "ebit": ebit,
            "nopat": nopat,
            "depreciation_amortization": depreciation_amortization,
            "capex": capex,
            "change_in_working_capital": change_in_working_capital,
            "free_cash_flow": free_cash_flow,
            "discount_factor": discount_factor,
            "pv_fcf": pv_fcf
        })

    forecast_df = pd.DataFrame(forecast_rows)

    final_year_fcf = forecast_df["free_cash_flow"].iloc[-1]

    terminal_value = (
        final_year_fcf
        * (1 + terminal_growth)
        / (wacc - terminal_growth)
    )

    pv_terminal_value = terminal_value / ((1 + wacc) ** 5)

    pv_forecast_fcf = forecast_df["pv_fcf"].sum()

    enterprise_value = pv_forecast_fcf + pv_terminal_value

    equity_value = enterprise_value + net_cash

    implied_share_price = equity_value / diluted_shares

    revenue_cagr = (forecast_df["revenue"].iloc[-1] / float(base_financials["revenue"])) ** (1 / 5) - 1
    fcf_cagr = (
        forecast_df["free_cash_flow"].iloc[-1] / float(base_financials["free_cash_flow"])
    ) ** (1 / 5) - 1
    final_fcf_margin = forecast_df["free_cash_flow"].iloc[-1] / forecast_df["revenue"].iloc[-1]
    terminal_value_pct_ev = pv_terminal_value / enterprise_value

    upside_downside = None

    if current_price and current_price != 0:
        upside_downside = implied_share_price / current_price - 1

    summary = {
        "scenario": scenario,
        "base_year": base_year,
        "current_price": current_price,
        "base_revenue": base_financials["revenue"],
        "base_free_cash_flow": base_financials["free_cash_flow"],
        "net_cash": net_cash,
        "diluted_shares": diluted_shares,
        "wacc": wacc,
        "terminal_growth": terminal_growth,
        "pv_forecast_fcf": pv_forecast_fcf,
        "terminal_value": terminal_value,
        "pv_terminal_value": pv_terminal_value,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "implied_share_price": implied_share_price,
        "upside_downside": upside_downside,
        "forecast_revenue_cagr": revenue_cagr,
        "forecast_fcf_cagr": fcf_cagr,
        "final_year_fcf_margin": final_fcf_margin,
        "terminal_value_pct_ev": terminal_value_pct_ev
    }

    return forecast_df, summary


def valuation_view(upside_downside) -> str:
    if upside_downside is None or pd.isna(upside_downside):
        return "Insufficient data"
    if upside_downside >= 0.15:
        return "Model-implied upside"
    if upside_downside <= -0.15:
        return "Model-implied downside"
    return "Close to model value"


def build_analyst_summary(
    base_financials: dict,
    market_data: dict,
    summary_df: pd.DataFrame,
    sensitivity_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build a short rule-based analyst memo from the model outputs.
    This is intentionally deterministic and evidence-based.
    """

    base = summary_df[summary_df["scenario"] == "Base"].iloc[0]
    bull = summary_df[summary_df["scenario"] == "Bull"].iloc[0]
    bear = summary_df[summary_df["scenario"] == "Bear"].iloc[0]

    current_price = base["current_price"]
    operating_margin = base_financials.get("operating_margin")
    fcf_margin = base_financials.get("fcf_margin")
    revenue_growth = base_financials.get("revenue_growth_yoy")
    capex_to_revenue = base_financials.get("capex_to_revenue")
    net_cash = base_financials.get("net_cash")

    sensitivity_min = sensitivity_df["implied_share_price"].min()
    sensitivity_max = sensitivity_df["implied_share_price"].max()

    rows = [
        {
            "section": "Valuation View",
            "takeaway": valuation_view(base["upside_downside"]),
            "evidence": (
                f"Base DCF implied price is ${base['implied_share_price']:,.2f} versus "
                f"current price of ${current_price:,.2f}, implying {base['upside_downside'] * 100:,.2f}%."
            ),
            "analyst_note": (
                "Read this as an assumption-based model output, not a price prediction. "
                "The result depends heavily on WACC, terminal growth, margin durability, and capex intensity."
            ),
        },
        {
            "section": "Business Quality",
            "takeaway": "High profitability and cash generation",
            "evidence": (
                f"Latest operating margin is {operating_margin * 100:,.2f}% and "
                f"FCF margin is {fcf_margin * 100:,.2f}%."
            ),
            "analyst_note": (
                "Microsoft's core financial profile remains strong; the harder question is how much of that quality "
                "is already reflected in the market price."
            ),
        },
        {
            "section": "Growth and Reinvestment",
            "takeaway": "AI/cloud capex must convert into durable growth",
            "evidence": (
                f"Latest revenue growth is {revenue_growth * 100:,.2f}% and capex/revenue is "
                f"{capex_to_revenue * 100:,.2f}%."
            ),
            "analyst_note": (
                "Rising infrastructure investment is not automatically negative, but it raises the burden of proof "
                "for future revenue growth and operating leverage."
            ),
        },
        {
            "section": "Balance Sheet",
            "takeaway": "Financial flexibility remains a strength",
            "evidence": f"Latest net cash is ${net_cash / 1_000_000_000:,.2f}B.",
            "analyst_note": (
                "Balance sheet strength gives Microsoft room to invest through the AI cycle without relying heavily "
                "on financial leverage."
            ),
        },
        {
            "section": "Scenario Range",
            "takeaway": "Valuation is sensitive across cases",
            "evidence": (
                f"Bear, Base, and Bull implied prices are ${bear['implied_share_price']:,.2f}, "
                f"${base['implied_share_price']:,.2f}, and ${bull['implied_share_price']:,.2f}."
            ),
            "analyst_note": (
                "The spread between cases shows how much the thesis depends on cloud/AI monetization, margins, "
                "discount rates, and terminal assumptions."
            ),
        },
        {
            "section": "Sensitivity",
            "takeaway": "Discount-rate assumptions matter materially",
            "evidence": (
                f"The sensitivity grid ranges from ${sensitivity_min:,.2f} to ${sensitivity_max:,.2f} per share."
            ),
            "analyst_note": (
                "A premium-quality business can still look expensive when discount rates or terminal growth assumptions move."
            ),
        },
    ]

    return pd.DataFrame(rows)


def run_sensitivity(base_financials: dict, market_data: dict, base_assumptions: dict) -> pd.DataFrame:
    """
    Create WACC vs terminal growth sensitivity table for the base scenario.
    """

    wacc_values = [0.075, 0.080, 0.085, 0.090, 0.095, 0.100]
    terminal_growth_values = [0.015, 0.020, 0.025, 0.030, 0.035]

    rows = []

    for wacc in wacc_values:
        for terminal_growth in terminal_growth_values:
            assumptions = dict(base_assumptions)
            assumptions["wacc"] = wacc
            assumptions["terminal_growth"] = terminal_growth
            assumptions["scenario"] = "Sensitivity"

            _, summary = run_single_dcf(
                base_financials,
                market_data,
                assumptions
            )

            rows.append({
                "wacc": wacc,
                "terminal_growth": terminal_growth,
                "implied_share_price": summary["implied_share_price"],
                "enterprise_value": summary["enterprise_value"],
                "equity_value": summary["equity_value"]
            })

    return pd.DataFrame(rows)


def save_outputs(
    con,
    forecast_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    sensitivity_df: pd.DataFrame,
    analyst_summary_df: pd.DataFrame,
) -> None:
    """
    Save DCF outputs into DuckDB.
    """

    con.register("dcf_forecast_df", forecast_df)
    con.register("dcf_summary_df", summary_df)
    con.register("dcf_sensitivity_df", sensitivity_df)
    con.register("analyst_summary_df", analyst_summary_df)

    con.execute("""
        CREATE OR REPLACE TABLE dcf_forecast AS
        SELECT *
        FROM dcf_forecast_df
    """)

    con.execute("""
        CREATE OR REPLACE TABLE dcf_summary AS
        SELECT *
        FROM dcf_summary_df
    """)

    con.execute("""
        CREATE OR REPLACE TABLE dcf_sensitivity AS
        SELECT *
        FROM dcf_sensitivity_df
    """)

    con.execute("""
        CREATE OR REPLACE TABLE analyst_summary AS
        SELECT *
        FROM analyst_summary_df
    """)


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}. Run previous steps first."
        )

    con = duckdb.connect(str(DB_PATH))

    tables = con.execute("SHOW TABLES").df()["name"].tolist()

    required_tables = [
        "ratios_annual",
        "valuation_multiples"
    ]

    for table in required_tables:
        if table not in tables:
            raise ValueError(
                f"{table} table not found. Complete previous steps first."
            )

    base_financials = load_latest_financials(con)
    market_data = load_market_data(con)
    assumptions_df = load_assumptions(con)

    all_forecasts = []
    all_summaries = []

    for _, assumption_row in assumptions_df.iterrows():
        assumption_dict = assumption_row.to_dict()

        forecast_df, summary = run_single_dcf(
            base_financials,
            market_data,
            assumption_dict
        )

        all_forecasts.append(forecast_df)
        all_summaries.append(summary)

    final_forecast_df = pd.concat(all_forecasts, ignore_index=True)
    final_summary_df = pd.DataFrame(all_summaries)

    base_assumptions = assumptions_df[
        assumptions_df["scenario"] == "Base"
    ].iloc[0].to_dict()

    sensitivity_df = run_sensitivity(
        base_financials,
        market_data,
        base_assumptions
    )

    analyst_summary_df = build_analyst_summary(
        base_financials,
        market_data,
        final_summary_df,
        sensitivity_df
    )

    save_outputs(
        con,
        final_forecast_df,
        final_summary_df,
        sensitivity_df,
        analyst_summary_df
    )

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 250)

    print("\nDCF summary:")

    summary_preview = con.execute("""
        SELECT
            scenario,
            ROUND(current_price, 2) AS current_price,
            ROUND(enterprise_value / 1000000000, 2) AS enterprise_value_bn,
            ROUND(equity_value / 1000000000, 2) AS equity_value_bn,
            ROUND(implied_share_price, 2) AS implied_share_price,
            ROUND(upside_downside * 100, 2) AS upside_downside_pct,
            ROUND(wacc * 100, 2) AS wacc_pct,
            ROUND(terminal_growth * 100, 2) AS terminal_growth_pct
        FROM dcf_summary
        ORDER BY
            CASE
                WHEN scenario = 'Bear' THEN 1
                WHEN scenario = 'Base' THEN 2
                WHEN scenario = 'Bull' THEN 3
                ELSE 4
            END
    """).df()

    print(summary_preview.to_string(index=False))

    print("\nBase scenario forecast:")

    base_forecast = con.execute("""
        SELECT
            forecast_year,
            ROUND(revenue / 1000000000, 2) AS revenue_bn,
            ROUND(revenue_growth * 100, 2) AS revenue_growth_pct,
            ROUND(ebit / 1000000000, 2) AS ebit_bn,
            ROUND(free_cash_flow / 1000000000, 2) AS free_cash_flow_bn,
            ROUND(pv_fcf / 1000000000, 2) AS pv_fcf_bn
        FROM dcf_forecast
        WHERE scenario = 'Base'
        ORDER BY forecast_year
    """).df()

    print(base_forecast.to_string(index=False))

    print("\nDCF tables created successfully:")
    print("- dcf_assumptions")
    print("- dcf_forecast")
    print("- dcf_summary")
    print("- dcf_sensitivity")
    print("- analyst_summary")

    con.close()


if __name__ == "__main__":
    main()
