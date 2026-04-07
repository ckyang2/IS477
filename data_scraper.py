"""
Data Scraper for U.S. Federal Debt & Federal Funds Rate
========================================================
Sources:
  1. FRED - Federal Funds Effective Rate (FEDFUNDS)
     https://fred.stlouisfed.org/series/FEDFUNDS
  2. U.S. Treasury FiscalData - Historical Debt Outstanding
     https://fiscaldata.treasury.gov/datasets/historical-debt-outstanding/

Both datasets are retrieved via their official public APIs (no API key required
for Treasury; FRED works without a key but supports one for higher rate limits).

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

# ── Optional: set your FRED API key here for higher rate limits ──────────────
# Register free at https://fred.stlouisfed.org/docs/api/api_key.html
# FRED_API_KEY = str(input())
FRED_API_KEY = "2b05271cfc46ff0885edbc9ed0335246"   # leave empty to use the public (no-key) endpoint
DEBT_CSV_PATH = "/Users/jonathanyang/Downloads/IS_477/HstDebt_17900101_20250930.csv"

# ── Output file paths ────────────────────────────────────────────────────────
OUTPUT_FEDFUNDS      = "fedfunds.csv"
OUTPUT_DEBT          = "historical_debt.csv"
OUTPUT_MERGED        = "merged_annual.csv"


# ════════════════════════════════════════════════════════════════════════════
# 1.  FRED — Federal Funds Effective Rate
# ════════════════════════════════════════════════════════════════════════════
 
def fetch_fedfunds() -> pd.DataFrame:
    """
    Retrieve the full FEDFUNDS series from the FRED API.
 
    Returns a DataFrame with columns:
        date        – observation date (datetime)
        fedfunds    – effective federal funds rate (%)
    """
    print("Fetching Federal Funds Effective Rate from FRED ...")
 
    if FRED_API_KEY:
        url = (
            "https://api.stlouisfed.org/fred/series/observations"
            f"?series_id=FEDFUNDS&api_key={FRED_API_KEY}&file_type=json"
        )
    else:
        # Publicly accessible JSON endpoint — no key needed
        url = (
            "https://fred.stlouisfed.org/graph/fredgraph.json"
            "?id=FEDFUNDS"
        )
 
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
 
    # ── Parse response depending on which endpoint was used ─────────────────
    if FRED_API_KEY:
        # Official API returns {"observations": [{"date": "...", "value": "..."}, ...]}
        observations = payload.get("observations", [])
        records = []
        for obs in observations:
            val = obs.get("value", ".")
            if val == ".":      # FRED uses "." for missing values
                continue
            records.append({"date": obs["date"], "fedfunds": float(val)})
        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"])
    else:
        # Public endpoint returns a list of [timestamp_ms, value] pairs
        obs_raw = payload.get("observations", payload)
        records = []
        for item in obs_raw:
            ts_ms, val = item[0], item[1]
            if val is None:
                continue
            records.append({
                "date":     pd.to_datetime(ts_ms, unit="ms"),
                "fedfunds": float(val),
            })
        df = pd.DataFrame(records)
 
    df = df.sort_values("date").reset_index(drop=True)
    print(f"  -> {len(df):,} observations retrieved "
          f"({df['date'].min().date()} - {df['date'].max().date()})")
    return df
 
 
# ════════════════════════════════════════════════════════════════════════════
# 2.  Local CSV — Historical Debt Outstanding
# ════════════════════════════════════════════════════════════════════════════
 
def load_historical_debt(csv_path: str = DEBT_CSV_PATH) -> pd.DataFrame:
    """
    Load the Historical Debt Outstanding data from a local CSV file.
 
    Expected CSV columns (as downloaded from Treasury FiscalData):
        Record Date             – date of the annual debt figure
        Debt Outstanding Amount – total federal debt outstanding (USD)
 
    Returns a DataFrame with normalised columns:
        record_date          – date (datetime)
        debt_outstanding_amt – debt amount (float)
        fiscal_year          – derived fiscal year (int)
        fiscal_calendar_note – era label for the fiscal year calendar change
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
    df = df_ff.copy()
    df["calendar_year"] = df["date"].dt.year
    annual = (
        df.groupby("calendar_year", as_index=False)
          .agg(
              fedfunds_annual_avg=("fedfunds", "mean"),
              fedfunds_annual_min=("fedfunds", "min"),
              fedfunds_annual_max=("fedfunds", "max"),
          )
    )
    return annual
 
 
def merge_datasets(df_debt: pd.DataFrame,
                   df_ff_annual: pd.DataFrame) -> pd.DataFrame:
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
    for downstream cleaning.
    """
    merged = pd.merge(
        df_debt,
        df_ff_annual,
        left_on="fiscal_year",
        right_on="calendar_year",
        how="left",
    )
    merged = merged.drop(columns=["calendar_year"], errors="ignore")
    return merged
 
 
# ════════════════════════════════════════════════════════════════════════════
# 4.  Main
# ════════════════════════════════════════════════════════════════════════════
 
def main():
    print("=" * 60)
    print("U.S. Federal Debt & Federal Funds Rate — Data Retriever")
    print(f"Run timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
 
    # ── Fetch / load ─────────────────────────────────────────────────────────
    try:
        df_fedfunds = fetch_fedfunds()
    except Exception as exc:
        print(f"ERROR fetching FEDFUNDS: {exc}", file=sys.stderr)
        raise
 
    try:
        df_debt = load_historical_debt(DEBT_CSV_PATH)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
 
    # ── Save raw / cleaned files ─────────────────────────────────────────────
    df_fedfunds.to_csv(OUTPUT_FEDFUNDS, index=False)
    print(f"\nSaved FEDFUNDS data        -> {OUTPUT_FEDFUNDS}")
 
    df_debt.to_csv(OUTPUT_DEBT, index=False)
    print(f"Saved Historical Debt data -> {OUTPUT_DEBT}")
 
    # ── Aggregate & merge ────────────────────────────────────────────────────
    print("\nBuilding annual FEDFUNDS summary and merging ...")
    df_ff_annual = build_annual_fedfunds(df_fedfunds)
    df_merged    = merge_datasets(df_debt, df_ff_annual)
 
    df_merged.to_csv(OUTPUT_MERGED, index=False)
    print(f"Saved merged annual dataset -> {OUTPUT_MERGED}")
 
    # ── Quick summary ────────────────────────────────────────────────────────
    print("\n-- Merged dataset preview (most recent 10 rows) --")
    pd.set_option("display.float_format", "{:,.2f}".format)
    pd.set_option("display.max_columns", 10)
    pd.set_option("display.width", 120)
    print(df_merged.tail(10).to_string(index=False))
 
    print("\n-- Column dtypes --")
    print(df_merged.dtypes)
 
    overlap = df_merged.dropna(subset=["fedfunds_annual_avg"])
    print(f"\n-- Rows with FEDFUNDS data: {len(overlap)} "
          f"(fiscal years {int(overlap['fiscal_year'].min())}-"
          f"{int(overlap['fiscal_year'].max())}) --")
 
    print("\nDone.")
 
 
if __name__ == "__main__":
    main()
 