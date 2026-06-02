from html import escape
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.io as pio


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "database" / "finance.duckdb"
DOCS_DIR = PROJECT_ROOT / "docs"
OUTPUT_PATH = DOCS_DIR / "index.html"


COLORWAY = ["#5ED6C6", "#E8C46A", "#8AB4F8", "#F29A8A", "#B6A6FF"]


def load_table(con: duckdb.DuckDBPyConnection, table_name: str) -> pd.DataFrame:
    return con.execute(f"SELECT * FROM {table_name}").df()


def format_billions(value) -> str:
    if pd.isna(value):
        return "N/A"
    return f"${value / 1_000_000_000:,.2f}B"


def format_pct(value) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{value * 100:,.2f}%"


def format_number(value) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{value:,.2f}"


def format_date(value) -> str:
    if pd.isna(value):
        return "N/A"
    return pd.to_datetime(value).strftime("%Y-%m-%d")


def valuation_view(upside_downside) -> str:
    if pd.isna(upside_downside):
        return "Insufficient data"
    if upside_downside >= 0.15:
        return "Model-Implied Upside"
    if upside_downside <= -0.15:
        return "Model-Implied Downside"
    return "Close to Model Value"


def chart_html(fig, include_plotlyjs=False) -> str:
    chart_title = fig.layout.title.text or ""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=COLORWAY,
        font=dict(color="#D6E4E2", family="Inter, Arial, sans-serif"),
        title=None,
        margin=dict(l=42, r=24, t=82, b=44),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.08,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=12),
        ),
        legend_title_text="",
    )
    fig.update_xaxes(
        gridcolor="rgba(214,228,226,0.10)",
        zerolinecolor="rgba(214,228,226,0.18)",
        linecolor="rgba(214,228,226,0.20)",
    )
    fig.update_yaxes(
        gridcolor="rgba(214,228,226,0.10)",
        zerolinecolor="rgba(214,228,226,0.18)",
        linecolor="rgba(214,228,226,0.20)",
    )
    fig.update_traces(
        marker=dict(size=7),
        line=dict(width=3),
        selector=dict(type="scatter"),
    )
    plot = pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs=include_plotlyjs,
        config={"displayModeBar": False, "responsive": True},
    )
    return (
        f"<div class='chart-title'>{escape(chart_title)}</div>"
        f"<div class='chart-plot'>{plot}</div>"
    )


def rename_traces(fig, name_map: dict):
    fig.for_each_trace(lambda trace: trace.update(name=name_map.get(trace.name, trace.name)))
    return fig


def table_html(df: pd.DataFrame) -> str:
    return df.to_html(index=False, classes="data-table", border=0, escape=False)


def analyst_summary_html(df: pd.DataFrame) -> str:
    cards = []
    for _, row in df.iterrows():
        cards.append(
            """
            <article class="summary-card">
                <div class="summary-section">{section}</div>
                <h3>{takeaway}</h3>
                <div class="summary-block">
                    <span>Evidence</span>
                    <p>{evidence}</p>
                </div>
                <div class="summary-block summary-note">
                    <span>Analyst Note</span>
                    <p>{note}</p>
                </div>
            </article>
            """.format(
                section=escape(str(row.get("Section", ""))),
                takeaway=escape(str(row.get("Takeaway", ""))),
                evidence=escape(str(row.get("Evidence", ""))),
                note=escape(str(row.get("Analyst Note", ""))),
            )
        )
    return f"<div class='summary-grid'>{''.join(cards)}</div>"


def metric_card(label: str, value: str, note: str = "") -> str:
    note_html = f"<div class='metric-note'>{note}</div>" if note else ""
    return (
        "<div class='metric-card'>"
        f"<div class='metric-label'>{label}</div>"
        f"<div class='metric-value'>{value}</div>"
        f"{note_html}"
        "</div>"
    )


def tab_panel(title: str, body: str, panel_id: str, active: bool = False) -> str:
    active_class = " active" if active else ""
    return f"<section id='{panel_id}' class='tab-panel{active_class}'><h2>{title}</h2>{body}</section>"


