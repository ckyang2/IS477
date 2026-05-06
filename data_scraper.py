"""
Data Scraper for U.S. Federal Debt & Federal Funds Rate
========================================================
Sources:
  1. FRED - Federal Funds Effective Rate (FEDFUNDS)
     https://fred.stlouisfed.org/series/FEDFUNDS
  2. U.S. Treasury FiscalData - Historical Debt Outstanding
     https://fiscaldata.treasury.gov/datasets/historical-debt-outstanding/

Both datasets are retrieved via their official public APIs (no API key required
for Treasury; FRED requires a API key and will require a input or update to FRED_API_KEY
before running the code.

Output:
  - fedfunds.csv              — raw Federal Funds rate data
  - historical_debt.csv       — raw Historical Debt Outstanding data
  - merged_annual.csv         — datasets joined on fiscal/calendar year
"""

import requests
import pandas as pd
import time
import sys
from datetime import datetime
from pathlib import Path
from datetime import date
import csv

try:
    from config import (
    # Register free at https://fred.stlouisfed.org/docs/api/api_key.html
        FRED_API_KEY,
        DEBT_CSV_PATH,

    # ── Output file paths ────────────────────────────────────────────────────────
        OUTPUT_FEDFUNDS,
        OUTPUT_DEBT,
        OUTPUT_MERGED,
    )
except ImportError:
    # Register free at https://fred.stlouisfed.org/docs/api/api_key.html
    FRED_API_KEY = ""
    DEBT_CSV_PATH = "HstDebt.csv"

    # ── Output file paths ────────────────────────────────────────────────────────
    OUTPUT_FEDFUNDS = "fedfunds.csv"
    OUTPUT_DEBT = "historical_debt.csv"
    OUTPUT_MERGED = "merged_annual.csv"


# ════════════════════════════════════════════════════════════════════════════
# 1.  FRED — Federal Funds Effective Rate
# ════════════════════════════════════════════════════════════════════════════
 
def fetch_fedfunds() -> pd.DataFrame:
    """
    Retrieve the FEDFUNDS series from the FRED API, filtered from 1977
    to the most recent available year, aggregated as annual averages.

    Returns a DataFrame with columns:
        year        - observation year (int)
        fedfunds    - annual average effective federal funds rate (%)
    """
    print("Fetching Federal Funds Effective Rate from FRED ...")

    url = (
        "https://api.stlouisfed.org/fred/series/observations?series_id="
        f"FEDFUNDS&api_key={FRED_API_KEY}&file_type=json"
    )

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    payload = resp.json()

    observations = payload.get("observations", [])
    records = []
    for obs in observations:
        val = obs.get("value", ".")
        if val == ".":      # FRED uses "." for missing values
            continue
        records.append({"date": obs["date"], "fedfunds": float(val)})

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])

    # Filter to 1977 onward
    df = df[df["date"].dt.year >= 1977]

    # Aggregate to annual averages
    df = (
        df.groupby(df["date"].dt.year)["fedfunds"]
        .mean()
        .reset_index()
        .rename(columns={"date": "year"})
    )

    df = df.sort_values("year").reset_index(drop=True)
    df["fedfunds"] = df["fedfunds"].round(4)

    print(f"  -> {len(df):,} annual observations retrieved "
          f"({df['year'].min()} - {df['year'].max()})")
    return df

 
# ════════════════════════════════════════════════════════════════════════════
# 2.  Local CSV — Historical Debt Outstanding
# ════════════════════════════════════════════════════════════════════════════
 
