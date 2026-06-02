import json
import os
from pathlib import Path

import duckdb
import pandas as pd
import requests
from dotenv import load_dotenv


# ----------------------------
# Project paths
# ----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
DB_DIR = PROJECT_ROOT / "database"

RAW_JSON_PATH = RAW_DIR / "sec_companyfacts_msft.json"
RAW_CSV_PATH = RAW_DIR / "raw_sec_facts_msft.csv"
DB_PATH = DB_DIR / "finance.duckdb"


# ----------------------------
# Microsoft details
# ----------------------------
TICKER = "MSFT"
COMPANY_NAME = "Microsoft Corporation"
CIK = "0000789019"


def get_headers() -> dict:
    """
    SEC expects automated requests to identify themselves.
    Store your User-Agent in .env as SEC_USER_AGENT.
    """
    load_dotenv(PROJECT_ROOT / ".env")

    user_agent = os.getenv("SEC_USER_AGENT")

    if not user_agent:
        raise ValueError(
            "Missing SEC_USER_AGENT in .env. "
            "Example: SEC_USER_AGENT='Your Name your_email@example.com'"
        )

    return {
        "User-Agent": user_agent,
        "Accept-Encoding": "gzip, deflate",
        "Host": "data.sec.gov"
    }


def fetch_company_facts(cik: str) -> dict:
    """
    Fetch full XBRL company facts from SEC EDGAR.
    """
    cik = str(cik).zfill(10)

    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

    response = requests.get(
        url,
        headers=get_headers(),
        timeout=30
    )

    response.raise_for_status()
    return response.json()


def save_raw_json(data: dict, output_path: Path) -> None:
    """
    Save original SEC response exactly as received.
    This is your raw data backup.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def flatten_company_facts(data: dict) -> pd.DataFrame:
    """
    Convert nested SEC companyfacts JSON into a flat table.

    SEC structure:
    facts -> taxonomy -> concept -> units -> observations
    """
    rows = []

    cik = data.get("cik")
    entity_name = data.get("entityName")

    facts = data.get("facts", {})

    for taxonomy, concepts in facts.items():
        for concept, concept_data in concepts.items():
            label = concept_data.get("label")
            description = concept_data.get("description")
            units = concept_data.get("units", {})

            for unit, observations in units.items():
                for obs in observations:
                    rows.append({
                        "ticker": TICKER,
                        "company_name": COMPANY_NAME,
                        "cik": str(cik).zfill(10),
                        "entity_name": entity_name,
                        "taxonomy": taxonomy,
                        "concept": concept,
                        "label": label,
                        "description": description,
                        "unit": unit,
                        "fy": obs.get("fy"),
                        "fp": obs.get("fp"),
                        "form": obs.get("form"),
                        "filed": obs.get("filed"),
                        "start_date": obs.get("start"),
                        "end_date": obs.get("end"),
                        "value": obs.get("val"),
                        "accession": obs.get("accn"),
                        "frame": obs.get("frame")
                    })

    return pd.DataFrame(rows)


def save_to_duckdb(df: pd.DataFrame, db_path: Path) -> None:
    """
    Save flattened SEC facts into DuckDB.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db_path))

    con.execute("DROP TABLE IF EXISTS raw_sec_facts")

    con.execute("""
        CREATE TABLE raw_sec_facts AS
        SELECT *
        FROM df
    """)

    con.close()


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    DB_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching Microsoft SEC companyfacts data...")
    raw_data = fetch_company_facts(CIK)

    print("Saving raw JSON...")
    save_raw_json(raw_data, RAW_JSON_PATH)

    print("Flattening SEC JSON...")
    df = flatten_company_facts(raw_data)

    print("Saving raw CSV...")
    df.to_csv(RAW_CSV_PATH, index=False)

    print("Loading raw facts into DuckDB...")
    save_to_duckdb(df, DB_PATH)

    print("\nCollection complete.")
    print(f"Raw JSON saved to: {RAW_JSON_PATH}")
    print(f"Raw CSV saved to:  {RAW_CSV_PATH}")
    print(f"DuckDB saved to:   {DB_PATH}")
    print(f"Rows collected:    {len(df):,}")
    print(f"Unique concepts:   {df['concept'].nunique():,}")
    print(f"Forms available:   {sorted(df['form'].dropna().unique())}")


if __name__ == "__main__":
    main()