def build_dashboard() -> str:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    con = duckdb.connect(str(DB_PATH), read_only=True)

    financials = load_table(con, "financials_annual")
    ratios = load_table(con, "ratios_annual")
    market_summary = load_table(con, "market_summary")
    market_metrics = load_table(con, "market_metrics")
    valuation = load_table(con, "valuation_multiples")
    dcf_summary = load_table(con, "dcf_summary")
    dcf_forecast = load_table(con, "dcf_forecast")
    dcf_sensitivity = load_table(con, "dcf_sensitivity")
    dcf_assumptions = load_table(con, "dcf_assumptions")
    health = load_table(con, "financial_health_score")
    analyst_summary = load_table(con, "analyst_summary")
    source_audit = con.execute(
        """
        SELECT
            COUNT(*) AS raw_sec_rows,
            COUNT(DISTINCT concept) AS sec_concepts
        FROM raw_sec_facts
        """
    ).df()

    con.close()

    latest_financials = financials.sort_values("fy").iloc[-1]
    latest_ratios = ratios.sort_values("fy").iloc[-1]
    latest_health = health.sort_values("fy").iloc[-1]
    latest_valuation = valuation.iloc[0]
    latest_market = market_summary.iloc[0]
    base_case = dcf_summary[dcf_summary["scenario"] == "Base"].iloc[0]
    bull_case = dcf_summary[dcf_summary["scenario"] == "Bull"].iloc[0]
    bear_case = dcf_summary[dcf_summary["scenario"] == "Bear"].iloc[0]
    msft_market = market_metrics[market_metrics["ticker"] == "MSFT"].iloc[0]

    fy_min = int(financials["fy"].min())
    fy_max = int(financials["fy"].max())
    raw_sec_rows = int(source_audit.iloc[0]["raw_sec_rows"])
    sec_concepts = int(source_audit.iloc[0]["sec_concepts"])
    market_start_date = format_date(msft_market["start_date"])
    market_end_date = format_date(msft_market["end_date"])
    market_summary_date = format_date(latest_market["as_of_date"])

    financials_chart = financials.assign(
        revenue_bn=financials["revenue"] / 1_000_000_000,
        gross_profit_bn=financials["gross_profit"] / 1_000_000_000,
        operating_income_bn=financials["operating_income"] / 1_000_000_000,
        net_income_bn=financials["net_income"] / 1_000_000_000,
        operating_cash_flow_bn=financials["operating_cash_flow"] / 1_000_000_000,
        capex_bn=financials["capex"] / 1_000_000_000,
        free_cash_flow_bn=financials["free_cash_flow"] / 1_000_000_000,
    )

    revenue_fig = px.line(
        financials_chart,
        x="fy",
        y=["revenue_bn", "gross_profit_bn", "operating_income_bn", "net_income_bn"],
        markers=True,
        title="Revenue, Profit and Earnings",
        labels={"value": "USD billions", "fy": "Fiscal Year", "variable": "Metric"},
    )
    rename_traces(
        revenue_fig,
        {
            "revenue_bn": "Revenue",
            "gross_profit_bn": "Gross Profit",
            "operating_income_bn": "Operating Income",
            "net_income_bn": "Net Income",
        },
    )

    cash_fig = px.line(
        financials_chart,
        x="fy",
        y=["operating_cash_flow_bn", "capex_bn", "free_cash_flow_bn"],
        markers=True,
        title="Cash Flow, Capex and FCF",
        labels={"value": "USD billions", "fy": "Fiscal Year", "variable": "Metric"},
    )
    rename_traces(
        cash_fig,
        {
            "operating_cash_flow_bn": "Operating Cash Flow",
            "capex_bn": "Capex",
            "free_cash_flow_bn": "Free Cash Flow",
        },
    )

    margins_fig = px.line(
        ratios,
        x="fy",
        y=["gross_margin", "operating_margin", "net_margin", "fcf_margin"],
        markers=True,
        title="Profitability and Cash Flow Margins",
        labels={"value": "Margin", "fy": "Fiscal Year", "variable": "Metric"},
    )
    margins_fig.update_yaxes(tickformat=".0%")
    rename_traces(
        margins_fig,
        {
            "gross_margin": "Gross Margin",
            "operating_margin": "Operating Margin",
            "net_margin": "Net Margin",
            "fcf_margin": "FCF Margin",
        },
    )

    returns_fig = px.line(
        ratios,
        x="fy",
        y=["roe_avg_equity", "roa_avg_assets"],
        markers=True,
        title="Return Profile",
        labels={"value": "Return", "fy": "Fiscal Year", "variable": "Metric"},
    )
    returns_fig.update_yaxes(tickformat=".0%")
    rename_traces(returns_fig, {"roe_avg_equity": "ROE", "roa_avg_assets": "ROA"})

    sensitivity = dcf_sensitivity.copy()
    sensitivity["wacc_pct"] = (sensitivity["wacc"] * 100).round(2)
    sensitivity["terminal_growth_pct"] = (sensitivity["terminal_growth"] * 100).round(2)
    sensitivity["implied_share_price"] = sensitivity["implied_share_price"].round(2)
    sensitivity_pivot = sensitivity.pivot(
        index="wacc_pct",
        columns="terminal_growth_pct",
        values="implied_share_price",
    )
    sensitivity_fig = px.imshow(
        sensitivity_pivot,
        text_auto=True,
        aspect="auto",
        title="DCF Sensitivity: WACC vs Terminal Growth",
        color_continuous_scale=["#F29A8A", "#181F28", "#5ED6C6"],
    )
    sensitivity_fig.update_layout(
        coloraxis_showscale=False,
        xaxis_title="Terminal Growth (%)",
        yaxis_title="WACC (%)",
    )

    base_forecast = dcf_forecast[dcf_forecast["scenario"] == "Base"].copy()
    base_forecast_chart = base_forecast.assign(
        revenue_bn=base_forecast["revenue"] / 1_000_000_000,
        free_cash_flow_bn=base_forecast["free_cash_flow"] / 1_000_000_000,
        pv_fcf_bn=base_forecast["pv_fcf"] / 1_000_000_000,
    )
    dcf_fig = px.line(
        base_forecast_chart,
        x="forecast_year",
        y=["revenue_bn", "free_cash_flow_bn", "pv_fcf_bn"],
        markers=True,
        title="Base Case Forecast",
        labels={"value": "USD billions", "forecast_year": "Forecast Year", "variable": "Metric"},
    )
    rename_traces(
        dcf_fig,
        {
            "revenue_bn": "Revenue",
            "free_cash_flow_bn": "Free Cash Flow",
            "pv_fcf_bn": "PV of FCF",
        },
    )

    score_components = pd.DataFrame(
        {
            "Category": [
                "Profitability",
                "Growth",
                "Liquidity",
                "Leverage",
                "Cash Flow Quality",
            ],
            "Score": [
                latest_health["profitability_score"],
                latest_health["growth_score"],
                latest_health["liquidity_score"],
                latest_health["leverage_score"],
                latest_health["cash_flow_quality_score"],
            ],
        }
    )
    score_fig = px.bar(
        score_components,
        x="Category",
        y="Score",
        text="Score",
        title="Financial Health Score Breakdown",
    )
    score_fig.update_yaxes(range=[0, 100])
    score_fig.update_traces(marker_color="#5ED6C6", texttemplate="%{text:.1f}")

    financials_display = financials[
        [
            "fy",
            "revenue",
            "gross_profit",
            "operating_income",
            "net_income",
            "operating_cash_flow",
            "capex",
            "free_cash_flow",
        ]
    ].copy()
    for col in financials_display.columns:
        if col != "fy":
            financials_display[col] = (financials_display[col] / 1_000_000_000).round(2)
    financials_display = financials_display.rename(
        columns={
            "fy": "Fiscal Year",
            "revenue": "Revenue ($B)",
            "gross_profit": "Gross Profit ($B)",
            "operating_income": "Operating Income ($B)",
            "net_income": "Net Income ($B)",
            "operating_cash_flow": "Operating Cash Flow ($B)",
            "capex": "Capex ($B)",
            "free_cash_flow": "FCF ($B)",
        }
    )

    ratio_display = pd.DataFrame(
        {
            "Metric": [
                "Revenue Growth",
                "Gross Margin",
                "Operating Margin",
                "Net Margin",
                "FCF Margin",
                "Capex / Revenue",
                "ROE",
                "ROA",
                "Current Ratio",
                "Debt to Equity",
                "Net Cash",
            ],
            "Latest Value": [
                format_pct(latest_ratios["revenue_growth_yoy"]),
                format_pct(latest_ratios["gross_margin"]),
                format_pct(latest_ratios["operating_margin"]),
                format_pct(latest_ratios["net_margin"]),
                format_pct(latest_ratios["fcf_margin"]),
                format_pct(latest_ratios["capex_to_revenue"]),
                format_pct(latest_ratios["roe_avg_equity"]),
                format_pct(latest_ratios["roa_avg_assets"]),
                format_number(latest_ratios["current_ratio"]),
                format_number(latest_ratios["debt_to_equity"]),
                format_billions(latest_ratios["net_cash"]),
            ],
        }
    )

    assumptions_display = dcf_assumptions.copy()
    for col in [c for c in assumptions_display.columns if c != "scenario"]:
        assumptions_display[col] = (assumptions_display[col] * 100).round(2)
    assumptions_display = assumptions_display.rename(
        columns={
            "scenario": "Scenario",
            "revenue_growth_y1": "Y1 Growth %",
            "revenue_growth_y2": "Y2 Growth %",
            "revenue_growth_y3": "Y3 Growth %",
            "revenue_growth_y4": "Y4 Growth %",
            "revenue_growth_y5": "Y5 Growth %",
            "operating_margin": "Operating Margin %",
            "tax_rate": "Tax Rate %",
            "da_pct_revenue": "D&A / Revenue %",
            "capex_pct_revenue": "Capex / Revenue %",
            "nwc_pct_revenue": "NWC / Revenue %",
            "wacc": "WACC %",
            "terminal_growth": "Terminal Growth %",
        }
    )

    scenario_order = {"Bear": 1, "Base": 2, "Bull": 3}
    scenario_table = dcf_summary.copy()
    scenario_table["rank"] = scenario_table["scenario"].map(scenario_order).fillna(4)
    scenario_table = scenario_table.sort_values("rank")
    scenario_display = pd.DataFrame(
        {
            "Scenario": scenario_table["scenario"],
            "Current Price": scenario_table["current_price"].map(lambda x: f"${x:,.2f}"),
            "Implied Share Price": scenario_table["implied_share_price"].map(lambda x: f"${x:,.2f}"),
            "Upside / Downside": scenario_table["upside_downside"].map(lambda x: f"{x * 100:,.2f}%"),
            "WACC": scenario_table["wacc"].map(lambda x: f"{x * 100:,.2f}%"),
            "Terminal Growth": scenario_table["terminal_growth"].map(lambda x: f"{x * 100:,.2f}%"),
            "Revenue CAGR": scenario_table["forecast_revenue_cagr"].map(lambda x: f"{x * 100:,.2f}%"),
            "FCF CAGR": scenario_table["forecast_fcf_cagr"].map(lambda x: f"{x * 100:,.2f}%"),
            "Terminal Value / EV": scenario_table["terminal_value_pct_ev"].map(lambda x: f"{x * 100:,.2f}%"),
        }
    )

    analyst_summary_display = analyst_summary.rename(
        columns={
            "section": "Section",
            "takeaway": "Takeaway",
            "evidence": "Evidence",
            "analyst_note": "Analyst Note",
        }
    )

    scenario_view = pd.DataFrame(
        {
            "Scenario": ["Bear", "Base", "Bull"],
            "Implied Share Price": [
                f"${bear_case['implied_share_price']:,.2f}",
                f"${base_case['implied_share_price']:,.2f}",
                f"${bull_case['implied_share_price']:,.2f}",
            ],
            "Upside / Downside": [
                format_pct(bear_case["upside_downside"]),
                format_pct(base_case["upside_downside"]),
                format_pct(bull_case["upside_downside"]),
            ],
            "Interpretation": [
                "AI/cloud capex remains elevated, revenue growth slows, and valuation support weakens.",
                "Microsoft sustains strong growth and margins, but valuation remains sensitive to WACC and terminal growth.",
                "Cloud and AI monetization accelerate, margins remain resilient, and free cash flow expands strongly.",
            ],
        }
    )

    risk_display = pd.DataFrame(
        {
            "Risk Area": [
                "AI / Cloud Capex Intensity",
                "Free Cash Flow Quality",
                "Balance Sheet Leverage",
                "Liquidity Position",
            ],
            "Metric": [
                "Capex / Revenue",
                "FCF Margin",
                "Debt / Equity",
                "Current Ratio",
            ],
            "Latest Value": [
                format_pct(latest_ratios["capex_to_revenue"]),
                format_pct(latest_ratios["fcf_margin"]),
                format_number(latest_ratios["debt_to_equity"]),
                format_number(latest_ratios["current_ratio"]),
            ],
            "Analyst View": [
                "Monitor AI infrastructure intensity against future revenue growth.",
                "Strong FCF margin supports valuation quality and shareholder returns.",
                "Low leverage gives Microsoft financial flexibility.",
                "Healthy liquidity supports resilience and reinvestment capacity.",
            ],
        }
    )

    market_display = market_metrics.copy()
    for col in [
        "total_return",
        "annualized_return",
        "annualized_volatility",
        "max_drawdown",
        "average_annualized_daily_return",
    ]:
        market_display[col] = (market_display[col] * 100).round(2)
    market_display = market_display[
        [
            "ticker",
            "start_date",
            "end_date",
            "trading_days",
            "total_return",
            "annualized_return",
            "annualized_volatility",
            "max_drawdown",
            "beta_vs_sp500",
            "correlation_vs_sp500",
        ]
    ].rename(
        columns={
            "ticker": "Ticker",
            "start_date": "Start Date",
            "end_date": "End Date",
            "trading_days": "Trading Days",
            "total_return": "Total Return %",
            "annualized_return": "Annualized Return %",
            "annualized_volatility": "Annualized Volatility %",
            "max_drawdown": "Max Drawdown %",
            "beta_vs_sp500": "Beta vs S&P 500",
            "correlation_vs_sp500": "Correlation vs S&P 500",
        }
    )

    pipeline_display = pd.DataFrame(
        {
            "Step": [
                "1. SEC Fact Ingestion",
                "2. XBRL Flattening",
                "3. Manual Concept Mapping",
                "4. Annual Financials Layer",
                "5. Financial Ratios Engine",
                "6. Market Risk Context",
                "7. SaaS Cohort Modeling",
                "8. Pricing Moat Sandbox",
                "9. CapEx & AI Drag Analysis",
                "10. Competitor Benchmarking",
                "11. Segment Growth Blending",
                "12. Headcount Drag Planner",
                "13. Monte Carlo DCF Simulator",
                "14. Financial Health Composite",
                "15. Interactive Presentation & AI Analyst Layer",
            ],
            "File / Layer / System": [
                "src/collect_msft_sec_data.py",
                "raw_sec_facts table",
                "sql/01_create_fact_map.sql",
                "sql/03_build_financials_annual.sql",
                "sql/04_create_ratios_annual.sql",
                "src/fetch_market_data.py + SQL",
                "app.py + historical SaaS data models",
                "app.py",
                "app.py + custom SQL view",
                "app.py + competitor peer dataset",
                "app.py",
                "app.py",
                "app.py + NumPy simulation vectors",
                "sql/07_create_financial_health_score.sql",
                "app.py + live DB query analytics",
            ],
            "What It Accomplishes": [
                "Pulls raw Microsoft companyfacts from the SEC EDGAR API (32,000+ rows).",
                "Converts nested XBRL taxonomy, concept, unit, and observation JSON facts into structured rows.",
                "Maps 500+ overlapping reporting concepts to select primary financial statements.",
                "Constructs fiscal-year Income Statements, Balance Sheets, and Cash Flows for FY2021–FY2025.",
                "Computes margin, growth, return, leverage, efficiency, and liquidity indicators.",
                "Pulls MSFT and S&P 500 price data from yfinance, calculating Beta, Sharpe, drawdown, and risk bands.",
                "Models historical seats, ARPU, CAC, and monthly churn with a 12-month cohort retention decay curve.",
                "Simulates price hikes against churn elasticity to display baseline vs. post-hike revenues.",
                "Compares Cash CapEx vs. GAAP Depreciation side-by-side, tracking cash burn efficiency.",
                "Benchmarks Microsoft against Big Tech peers (AAPL, GOOGL, AMZN, META, NVDA) on multiples.",
                "Blends Intelligent Cloud, Productivity, and MPC growth inputs into a single DCF CAGR seed.",
                "Applies incremental headcount hiring expenses as a margin drag to the DCF projection.",
                "Executes 5,000 randomized normal projection walks over a 5-year forecast horizon.",
                "Constructs Altman Z-Score components and composite 0-100 financial health scores.",
                "Renders Plotly visualizations alongside glassmorphic AI Analyst Explainers and commentary.",
            ],
        }
    )

    metrics_html = "".join(
        [
            metric_card("Revenue", format_billions(latest_financials["revenue"]), f"FY {fy_max}"),
            metric_card("Net Income", format_billions(latest_financials["net_income"]), f"FY {fy_max}"),
            metric_card("Free Cash Flow", format_billions(latest_financials["free_cash_flow"]), f"FY {fy_max}"),
            metric_card("Health Score", f"{latest_health['financial_health_score']:.2f}/100", latest_health["financial_health_rating"]),
            metric_card("Current Price", f"${latest_valuation['current_price']:,.2f}", market_summary_date),
            metric_card("Base DCF Price", f"${base_case['implied_share_price']:,.2f}", valuation_view(base_case["upside_downside"])),
            metric_card("Share Price Growth", format_pct(base_case["upside_downside"]), "Assumption-based"),
            metric_card("EV / FCF", format_number(latest_valuation["ev_to_fcf"]), "Valuation multiple"),
        ]
    )

    analyst_cards = f"""
        <div class="card-grid">
            <div class="analyst-card">
                <div class="card-label">Quality of earnings</div>
                <div class="card-title">High-margin, cash-generative core</div>
                <p>Latest operating margin is {format_pct(latest_ratios["operating_margin"])} and FCF margin is {format_pct(latest_ratios["fcf_margin"])}. The central business question is whether cloud and AI investment can protect this cash conversion.</p>
            </div>
            <div class="analyst-card">
                <div class="card-label">Balance sheet</div>
                <div class="card-title">Financial flexibility remains a strength</div>
                <p>Net cash is {format_billions(latest_ratios["net_cash"])} and debt to equity is {format_number(latest_ratios["debt_to_equity"])}. That supports reinvestment capacity while AI infrastructure spending raises the bar for future returns.</p>
            </div>
            <div class="analyst-card">
                <div class="card-label">Valuation discipline</div>
                <div class="card-title">{valuation_view(base_case["upside_downside"])}</div>
                <p>The base DCF implies {format_pct(base_case["upside_downside"])} versus the market price. This is a model result, not a price prediction, and should be read with the sensitivity table.</p>
            </div>
        </div>
    """

    css = """
        :root {
            color-scheme: dark;
            --bg: #090C10;
            --panel: rgba(18, 24, 31, 0.72);
            --stroke: rgba(221, 231, 239, 0.15);
            --stroke-strong: rgba(133, 197, 190, 0.38);
            --text: #F4F7F8;
            --muted: #AAB6BC;
            --soft: #D6E4E2;
            --accent: #5ED6C6;
            --accent-2: #E8C46A;
        }

        * { box-sizing: border-box; }
        html {
            scroll-behavior: smooth;
            background: #090C10;
        }
        body {
            margin: 0;
            background:
                radial-gradient(circle at 18% 8%, rgba(94, 214, 198, 0.14), transparent 30%),
                radial-gradient(circle at 90% 4%, rgba(232, 196, 106, 0.10), transparent 28%),
                linear-gradient(145deg, #090C10 0%, #11161B 48%, #080A0D 100%);
            color: var(--text);
            font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
            line-height: 1.55;
            font-size: 15px;
        }

        button { font: inherit; }
        .shell { width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 28px 0 54px; }
        .nav {
            position: sticky;
            top: 0;
            z-index: 20;
            display: grid;
            grid-template-columns: minmax(220px, 0.9fr) minmax(0, 2.4fr);
            gap: 18px;
            align-items: start;
            padding: 16px 18px 14px;
            margin-bottom: 16px;
            background: rgba(9, 12, 16, 0.66);
            border: 1px solid rgba(221, 231, 239, 0.08);
            border-radius: 14px;
            box-shadow: 0 18px 44px rgba(0, 0, 0, 0.22);
            backdrop-filter: blur(18px);
            overflow: visible;
        }
        .brand {
            display: flex;
            gap: 10px;
            align-items: center;
            min-height: 40px;
            font-size: 14px;
            font-weight: 800;
            color: var(--accent);
            text-transform: uppercase;
        }
        .ms-logo {
            display: grid;
            grid-template-columns: repeat(2, 10px);
            grid-template-rows: repeat(2, 10px);
            gap: 3px;
            width: 23px;
            height: 23px;
            flex: 0 0 auto;
        }
        .ms-logo span { display: block; border-radius: 1px; }
        .ms-logo .red { background: #F25022; }
        .ms-logo .green { background: #7FBA00; }
        .ms-logo .blue { background: #00A4EF; }
        .ms-logo .yellow { background: #FFB900; }
        .tabs {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            justify-content: flex-end;
            align-content: flex-start;
        }
        .tab-button {
            color: var(--muted);
            font-size: 13px;
            padding: 8px 12px;
            border: 1px solid var(--stroke);
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.04);
            cursor: pointer;
            transition: border-color 160ms ease, color 160ms ease, background 160ms ease;
        }
        .tab-button:hover,
        .tab-button.active {
            color: var(--text);
            border-color: var(--stroke-strong);
            background: rgba(94, 214, 198, 0.13);
        }

        .hero,
        .panel,
        .metric-card,
        .analyst-card {
            background: linear-gradient(145deg, rgba(255,255,255,0.10), rgba(255,255,255,0.025)), var(--panel);
            border: 1px solid var(--stroke);
            border-radius: 8px;
            box-shadow: 0 22px 60px rgba(0,0,0,0.30);
            backdrop-filter: blur(18px);
        }
        .hero { padding: 32px; margin-bottom: 22px; }
        .hero-brand {
            display: flex;
            gap: 12px;
            align-items: center;
            margin-bottom: 10px;
        }
        .kicker { color: var(--accent); font-size: 13px; font-weight: 800; text-transform: uppercase; margin-bottom: 8px; }
        h1 { font-size: clamp(38px, 5vw, 68px); line-height: 1.02; margin: 0 0 18px; letter-spacing: 0; }
        .hero p { max-width: 980px; color: var(--soft); font-size: 17px; margin: 0 0 20px; }
        .tags { display: flex; flex-wrap: wrap; gap: 10px; }
        .tag { color: var(--soft); background: rgba(255,255,255,0.06); border: 1px solid var(--stroke); border-radius: 999px; padding: 7px 11px; font-size: 12px; }
        .tab-panel {
            display: none;
            margin-top: 28px;
            animation: fadeIn 220ms ease;
        }
        .tab-panel.active { display: block; }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }
        h2 { font-size: 28px; margin: 0 0 14px; letter-spacing: 0; }
        .section-heading {
            color: var(--text);
            font-size: 22px;
            font-weight: 850;
            margin: 28px 0 12px;
            letter-spacing: 0;
        }
        .note, .panel p { color: var(--soft); }
        .panel { padding: 20px; margin-bottom: 22px; }
        .metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin: 18px 0 22px; }
        .metric-card { padding: 18px; min-height: 120px; }
        .metric-label { color: var(--muted); font-size: 12px; font-weight: 700; margin-bottom: 9px; }
        .metric-value { color: var(--text); font-size: clamp(21px, 2.2vw, 27px); font-weight: 850; line-height: 1.14; overflow-wrap: anywhere; }
        .metric-note { color: var(--accent-2); font-size: 12px; margin-top: 10px; }
        .card-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
        .analyst-card { padding: 20px; }
        .card-label { color: var(--accent); font-size: 12px; font-weight: 800; text-transform: uppercase; margin-bottom: 7px; }
        .card-title { color: var(--text); font-size: 19px; font-weight: 800; margin-bottom: 8px; }
        .analyst-card p { color: var(--muted); margin: 0; }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 16px;
            margin: 24px 0 30px;
        }
        .summary-card {
            min-width: 0;
            padding: 20px;
            background: linear-gradient(145deg, rgba(255,255,255,0.09), rgba(255,255,255,0.025)), rgba(18,24,31,0.62);
            border: 1px solid var(--stroke);
            border-radius: 8px;
            box-shadow: 0 18px 46px rgba(0,0,0,0.24);
        }
        .summary-section {
            color: var(--accent);
            font-size: 12px;
            font-weight: 850;
            letter-spacing: 0;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .summary-card h3 {
            color: var(--text);
            font-size: 18px;
            line-height: 1.28;
            margin: 0 0 16px;
        }
        .summary-block {
            padding-top: 12px;
            border-top: 1px solid rgba(221,231,239,0.10);
            margin-top: 12px;
        }
        .summary-block span {
            display: block;
            color: var(--muted);
            font-size: 12px;
            font-weight: 800;
            margin-bottom: 6px;
            text-transform: uppercase;
        }
        .summary-block p {
            color: var(--soft);
            line-height: 1.58;
            margin: 0;
            white-space: normal;
            overflow-wrap: anywhere;
        }
        .summary-note p {
            color: var(--text);
        }
        .chart-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 24px;
            margin: 18px 0 26px;
        }
        .chart-card {
            min-width: 0;
            padding: 24px 22px 18px;
            background: rgba(18,24,31,0.58);
            border: 1px solid var(--stroke);
            border-radius: 8px;
        }
        .chart-title {
            color: var(--text);
            font-size: 18px;
            font-weight: 820;
            line-height: 1.2;
            margin: 0 0 18px;
            letter-spacing: 0;
        }
        .chart-plot {
            min-height: 430px;
        }
        .chart-plot .plotly-graph-div {
            min-height: 430px;
        }
        .table-wrap {
            overflow-x: visible;
            border: 1px solid var(--stroke);
            border-radius: 8px;
            background: rgba(18,24,31,0.58);
            margin: 24px 0;
        }
        .panel + .table-wrap,
        .table-wrap + .chart-grid,
        .chart-grid + .table-wrap,
        .table-wrap + .table-wrap {
            margin-top: 28px;
        }
        .data-table { width: 100%; border-collapse: collapse; table-layout: fixed; color: var(--soft); font-size: 13px; }
        .data-table th { text-align: left; color: var(--text); background: rgba(94,214,198,0.12); font-weight: 800; white-space: normal; }
        .data-table th, .data-table td { padding: 10px 12px; border-bottom: 1px solid rgba(221,231,239,0.10); white-space: normal; overflow-wrap: anywhere; line-height: 1.48; vertical-align: top; }
        .data-table tr:last-child td { border-bottom: 0; }
        footer { margin-top: 44px; color: var(--muted); font-size: 13px; }
        @media print {
            @page {
                size: A4 landscape;
                margin: 0.35in;
            }
            body {
                background: #ffffff;
                color: #111827;
                font-size: 10px;
            }
            .shell {
                width: 100%;
                padding: 0;
            }
            .nav,
            .tabs,
            footer {
                display: none;
            }
            .hero,
            .panel,
            .metric-card,
            .analyst-card,
            .chart-card,
            .summary-card,
            .table-wrap {
                box-shadow: none;
                background: #ffffff;
                color: #111827;
                border-color: #d1d5db;
            }
            .tab-panel {
                display: none !important;
                margin-top: 12px;
            }
            .tab-panel.active {
                display: block !important;
            }
            .tab-panel h2,
            h1,
            .metric-value,
            .card-title,
            .chart-title {
                color: #111827;
            }
            .hero p,
            .panel p,
            .analyst-card p,
            .summary-block p,
            .data-table,
            .metric-label,
            .metric-note,
            .tag {
                color: #374151;
            }
            .chart-grid,
            .metric-grid,
            .card-grid,
            .summary-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 10px;
            }
            .chart-card {
                break-inside: avoid;
                padding: 10px;
            }
            .chart-plot,
            .chart-plot .plotly-graph-div {
                min-height: 360px;
                height: 360px !important;
                width: 100% !important;
            }
            .hero {
                padding: 12px 14px;
                margin-bottom: 10px;
            }
            h1 {
                font-size: 26px;
            }
            h2 {
                font-size: 18px;
                margin-bottom: 8px;
            }
            .panel,
            .metric-card,
            .analyst-card,
            .summary-card {
                padding: 10px;
                margin-bottom: 10px;
            }
            .table-wrap {
                margin: 10px 0 14px;
                break-inside: auto;
            }
            .data-table {
                font-size: 9px;
            }
            .data-table th,
            .data-table td {
                padding: 5px 6px;
                color: #111827;
                border-color: #d1d5db;
            }
        }
        @media (max-width: 1180px) {
            .nav {
                grid-template-columns: 1fr;
                position: static;
            }
            .tabs {
                justify-content: flex-start;
            }
        }
        @media (max-width: 920px) {
            .metric-grid, .card-grid, .chart-grid, .summary-grid { grid-template-columns: 1fr; }
            .hero { padding: 24px; }
        }
    """

    html = f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Microsoft Financial Health & Valuation Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <style>{css}</style>
