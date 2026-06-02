# Microsoft Financial Health & Valuation Dashboard

An end-to-end institutional-grade financial analytics platform for Microsoft Corporation built entirely on public data — SEC XBRL filings, yfinance market data, DuckDB, SQL, Python, Plotly, and Streamlit.

The goal is not to present a stock recommendation. The goal is to show a realistic analyst workflow at institutional depth: collect raw public data, normalise it, build financial statements and ratios, add market context, run scenario and probabilistic DCF models, analyse SaaS unit economics, benchmark against peers, and present all results in an interactive, plain-English dashboard.

---

## What The Project Does

- Collects Microsoft `companyfacts` data from the SEC EDGAR API (32,000+ raw XBRL rows across 547 concepts).
- Flattens raw XBRL facts into a DuckDB analytical database.
- Maps selected SEC concepts into standardised financial metrics via a manual concept map.
- Builds annual financial statements for fiscal years **FY2021–FY2025**.
- Calculates profitability, growth, liquidity, leverage, cash flow, and return ratios for every year.
- Pulls Microsoft and S&P 500 price history from yfinance and computes market-risk metrics.
- Builds valuation multiples and a multi-scenario DCF model (Bear / Base / Bull).
- Creates a custom **Financial Health Score** (0–100) with fully visible scoring logic.
- Models **SaaS unit economics** (LTV, CAC, ARPU, churn) for Office 365 and Xbox Game Pass across all 5 years.
- Runs a **Monte Carlo DCF simulation** (5,000 randomised valuation paths) using NumPy.
- Benchmarks Microsoft against Big Tech peers (AAPL, GOOGL, AMZN, META, NVDA) on valuation and efficiency multiples.
- Presents the analysis through a **Streamlit interactive dashboard** designed for local use and Streamlit Community Cloud deployment.

---

## Dashboard Sections (12 Tabs)

| # | Tab | What It Shows |
|---|---|---|
| 1 | **Executive Summary** | Revenue, net income, FCF, health score, P/E, ROIC, DCF implied price, automated analyst brief |
| 2 | **Financial Trends** | 5-year revenue/income/FCF lines, quarterly seasonality bar chart, TTM rolling curves, margin trends |
| 3 | **Ratio Analysis** | Operating margin, FCF margin, ROIC, debt/equity, current ratio — yearly table with risk traffic lights |
| 4 | **SaaS & Pricing Moat** | Office 365 + Xbox Game Pass unit economics by year, LTV/CAC ratios, 12-month cohort retention decay curve, interactive price elasticity & price hike sandbox |
| 5 | **CapEx & AI Cash Drag** | Cash CapEx vs. GAAP depreciation gap chart, FCF conversion efficiency line, R&D ROI bar chart |
| 6 | **Competitor Benchmarking** | Peer multiple table (P/E, EV/EBITDA, P/S, ROIC, WACC), ROIC vs. WACC capital-return scatter plot |
| 7 | **Market Risk** | Annualised volatility, max drawdown, Beta, Sharpe ratio, stock price performance vs. volatility bands |
| 8 | **Segment & Headcount Drivers** | Intelligent Cloud / Productivity / More Personal Computing growth sliders → weighted CAGR; headcount OpEx planner with operating margin drag |
| 9 | **DCF Sandbox & Valuation** | 5-year FCF projection, WACC/terminal-growth sensitivity matrix, custom scenario builder, Monte Carlo 5,000-path simulation histogram |
| 10 | **Health Score** | Altman Z-Score, 5 component ratios with risk labels, composite 0–100 financial health score |
| 11 | **Business Judgment** | Strategic moat, AI transition risk, capital allocation quality, live AI Q&A engine (4 analyst questions) |
| 12 | **Methodology** | Full data pipeline transparency: SEC EDGAR ingestion, SQL transformations, DCF framework, health-score formula, data freshness audit |

---

## Key Features Added

### SaaS Subscription Cohort Engine
Models seats, ARPU, CAC, and monthly churn for both Office 365 (B2B) and Xbox Game Pass (B2C) across all five fiscal years. A sidebar **Historical Period Analysis** selector (FY21–FY25) dynamically rebinds all metric cards, the cohort decay curve, and the price elasticity sandbox to the selected year.

- **LTV / CAC ratio** — Office 365 reaches ~29:1 in FY25, one of the highest in enterprise software.
- **12-Month Cohort Retention Decay Curve** — Visualises how many of an original cohort remain subscribed each month, driven by the year's actual churn rate.
- **Price Elasticity & Price Hike Sandbox** — Interactive sliders for Price Increase % and Churn Elasticity Coefficient. Instantly calculates subscriber drop-off and renders a Baseline vs. Post-Pricing revenue bar chart with a plain-English scenario verdict (Strong Pricing Power / Risky Revenue Gain / Price Hike Backfires).

### CapEx & AI Cash Drag Analysis
Plots Cash CapEx vs. GAAP Depreciation side by side (FY21–FY25), exposing the $34.5B FCF conversion gap created by front-loaded datacenter and GPU spend. Includes FCF Conversion Efficiency line chart and R&D ROI bar chart.

### Competitor Benchmarking Matrix
Compares MSFT against AAPL, GOOGL, AMZN, META, and NVDA on P/E, EV/EBITDA, P/S, ROIC, and WACC. The ROIC vs. WACC scatter plot shows capital-return spreads (economic value creation) for every peer.

