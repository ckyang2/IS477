from datetime import datetime
import sys
import requests
import pandas as pd
import time
from pathlib import Path
from data_scraper import (fetch_fedfunds, load_historical_debt, build_annual_fedfunds, merge_datasets)

from config import (
    FRED_API_KEY,
    DEBT_CSV_PATH,
    OUTPUT_FEDFUNDS,
    OUTPUT_DEBT,
    OUTPUT_MERGED,
    OUTPUT_ANALYSIS_DIR
)
from analysis import (
    load_data, 
    descriptive_stats, 
    simple_ols, 
    fig_debt_and_rate,
    fig_debt_growth,
    fig_interest_expense,
    fig_scatter_rate_vs_growth,
    fig_compounding, 
    fig_era_boxplot, 
    regression_analysis,
    era_summary,
    print_findings
)



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

    print("\n========================================================")
    print("  U.S. FEDERAL DEBT ANALYSIS")
    print("========================================================\n")

    df = load_data(OUTPUT_MERGED)

    # ── Text outputs ──────────────────────────────────────────────────────────
    descriptive_stats(df)
    era_summary(df)
    regression_analysis(df)
    print_findings(df)

    # ── Figures ───────────────────────────────────────────────────────────────
    print("Generating figures...")
    fig_debt_and_rate(df)
    fig_debt_growth(df)
    fig_interest_expense(df)
    fig_scatter_rate_vs_growth(df)
    fig_compounding(df)
    fig_era_boxplot(df)

    print("\nAll outputs written to:", OUTPUT_ANALYSIS_DIR)
    print("Done.\n")
if __name__ == "__main__":
    main()