</head>
<body>
    <main class="shell">
        <nav class="nav">
            <div class="brand">
                <span class="ms-logo" aria-hidden="true">
                    <span class="red"></span><span class="green"></span>
                    <span class="blue"></span><span class="yellow"></span>
                </span>
                <span>MSFT Financial Dashboard</span>
            </div>
            <div class="tabs" role="tablist" aria-label="Dashboard sections">
                <button class="tab-button active" type="button" data-tab="summary">Summary</button>
                <button class="tab-button" type="button" data-tab="financials">Financials</button>
                <button class="tab-button" type="button" data-tab="ratios">Ratios</button>
                <button class="tab-button" type="button" data-tab="market">Market Risk</button>
                <button class="tab-button" type="button" data-tab="valuation">Valuation</button>
                <button class="tab-button" type="button" data-tab="health">Health Score</button>
                <button class="tab-button" type="button" data-tab="judgment">Business Judgment</button>
                <button class="tab-button" type="button" data-tab="methodology">Methodology</button>
            </div>
        </nav>

        <header class="hero">
            <div class="hero-brand">
                <span class="ms-logo" aria-hidden="true">
                    <span class="red"></span><span class="green"></span>
                    <span class="blue"></span><span class="yellow"></span>
                </span>
                <div class="kicker">Static GitHub Pages version</div>
            </div>
            <h1>Microsoft Financial Health & Valuation Dashboard</h1>
            <p>
                A public-data analyst model that traces Microsoft from raw SEC XBRL facts to normalized
                financial statements, ratio analysis, market-risk context, scenario DCF valuation, and a
                transparent financial health score. The valuation output is assumption-based, not a stock recommendation.
            </p>
            <div class="tags">
                <span class="tag">SEC XBRL facts: {raw_sec_rows:,} rows</span>
                <span class="tag">SEC concepts: {sec_concepts:,}</span>
                <span class="tag">Financial years: {fy_min}-{fy_max}</span>
                <span class="tag">Market window: {market_start_date} to {market_end_date}</span>
                <span class="tag">Snapshot: {market_summary_date}</span>
            </div>
        </header>
        {tab_panel("Executive Brief", f'''
            <div class="panel">
                <p><strong>Data reality:</strong> SEC annual 10-K / 10-K/A facts are used for fiscal-year analysis.
                Market prices and company summary fields come from yfinance. DCF and health-score outputs are
                custom frameworks built for transparent analysis, not third-party ratings.</p>
            </div>
            <div class="metric-grid">{metrics_html}</div>
            {analyst_cards}
            <h3 class="section-heading">Automated Analyst Summary</h3>
            {analyst_summary_html(analyst_summary_display)}
        ''', "summary", active=True)}

        {tab_panel("Financial Trends", f'''
            <div class="chart-grid">
                <div class="chart-card">{chart_html(revenue_fig, include_plotlyjs=False)}</div>
                <div class="chart-card">{chart_html(cash_fig, include_plotlyjs=False)}</div>
            </div>
            <div class="table-wrap">{table_html(financials_display)}</div>
        ''', "financials")}

        {tab_panel("Ratio Analysis", f'''
            <div class="chart-grid">
                <div class="chart-card">{chart_html(margins_fig, include_plotlyjs=False)}</div>
                <div class="chart-card">{chart_html(returns_fig, include_plotlyjs=False)}</div>
            </div>
            <div class="table-wrap">{table_html(ratio_display)}</div>
        ''', "ratios")}

        {tab_panel("Market Risk", f'''
            <div class="panel">
                <p>Strong fundamentals do not remove market risk. Beta, drawdown, volatility, and correlation help frame
                how much valuation risk can come from expectations and discount rates rather than operating performance alone.</p>
            </div>
            <div class="table-wrap">{table_html(market_display)}</div>
        ''', "market")}

        {tab_panel("DCF Valuation", f'''
            <div class="panel">
                <p><strong>Base-case view:</strong> {valuation_view(base_case["upside_downside"])}. The base DCF implies
                {format_pct(base_case["upside_downside"])} versus the current market price. This is a model result,
                not a price prediction.</p>
            </div>
            <div class="table-wrap">{table_html(assumptions_display)}</div>
            <div class="table-wrap">{table_html(scenario_display)}</div>
            <div class="chart-grid">
                <div class="chart-card">{chart_html(sensitivity_fig, include_plotlyjs=False)}</div>
                <div class="chart-card">{chart_html(dcf_fig, include_plotlyjs=False)}</div>
            </div>
        ''', "valuation")}

        {tab_panel("Financial Health Score", f'''
            <div class="panel">
                <p>{latest_health["analyst_commentary"]} This score is a custom framework for this dashboard and should
                not be read as a credit rating or an external analyst rating.</p>
            </div>
            <div class="chart-card">{chart_html(score_fig, include_plotlyjs=False)}</div>
        ''', "health")}

        {tab_panel("Business Judgment & Analyst View", f'''
            <div class="metric-grid">
                {metric_card("Financial Health", latest_health["financial_health_rating"], f"{latest_health['financial_health_score']:.2f}/100")}
                {metric_card("Valuation View", valuation_view(base_case["upside_downside"]), "Base-case DCF")}
                {metric_card("Share Price Growth", format_pct(base_case["upside_downside"]), "Assumption-based")}
                {metric_card("Market Cap", format_billions(latest_valuation["market_cap"]), market_summary_date)}
            </div>
            <div class="panel">
                <p><strong>Analyst memo:</strong> Microsoft shows excellent financial health in this framework, supported by high profitability,
                strong free cash flow generation, low leverage, and a healthy liquidity position. The dashboard does not treat that quality
                as enough by itself. The key underwriting question is whether Microsoft can convert AI and cloud infrastructure spending
                into durable revenue growth, margin stability, and free cash flow conversion.</p>
                <p><strong>Base-case valuation view:</strong> {valuation_view(base_case["upside_downside"])}. Under the selected assumptions,
                the base DCF implies {format_pct(base_case["upside_downside"])} versus the current market price.</p>
            </div>
            <div class="table-wrap">{table_html(scenario_view)}</div>
            <div class="table-wrap">{table_html(risk_display)}</div>
        ''', "judgment")}

        {tab_panel("Methodology & Reality Check", f'''
            <div class="panel">
                <p>This static page is generated from the DuckDB database. It is meant for GitHub Pages or direct browser viewing.
                It does not need Streamlit, a Python runtime, or localhost after generation.</p>
            </div>
            
            <div class="section-heading">Core Analytical Methodologies</div>
            
            <div class="panel">
                <h4 style="margin-top: 0; color: var(--accent);">1. SaaS Subscription Unit Economics & Cohort Engine</h4>
                <ul>
                    <li><b>Lifetime Value (LTV):</b> Calculated as <code>(ARPU × Gross Margin) / Monthly Churn Rate</code>.</li>
                    <li><b>Cohort Retention Decay:</b> Built on a standard exponential retention decay model: <code>S_t = S_0 × (1 - Monthly Churn)^t</code> over a 12-month period based on actual annualised parameters.</li>
                    <li><b>Price Elasticity Sandbox:</b> Simulates subscription price increases against user-defined churn elasticity coefficients: <code>ΔSubscribers = Price Hike % × Churn Elasticity × Baseline Subscribers</code>.</li>
                </ul>
            </div>
            
            <div class="panel">
                <h4 style="margin-top: 0; color: var(--accent);">2. CapEx & AI Capital Cash Drag</h4>
                <ul>
                    <li><b>FCF Conversion Gap:</b> Divergence between <b>Cash Capital Expenditures (CapEx)</b> and <b>GAAP Depreciation & Amortisation (D&A)</b>: <code>Gap = Cash CapEx - GAAP Depreciation</code>.</li>
                    <li><b>FCF Conversion Efficiency:</b> Measures the percentage of EBITDA converted to Free Cash Flow: <code>FCF / EBITDA × 100%</code>, illustrating rapid physical asset spend cash drag.</li>
                </ul>
            </div>

            <div class="panel">
                <h4 style="margin-top: 0; color: var(--accent);">3. Monte Carlo DCF Simulation Engine</h4>
                <ul>
                    <li><b>Stochastic Path Generation:</b> Runs 5,000 randomized normal projection walks over a 5-year forecast horizon of revenue growth and operating margins: <code>N(μ, σ^2)</code>, highlighting the 10th, 50th, and 90th percentiles of discounted cash flows.</li>
                </ul>
            </div>

            <div class="panel">
                <h4 style="margin-top: 0; color: var(--accent);">4. Segment CAGR Blending & Headcount Drag</h4>
                <ul>
                    <li><b>Weighted Growth Blender:</b> Combines segment CAGRs (Azure, Office/Teams, MPC) by revenue weight: <code>CAGR_blended = Σ(Segment Weight_i × Segment CAGR_i)</code>.</li>
                    <li><b>Hiring Margin Drag Planner:</b> Models incremental headcount expense as an operating margin drag: <code>(Incremental Headcount × Average Salary) / Projected Revenue × 100%</code>.</li>
                </ul>
            </div>

            <div class="panel">
                <h4 style="margin-top: 0; color: var(--accent);">5. Composite Financial Health & Altman Z-Score</h4>
                <ul>
                    <li><b>Altman Z-Score Model:</b> Computes core liquidity, profitability, operating efficiency, solvency, and asset turnover metrics: <code>Z = 1.2X_1 + 1.4X_2 + 3.3X_3 + 0.6X_4 + 0.999X_5</code>. Mapped to a composite 0-100 score.</li>
                </ul>
            </div>

            <div class="section-heading">Data Ingestion & Analytical Pipeline</div>
            <div class="table-wrap">{table_html(pipeline_display)}</div>
            
            <div class="section-heading">Model Boundaries & Scope Limitations</div>
            <div class="panel">
                <ul>
                    <li><b>Company scope:</b> Single-company primary analysis (Microsoft Corporation) relative to Big Tech peers.</li>
                    <li><b>Financial reporting:</b> Uses selected annual 10-K / 10-K/A SEC facts from FY2021-2025.</li>
                    <li><b>Market metrics feed:</b> Sourced via yfinance API; minor pricing differences may exist relative to paid institutional terminals.</li>
                    <li><b>SaaS economics modeling:</b> Seat counts, ARPU, churn, and CAC are modeled based on disclosures and industry standards, not internal systems.</li>
                    <li><b>Competitor benchmarks:</b> Peer multiples (AAPL, GOOGL, AMZN, META, NVDA) represent point-in-time snapshots for structural context.</li>
                    <li><b>Monte Carlo simulation:</b> Assumes normally distributed randomized walks based on historical volatility; does not simulate tail risk.</li>
                    <li><b>Headcount expenditure planner:</b> Assumes standardized employee compensation packages; does not model stock-based compensation dilution.</li>
                    <li><b>DCF sensitivity:</b> Scenario-based valuation; highly sensitive to WACC, terminal growth, capex, and margin inputs.</li>
                    <li><b>Composite health scoring:</b> Custom research framework based on Altman Z and financial ratios; not an official credit rating.</li>
                </ul>
            </div>
            
            <div class="panel">
                <p><strong>Assumption-Based Outputs:</strong> The models, simulations, and indicators calculated across this platform are mathematically rigorous 
                but ultimately dependent on the inputs and assumptions specified. A DCF implied price is not a stock 
                prediction; a Financial Health Score is not a corporate solvency guarantee. These frameworks are designed 
                to make investment assumptions fully visible, test operational sensitivity, and foster structured, 
                disciplined discussions of business quality.</p>
            </div>
        ''', "methodology")}

        <footer>
            Generated from DuckDB using Python and Plotly. This project demonstrates a transparent finance analytics workflow,
            not investment advice.
        </footer>
    </main>
    <script>
        const buttons = Array.from(document.querySelectorAll(".tab-button"));
        const panels = Array.from(document.querySelectorAll(".tab-panel"));

        function activateTab(tabId) {{
            buttons.forEach((button) => {{
                const isActive = button.dataset.tab === tabId;
                button.classList.toggle("active", isActive);
                button.setAttribute("aria-selected", String(isActive));
            }});

            panels.forEach((panel) => {{
                panel.classList.toggle("active", panel.id === tabId);
            }});

            requestAnimationFrame(() => {{
                window.dispatchEvent(new Event("resize"));
            }});
        }}

        buttons.forEach((button) => {{
            button.addEventListener("click", () => activateTab(button.dataset.tab));
        }});

        window.resizeCharts = function resizeCharts() {{
            if (!window.Plotly) return;
            document.querySelectorAll(".tab-panel.active .plotly-graph-div").forEach((chart) => {{
                window.Plotly.Plots.resize(chart);
            }});
        }};

        window.addEventListener("load", resizeCharts);
    </script>
</body>
</html>"""

    return html


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(build_dashboard(), encoding="utf-8")
    print(f"Static dashboard written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