def load_historical_debt(csv_path: str = DEBT_CSV_PATH) -> pd.DataFrame:
    """
    Load the Historical Debt Outstanding data from a local CSV file.
 
    Expected CSV columns (as downloaded from Treasury FiscalData):
        Record Date             - date of the annual debt figure
        Debt Outstanding Amount - total federal debt outstanding (USD)
 
    Returns a DataFrame with normalised columns:
        record_date          - date (datetime)
        debt_outstanding_amt - debt amount (float)
        fiscal_year          - derived fiscal year (int)
        fiscal_calendar_note - era label for the fiscal year calendar change
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Debt CSV not found at '{csv_path}'.\n"
            "Download it from: https://fiscaldata.treasury.gov/datasets/"
            "historical-debt-outstanding/\n"
            "and place it in the same directory as this script."
        )
 
    print(f"Loading Historical Debt Outstanding from '{csv_path}' ...")
 
    df = pd.read_csv(
        path,
        encoding="utf-8-sig",   # handles the BOM in the Treasury file
        parse_dates=["Record Date"],
    )
 
    # ── Normalise column names ────────────────────────────────────────────────
    df = df.rename(columns={
        "Record Date":             "record_date",
        "Debt Outstanding Amount": "debt_outstanding_amt",
    })
 
    df["debt_outstanding_amt"] = pd.to_numeric(
        df["debt_outstanding_amt"], errors="coerce"
    )
 
    # ── Derive fiscal year from the record date ───────────────────────────────
    # Each row is already one end-of-fiscal-year snapshot; the year component
    # of the record date represents the fiscal year across all three eras:
    #   - 1790-1842: FY ended Dec 31  (record month = 1, year = FY)
    #   - 1843-1976: FY ended Jun 30  (record month = 6, year = FY)
    #   - 1977-now:  FY ended Sep 30  (record month = 9, year = FY)
    df["fiscal_year"] = df["record_date"].dt.year
 
    # ── Fiscal calendar era label ─────────────────────────────────────────────
    df["fiscal_calendar_note"] = df["fiscal_year"].apply(
        lambda fy: (
            "FY=CY (Jan-Dec)"       if fy <= 1842 else
            "FY ends Jun (Jul-Jun)" if fy <= 1976 else
            "FY ends Sep (Oct-Sep)"
        )
    )
 
    df = df.sort_values("record_date").reset_index(drop=True)
    print(f"  -> {len(df):,} rows loaded "
          f"({df['record_date'].min().date()} - {df['record_date'].max().date()})")
    return df
 
 
# ════════════════════════════════════════════════════════════════════════════
# 3.  Merge on a common annual time key
# ════════════════════════════════════════════════════════════════════════════
 
def build_annual_fedfunds(df_ff: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate the monthly FEDFUNDS series to an annual average,
    using the calendar year of each observation.
    """
    # df = df_ff.copy()
    # df["calendar_year"] = df["date"].dt.year
    # annual = (
    #     df.groupby("calendar_year", as_index=False)
    #       .agg(
    #           fedfunds_annual_avg=("fedfunds", "mean"),
    #           fedfunds_annual_min=("fedfunds", "min"),
    #           fedfunds_annual_max=("fedfunds", "max"),
    #       )
    # )
    # return annual
    return df_ff.rename(columns={
        "year": "calendar_year",
        "fedfunds": "fedfunds_annual_avg"
    })
 
 
def merge_datasets(df_debt: pd.DataFrame, df_ff_annual: pd.DataFrame) -> pd.DataFrame:
    """
    Left-join the debt dataset with the annual FEDFUNDS aggregates on
    fiscal_year == calendar_year.
    
    NOTE on fiscal vs. calendar year alignment
    ------------------------------------------
    The Treasury's fiscal year end date has changed over time:
      - 1790-1842: FY ended Dec 31  -> FY == calendar year
      - 1843-1976: FY ended Jun 30  -> FY N covers Jul (N-1) through Jun N
      - 1977-now:  FY ended Sep 30  -> FY N covers Oct (N-1) through Sep N
    
    FEDFUNDS data only starts in 1954, so earlier debt rows will have
    NaN for the rate columns — expected and flagged via fiscal_calendar_note
    for downstream cleaning. This code will only keep fiscal year 1977 and after as 
    there is a change in reporting month.
    """
    merged = pd.merge(
        df_debt,
        df_ff_annual,
        left_on="fiscal_year",
        right_on="calendar_year",
        how="left",
    )
    merged = merged.drop(columns=["calendar_year"], errors="ignore")
    merged = merged[merged["fiscal_year"] >= 1977].reset_index(drop=True)
    return merged




def fetch_federal_receipts(api_key: str, output_file) -> str:
    """
    Fetch US Federal Receipts (FYFR) from FRED API from 1977 to today
    and write results to a CSV file.
 
    Args:
        output_file: Path/name of the output CSV file (default: 'federal_receipts.csv')
 
    Returns:
        Path to the written CSV file.
    """
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id":         "FYFR",
        "api_key":           api_key,
        "file_type":         "json",
        "observation_start": "1977-01-01",
        "observation_end":   date.today().isoformat(),
        "units":             "lin",          # levels (billions of dollars)
        "frequency":         "a",            # annual — FYFR is annual data
        "sort_order":        "asc",
    }
 
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
 
    data = response.json()
    observations = data.get("observations", [])
 
    if not observations:
        raise ValueError("No observations returned from FRED. Check your API key and series ID.")
 
    with open(output_file, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["date", "federal_receipts_billions_usd"])
        writer.writeheader()
        for obs in observations:
            # FRED uses "." for missing values — skip them
            if obs["value"] == ".":
                continue
            writer.writerow({
                "date":                           obs["date"],
                "federal_receipts_billions_usd":  obs["value"],
            })
 
    print(f"Done. {len(observations)} records written to '{output_file}'.")
    return output_file
 
 
# ── Example usage ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    YOUR_API_KEY = "YOUR_FRED_API_KEY_HERE"   # ← replace with your key
    fetch_federal_receipts(api_key=YOUR_API_KEY, output_file="federal_receipts.csv")