### Monte Carlo DCF Simulation
Runs 5,000 randomised normal projection walks using vectorised NumPy arrays in under 50 ms. Produces a probability distribution of implied share prices with the 10th (Conservative), 50th (Median), and 90th (Optimistic) percentiles highlighted on a bell-curve histogram.

### Segment-Level Growth Model
Weights Azure (45%), Office/Teams (32%), and More Personal Computing (23%) as independent growth levers. Adjusting segment sliders produces a dynamically blended revenue CAGR fed directly into the DCF.

### Headcount OpEx Planner
Calculates incremental personnel expenditure from headcount growth % and average salary inputs. Converts the result into an operating margin drag applied to the active DCF model.

### AI Analyst Explainer Layer
Every tab includes an optional **Enable AI Analyst Explainer** checkbox that renders a glassmorphic insight card with plain-English, quantitative commentary generated from live database values — no hardcoded text.

### Plain-English Chart Commentary
Every chart across all 12 tabs is paired with a dedicated insight card that translates the visual into a business narrative accessible without a finance background.

---

## Current Data Coverage

| Dimension | Value |
|---|---|
| Company | Microsoft Corporation (MSFT) |
| SEC financial period | Fiscal years 2021–2025 |
| Raw XBRL rows | 32,070 |
| SEC concepts mapped | 547 |
| Market data start | 2020-01-02 |
| Market snapshot | 2026-05-21 |
| Financial data source | SEC EDGAR companyfacts API |
| Market data source | yfinance |

---

## Project Structure

```text
.
├── app.py                          # Main Streamlit dashboard (12 tabs, 3,700+ lines)
├── requirements.txt
├── .env                            # SEC_USER_AGENT (not committed)
├── recordings/
│   └── make_gif.py                 # Screenshot-to-GIF compiler (Pillow)
├── data/
│   ├── raw/
│   └── processed/
├── database/
│   └── finance.duckdb              # Processed analytical database
├── sql/
│   ├── 01_create_fact_map.sql
│   ├── 02_clean_sec_facts.sql
│   ├── 03_build_financials_annual.sql
│   ├── 04_create_ratios_annual.sql
│   ├── 05_create_market_metrics.sql
│   ├── 06_create_valuation_multiples.sql
│   └── 07_create_financial_health_score.sql
└── src/
    ├── collect_msft_sec_data.py
    ├── fetch_market_data.py
    ├── run_sql_pipeline.py
    ├── run_market_metrics.py
    ├── run_valuation_multiples.py
    ├── run_dcf_model.py
    └── run_health_score.py
```

---

## Streamlit App

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Create a `.env` file:**

```bash
SEC_USER_AGENT="Your Name your_email@example.com"
```

**Run the data pipeline:**

```bash
python src/collect_msft_sec_data.py
python src/fetch_market_data.py
python src/run_sql_pipeline.py
python src/run_market_metrics.py
python src/run_valuation_multiples.py
python src/run_dcf_model.py
python src/run_health_score.py
```

**Start the dashboard:**

```bash
streamlit run app.py
```

---

## Streamlit Community Cloud Deployment

This repository is intended to deploy directly on Streamlit Community Cloud. The app reads the processed DuckDB database from:

```text
database/finance.duckdb
```

Recommended deployment settings:

| Setting | Value |
|---|---|
| Repository | `dabhishek0410-spec/Microsoft-Financial-Dashboard` |
| Branch | `main` |
| Main file path | `app.py` |

The repository does not require `docs/index.html` or a GitHub Pages build for deployment.

---

## Methodology Notes

**SEC data:** The EDGAR companyfacts API contains many overlapping reporting concepts. A manual concept map in `sql/01_create_fact_map.sql` selects the specific financial metrics used. Only annual 10-K and 10-K/A observations are used. Balance sheet facts are selected as point-in-time values; income statement and cash flow facts are filtered to annual-length periods.

**DCF model:** Intentionally transparent. Uses scenario assumptions for revenue growth (per year), operating margin, tax rate, D&A, CapEx intensity, working capital, WACC, and terminal growth. Output should be read as an assumption-based valuation exercise, not a prediction. The Monte Carlo layer adds probabilistic bounds using normally distributed growth and margin walks.

**SaaS unit economics:** Historical data for Office 365 and Xbox Game Pass (seats, ARPU, churn, CAC) is modelled from public disclosures and industry benchmarks. LTV is calculated as ARPU × gross margin / monthly churn rate. The cohort decay curve is a standard exponential retention model driven by the year's churn parameter.

**Health score:** A custom composite framework (0–100) built from profitability, liquidity, solvency, cash generation, and capital efficiency components. Not a credit rating or third-party analyst score.

**Competitor benchmarking:** Peer multiples (P/E, EV/EBITDA, P/S, ROIC, WACC) are sourced from public market data and used for relative valuation context only.

---

## Reality Check

This is a single-company public-data project. It does not include management guidance parsing, sell-side consensus estimates, live scheduling, intraday pricing, or audited reconciliation against every line item in Microsoft's 10-K. Natural extensions would include multi-company support, live data refresh, and segment-level SEC fact parsing.

---

## Portfolio Positioning

This project demonstrates practical skills across: financial statement analysis, SEC data engineering, SQL transformation pipelines, Python data science, probabilistic modelling (Monte Carlo), SaaS unit economics, competitive analysis, DCF valuation, and full-stack dashboard design. It is best described as a transparent, institutional-depth finance analytics workflow built entirely on public data.
