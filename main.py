from datetime import datetime
import sys
import requests
import pandas as pd
import time
from pathlib import Path
from datetime import date
import csv

from data_scraper import (
    fetch_fedfunds, 
    load_historical_debt, 
    build_annual_fedfunds, 
    merge_datasets,
    fetch_federal_receipts
)

from config import (
    FRED_API_KEY,
    DEBT_CSV_PATH,
    OUTPUT_FEDFUNDS,
    OUTPUT_DEBT,
    OUTPUT_MERGED,
    OUTPUT_ANALYSIS_DIR,
    OUTPUT_FEDERAL_RECEIPT
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
    print_findings,
    fig_debt_vs_receipts,
    fig_debt_to_receipts_ratio,
    fig_deficit_proxy,
    fig_receipts_coverage,
    fig_receipts_rate_scatter,
    fig_receipts_growth_vs_debt_growth,
    merge_receipts,
    descriptive_stats_receipts,
    era_summary_receipts,
    regression_analysis_receipts,
    print_findings_receipts




)

# ── Stage 1: Data Acquisition ─────────────────────────────────────────────────
def stage_acquisition() -> None:
    """Fetch, clean, and save the debt and fed funds datasets."""
    print("=" * 60)
    print("STAGE 1 — Data Acquisition")
    print("=" * 60)

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

    df_fedfunds.to_csv(OUTPUT_FEDFUNDS, index=False)
    print(f"Saved FEDFUNDS data         -> {OUTPUT_FEDFUNDS}")

    df_debt.to_csv(OUTPUT_DEBT, index=False)
    print(f"Saved Historical Debt data  -> {OUTPUT_DEBT}")

    print("\nBuilding annual FEDFUNDS summary and merging ...")
    df_ff_annual = build_annual_fedfunds(df_fedfunds)
    df_merged    = merge_datasets(df_debt, df_ff_annual)

    df_merged.to_csv(OUTPUT_MERGED, index=False)
    print(f"Saved merged annual dataset -> {OUTPUT_MERGED}")

    print("\n-- Merged dataset preview (most recent 10 rows) --")
    import pandas as pd
    pd.set_option("display.float_format", "{:,.2f}".format)
    pd.set_option("display.max_columns", 10)
    pd.set_option("display.width", 120)
    print(df_merged.tail(10).to_string(index=False))

    overlap = df_merged.dropna(subset=["fedfunds_annual_avg"])
    print(f"\nRows with FEDFUNDS data: {len(overlap)} "
          f"(FY {int(overlap['fiscal_year'].min())}–"
          f"{int(overlap['fiscal_year'].max())})")


# ── Stage 2: Federal Receipts ─────────────────────────────────────────────────
def stage_receipts() -> None:
    """Fetch the FYFR federal receipts series from FRED and save to CSV."""
    print("\n" + "=" * 60)
    print("STAGE 2 — Federal Receipts")
    print("=" * 60)

    try:
        fetch_federal_receipts(
            api_key=FRED_API_KEY,
            output_file=OUTPUT_FEDERAL_RECEIPT,
        )
        print(f"Saved federal receipts      -> {OUTPUT_FEDERAL_RECEIPT}")
    except Exception as exc:
        print(f"ERROR fetching federal receipts: {exc}", file=sys.stderr)
        raise


# ── Stage 3: Analysis ─────────────────────────────────────────────────────────
def stage_analysis() -> None:
    """Run all descriptive stats, regressions, and figures."""
    print("\n" + "=" * 60)
    print("STAGE 3 — Analysis")
    print("=" * 60)

    Path(OUTPUT_ANALYSIS_DIR).mkdir(parents=True, exist_ok=True)

    # Load base dataset then merge receipts
    df = load_data(OUTPUT_MERGED)
    df = merge_receipts(df, OUTPUT_FEDERAL_RECEIPT)

    # ── Descriptive statistics ────────────────────────────────────────────────
    descriptive_stats(df)
    descriptive_stats_receipts(df)

    # ── Era summaries ─────────────────────────────────────────────────────────
    era_summary(df)
    era_summary_receipts(df)

    # ── Regression analyses ───────────────────────────────────────────────────
    regression_analysis(df)
    regression_analysis_receipts(df)

    # ── Key findings ──────────────────────────────────────────────────────────
    print_findings(df)
    print_findings_receipts(df)

    # ── Figures ───────────────────────────────────────────────────────────────
    print("Generating figures ...")

    # Original set
    fig_debt_and_rate(df)
    fig_debt_growth(df)
    fig_interest_expense(df)
    fig_scatter_rate_vs_growth(df)
    fig_compounding(df)
    fig_era_boxplot(df)

    # Receipts set
    fig_debt_vs_receipts(df)
    fig_debt_to_receipts_ratio(df)
    fig_deficit_proxy(df)
    fig_receipts_coverage(df)
    fig_receipts_rate_scatter(df)
    fig_receipts_growth_vs_debt_growth(df)

    print(f"\nAll outputs written to: {OUTPUT_ANALYSIS_DIR}")


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    print("=" * 60)
    print("U.S. Federal Debt Analysis Pipeline")
    print(f"Run timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    stage_acquisition()
    stage_receipts()
    stage_analysis()

    print("\nDone.\n")


if __name__ == "__main__":
    main()
