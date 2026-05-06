"""
analysis.py
===========
U.S. Federal Debt Analysis
Authors: Jonathan Yang & Louis Wen

Research Question:
    How do changes in U.S. government spending, tax revenue, and interest rates
    influence the growth of outstanding federal debt over time?

Supporting Questions:
    1. What relationship exists between federal spending and increases in
       outstanding national debt?
    2. How does tax revenue affect budget deficits and debt growth?
    3. How do interest rate changes impact government interest payments and
       debt sustainability?
    4. To what extent do spending, revenue, and interest rates together explain
       long-term trends in U.S. federal debt?
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy import stats
import warnings

warnings.filterwarnings("ignore")

from config import (
    OUTPUT_MERGED,
    OUTPUT_ANALYSIS_DIR
)

# ── Configuration ─────────────────────────────────────────────────────────────
DATA_PATH = OUTPUT_MERGED   # path to the merged CSV
OUTPUT_DIR = OUTPUT_ANALYSIS_DIR                 # where to save figures (change if needed)

# Colour palette (colourblind-friendly)
C_DEBT   = "#1f77b4"   # blue
C_RATE   = "#d62728"   # red
C_GROWTH = "#2ca02c"   # green
C_IEXP   = "#ff7f0e"   # orange
C_RATIO  = "#9467bd"   # purple


# ── 1. Load & Clean ───────────────────────────────────────────────────────────
def load_data(path: str) -> pd.DataFrame:
    """Load the merged annual CSV and derive key analytical columns."""
    df = pd.read_csv(path, parse_dates=["record_date"])

    # Rename for convenience
    df = df.rename(columns={
        "debt_outstanding_amt": "debt",
        "fedfunds_annual_avg":  "fed_rate",
        "fiscal_year":          "year",
    })

    df = df.sort_values("year").reset_index(drop=True)

    # ── Derived columns ──────────────────────────────────────────────────────

    # Debt in trillions (easier to read on charts)
    df["debt_T"] = df["debt"] / 1e12

    # Year-over-year dollar change in debt
    df["debt_yoy_change"] = df["debt"].diff()

    # YoY percentage growth rate
    df["debt_growth_pct"] = df["debt"].pct_change() * 100

    # Estimated annual interest expense  =  debt(t-1) × fed_rate(t) / 100
    # This approximates what was owed on the *prior year's* outstanding balance.
    df["est_interest_expense"] = df["debt"].shift(1) * (df["fed_rate"] / 100)
    df["est_interest_expense_T"] = df["est_interest_expense"] / 1e12

    # Debt-to-prior-debt ratio (compounding factor)
    df["compounding_factor"] = df["debt"] / df["debt"].iloc[0]

    # Rolling 5-year average growth rate
    df["rolling5_growth"] = df["debt_growth_pct"].rolling(5, min_periods=3).mean()

    # Lag of fed_rate (rate in prior year, useful for lagged regression)
    df["fed_rate_lag1"] = df["fed_rate"].shift(1)

    # Flag notable black-swan periods
    df["era"] = pd.cut(
        df["year"],
        bins=[1976, 1989, 2001, 2009, 2019, 2030],
        labels=["Reagan/Bush", "Clinton/Bush", "GFC Buildup", "Post-GFC", "COVID/Recent"],
    )

    return df


# ── 2. Descriptive Statistics ─────────────────────────────────────────────────
def descriptive_stats(df: pd.DataFrame) -> None:
    """Print a concise summary of the key variables."""
    print("=" * 65)
    print("DESCRIPTIVE STATISTICS")
    print("=" * 65)

    cols = ["debt_T", "fed_rate", "debt_growth_pct", "est_interest_expense_T"]
    labels = {
        "debt_T":                  "Debt Outstanding ($ Trillions)",
        "fed_rate":                "Fed Funds Rate (%)",
        "debt_growth_pct":         "YoY Debt Growth (%)",
        "est_interest_expense_T":  "Est. Interest Expense ($ Trillions)",
    }

    summary = df[cols].describe().T
    summary.index = [labels[c] for c in cols]
    print(summary.round(3).to_string())

    print("\nCorrelation Matrix (key variables):")
    corr_cols = ["debt_T", "fed_rate", "debt_growth_pct", "est_interest_expense_T"]
    corr = df[corr_cols].corr()
    corr.index  = [labels[c] for c in corr_cols]
    corr.columns = [labels[c] for c in corr_cols]
    print(corr.round(3).to_string())
    print()


# ── 3. Regression Helper ──────────────────────────────────────────────────────
def simple_ols(x: pd.Series, y: pd.Series, label_x: str, label_y: str) -> None:
    """Run a simple OLS regression and print results."""
    mask = x.notna() & y.notna()
    x_c, y_c = x[mask], y[mask]
    slope, intercept, r, p, se = stats.linregress(x_c, y_c)
    print(f"  OLS: {label_y} ~ {label_x}")
    print(f"       slope={slope:.4f}  intercept={intercept:.4f}")
    print(f"       R²={r**2:.4f}  p-value={p:.4f}  (n={mask.sum()})")


# ── 4. Visualisations ─────────────────────────────────────────────────────────
def fig_debt_and_rate(df: pd.DataFrame) -> None:
    """Fig 1 – Dual-axis: Debt outstanding vs. Fed Funds Rate over time."""
    fig, ax1 = plt.subplots(figsize=(12, 5))

    ax1.fill_between(df["year"], df["debt_T"], alpha=0.25, color=C_DEBT)
    ax1.plot(df["year"], df["debt_T"], color=C_DEBT, lw=2, label="Debt Outstanding")
    ax1.set_ylabel("Federal Debt ($ Trillions)", color=C_DEBT)
    ax1.tick_params(axis="y", labelcolor=C_DEBT)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.0f}T"))

    ax2 = ax1.twinx()
    ax2.plot(df["year"], df["fed_rate"], color=C_RATE, lw=2,
             linestyle="--", label="Fed Funds Rate")
    ax2.set_ylabel("Fed Funds Rate (%)", color=C_RATE)
    ax2.tick_params(axis="y", labelcolor=C_RATE)

    # Shade notable eras
    shades = [
        (2008, 2010, "GFC", "lightgrey"),
        (2020, 2021, "COVID", "lightyellow"),
    ]
    for start, end, label, color in shades:
        ax1.axvspan(start, end, alpha=0.3, color=color, label=label)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8)

    ax1.set_title("U.S. Federal Debt Outstanding vs. Fed Funds Rate (FY 1977–2025)",
                  fontsize=13, fontweight="bold")
    ax1.set_xlabel("Fiscal Year")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/fig1_debt_vs_rate.png", dpi=150)
    plt.close()
    print("Saved: fig1_debt_vs_rate.png")


def fig_debt_growth(df: pd.DataFrame) -> None:
    """Fig 2 – YoY debt growth % with rolling 5-year average."""
    fig, ax = plt.subplots(figsize=(12, 4))

    ax.bar(df["year"], df["debt_growth_pct"], color=C_GROWTH, alpha=0.6,
           label="YoY Growth %")
    ax.plot(df["year"], df["rolling5_growth"], color="black", lw=2,
            linestyle="-", label="5-Year Rolling Avg")
    ax.axhline(0, color="grey", lw=0.8, linestyle=":")

    ax.set_title("Year-over-Year Growth in Federal Debt (FY 1978–2025)",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Fiscal Year")
    ax.set_ylabel("Growth (%)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))
    ax.legend()
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/fig2_debt_growth.png", dpi=150)
    plt.close()
    print("Saved: fig2_debt_growth.png")


def fig_interest_expense(df: pd.DataFrame) -> None:
    """Fig 3 – Estimated annual interest expense vs. debt growth."""
    clean = df.dropna(subset=["est_interest_expense_T", "debt_yoy_change"])

    fig, ax1 = plt.subplots(figsize=(12, 5))
    ax1.bar(clean["year"], clean["est_interest_expense_T"],
            color=C_IEXP, alpha=0.7, label="Est. Interest Expense")
    ax1.set_ylabel("Est. Interest Expense ($ Trillions)", color=C_IEXP)
    ax1.tick_params(axis="y", labelcolor=C_IEXP)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.1f}T"))

    ax2 = ax1.twinx()
    yoy_T = clean["debt_yoy_change"] / 1e12
    ax2.plot(clean["year"], yoy_T, color=C_DEBT, lw=2, marker="o",
             markersize=4, label="YoY Debt Change")
    ax2.set_ylabel("YoY Debt Change ($ Trillions)", color=C_DEBT)
    ax2.tick_params(axis="y", labelcolor=C_DEBT)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8)

    ax1.set_title(
        "Estimated Annual Interest Expense vs. Year-over-Year Debt Growth",
        fontsize=13, fontweight="bold",
    )
    ax1.set_xlabel("Fiscal Year")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/fig3_interest_expense.png", dpi=150)
    plt.close()
    print("Saved: fig3_interest_expense.png")


def fig_scatter_rate_vs_growth(df: pd.DataFrame) -> None:
    """Fig 4 – Scatter: Fed Funds Rate vs. Debt Growth % (coloured by era)."""
    clean = df.dropna(subset=["fed_rate", "debt_growth_pct", "era"])

    era_colors = {
        "Reagan/Bush":  "#e41a1c",
        "Clinton/Bush": "#377eb8",
        "GFC Buildup":  "#4daf4a",
        "Post-GFC":     "#984ea3",
        "COVID/Recent": "#ff7f00",
    }

    fig, ax = plt.subplots(figsize=(8, 6))
    for era, grp in clean.groupby("era", observed=True):
        ax.scatter(grp["fed_rate"], grp["debt_growth_pct"],
                   label=str(era), color=era_colors.get(str(era), "grey"),
                   s=70, edgecolors="white", linewidths=0.5, zorder=3)
        for _, row in grp.iterrows():
            ax.annotate(str(int(row["year"])),
                        (row["fed_rate"], row["debt_growth_pct"]),
                        fontsize=6, alpha=0.6)

    # Overall regression line
    mask = clean["fed_rate"].notna() & clean["debt_growth_pct"].notna()
    slope, intercept, r, p, _ = stats.linregress(
        clean.loc[mask, "fed_rate"], clean.loc[mask, "debt_growth_pct"]
    )
    x_line = np.linspace(clean["fed_rate"].min(), clean["fed_rate"].max(), 200)
    ax.plot(x_line, slope * x_line + intercept, "k--", lw=1.5,
            label=f"OLS (R²={r**2:.2f}, p={p:.3f})")

    ax.set_xlabel("Fed Funds Rate (%)")
    ax.set_ylabel("YoY Debt Growth (%)")
    ax.set_title("Fed Funds Rate vs. Annual Debt Growth Rate",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=8)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/fig4_scatter_rate_vs_growth.png", dpi=150)
    plt.close()
    print("Saved: fig4_scatter_rate_vs_growth.png")


def fig_compounding(df: pd.DataFrame) -> None:
    """Fig 5 – Cumulative compounding of debt from the 1977 base."""
    fig, ax = plt.subplots(figsize=(12, 4))
    base_debt = df["debt_T"].iloc[0]

    ax.plot(df["year"], df["debt_T"], color=C_DEBT, lw=2.5, label="Actual Debt")

    # Hypothetical path at a constant 4 % growth (long-run nominal GDP proxy)
    const_growth = [base_debt * (1.04 ** i) for i in range(len(df))]
    ax.plot(df["year"], const_growth, color="grey", lw=1.5, linestyle="--",
            label="Hypothetical 4%/yr Growth")

    ax.fill_between(df["year"], const_growth, df["debt_T"],
                    where=(df["debt_T"] > const_growth),
                    interpolate=True, alpha=0.15, color=C_DEBT,
                    label="Excess debt accumulation")

    ax.set_title("Actual Debt vs. Hypothetical Constant 4%/yr Growth (Base: FY 1977)",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Fiscal Year")
    ax.set_ylabel("Federal Debt ($ Trillions)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.0f}T"))
    ax.legend()
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/fig5_compounding.png", dpi=150)
    plt.close()
    print("Saved: fig5_compounding.png")


def fig_era_boxplot(df: pd.DataFrame) -> None:
    """Fig 6 – Box plot of debt growth % by era."""
    clean = df.dropna(subset=["debt_growth_pct", "era"])
    eras = clean["era"].cat.categories.tolist()
    data = [clean.loc[clean["era"] == e, "debt_growth_pct"].values for e in eras]

    fig, ax = plt.subplots(figsize=(10, 5))
    bp = ax.boxplot(data, patch_artist=True, notch=False)
    colors = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00"]
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    ax.set_xticklabels(eras, rotation=15, ha="right")
    ax.set_ylabel("YoY Debt Growth (%)")
    ax.set_title("Distribution of Annual Debt Growth by Historical Era",
                 fontsize=13, fontweight="bold")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))
    ax.axhline(df["debt_growth_pct"].mean(), color="black", lw=1, linestyle="--",
               label=f"Overall mean ({df['debt_growth_pct'].mean():.1f}%)")
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/fig6_era_boxplot.png", dpi=150)
    plt.close()
    print("Saved: fig6_era_boxplot.png")


# ── 5. Regression Analysis ────────────────────────────────────────────────────
def regression_analysis(df: pd.DataFrame) -> None:
    """Supporting question regressions and printed results."""
    print("=" * 65)
    print("REGRESSION ANALYSIS")
    print("=" * 65)

    print("\n[SQ3] Fed Funds Rate → YoY Debt Growth %")
    simple_ols(df["fed_rate"], df["debt_growth_pct"],
               "Fed Funds Rate (%)", "Debt Growth %")

    print("\n[SQ3-lag] Lagged Fed Funds Rate (t-1) → Debt Growth % (t)")
    simple_ols(df["fed_rate_lag1"], df["debt_growth_pct"],
               "Fed Rate (lag 1yr)", "Debt Growth %")

    print("\n[SQ3] Fed Funds Rate → Est. Interest Expense ($T)")
    simple_ols(df["fed_rate"], df["est_interest_expense_T"],
               "Fed Funds Rate (%)", "Est. Interest Expense $T")

    print("\n[SQ1/SQ4] Debt level → YoY Dollar Change in Debt")
    simple_ols(df["debt_T"], df["debt_yoy_change"] / 1e12,
               "Debt Level ($T)", "YoY Debt Change ($T)")

    print()


# ── 6. Era Summary Table ──────────────────────────────────────────────────────
def era_summary(df: pd.DataFrame) -> None:
    """Print per-era summary statistics."""
    print("=" * 65)
    print("ERA SUMMARY")
    print("=" * 65)
    summary = (
        df.dropna(subset=["era"])
        .groupby("era", observed=True)
        .agg(
            years=("year", "count"),
            avg_debt_growth=("debt_growth_pct", "mean"),
            avg_fed_rate=("fed_rate", "mean"),
            avg_interest_exp=("est_interest_expense_T", "mean"),
            total_debt_added_T=("debt_yoy_change", lambda x: x.sum() / 1e12),
        )
        .round(2)
    )
    summary.columns = [
        "Years", "Avg Debt Growth %", "Avg Fed Rate %",
        "Avg Int. Expense $T", "Total Debt Added $T",
    ]
    print(summary.to_string())
    print()


# ── 7. Key Findings Summary ───────────────────────────────────────────────────
def print_findings(df: pd.DataFrame) -> None:
    """Print a concise narrative of key findings."""
    print("=" * 65)
    print("KEY FINDINGS SUMMARY")
    print("=" * 65)

    total_growth = (df["debt"].iloc[-1] / df["debt"].iloc[0] - 1) * 100
    peak_growth_yr = df.loc[df["debt_growth_pct"].idxmax(), "year"]
    peak_growth_val = df["debt_growth_pct"].max()
    highest_rate_yr = df.loc[df["fed_rate"].idxmax(), "year"]
    highest_rate_val = df["fed_rate"].max()
    lowest_rate_yr  = df.loc[df["fed_rate"].idxmin(), "year"]
    lowest_rate_val = df["fed_rate"].min()

    print(f"  Period covered     : FY {df['year'].min()} – FY {df['year'].max()}")
    print(f"  Total debt growth  : {total_growth:.1f}% ({df['debt_T'].iloc[0]:.2f}T → {df['debt_T'].iloc[-1]:.2f}T)")
    print(f"  Highest growth yr  : FY {peak_growth_yr} ({peak_growth_val:.1f}%)")
    print(f"  Highest fed rate   : FY {highest_rate_yr} ({highest_rate_val:.2f}%)")
    print(f"  Lowest fed rate    : FY {lowest_rate_yr} ({lowest_rate_val:.2f}%)")

    # Correlation
    mask = df["fed_rate"].notna() & df["debt_growth_pct"].notna()
    r, p = stats.pearsonr(df.loc[mask, "fed_rate"], df.loc[mask, "debt_growth_pct"])
    direction = "negative" if r < 0 else "positive"
    sig = "statistically significant" if p < 0.05 else "not statistically significant"
    print(f"\n  Pearson r (rate vs. debt growth) = {r:.3f} ({direction}, {sig}, p={p:.3f})")
    print("  Interpretation: In the modern era, LOWER rates correlate with HIGHER")
    print("  debt growth — consistent with post-crisis stimulus spending driving debt,")
    print("  not the rate itself causing growth.")
    print()


# ── 8. Load & Merge Federal Receipts ─────────────────────────────────────────
def load_receipts(path: str) -> pd.DataFrame:
    """
    Load the federal receipts CSV and return a clean annual DataFrame.
 
    Expects columns: date, federal_receipts_billions_usd
    The FRED FYFR series reports in *millions* of dollars despite the column
    name — values like 355559 for 1977 are millions, not billions.
    We normalise to trillions for consistency with the debt figures.
    """
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.rename(columns={"federal_receipts_billions_usd": "receipts_raw"})
    df["receipts_raw"] = pd.to_numeric(df["receipts_raw"], errors="coerce")
 
    # FRED FYFR is in millions of USD → convert to trillions
    df["receipts_T"] = df["receipts_raw"] / 1e6
 
    # Derive fiscal year from the September 30 record date
    df["year"] = df["date"].dt.year
 
    return df[["year", "receipts_T"]].dropna().sort_values("year").reset_index(drop=True)
 
 
def merge_receipts(df: pd.DataFrame, receipts_path: str) -> pd.DataFrame:
    """
    Left-join the main analytical DataFrame with federal receipts on fiscal year.
    Adds columns:
        receipts_T          – annual federal receipts ($ trillions)
        deficit_T           – debt_yoy_change minus receipts (simple deficit proxy, $T)
        receipts_coverage   – receipts / debt_yoy_change (how much of new debt receipts cover)
        debt_to_receipts    – total debt / annual receipts (years-of-revenue ratio)
        receipts_growth_pct – YoY growth in receipts (%)
    """
    rec = load_receipts(receipts_path)
    df  = df.merge(rec, on="year", how="left")
 
    # Deficit proxy: annual debt increase minus receipts collected
    df["deficit_T"] = (df["debt_yoy_change"] / 1e12) - df["receipts_T"]
 
    # How many cents of new borrowing are covered by each dollar of receipts
    df["receipts_coverage"] = df["receipts_T"] / (df["debt_yoy_change"] / 1e12)
 
    # Debt-to-receipts ratio: years of revenue needed to retire total debt
    df["debt_to_receipts"] = df["debt_T"] / df["receipts_T"]
 
    # YoY receipts growth
    df["receipts_growth_pct"] = df["receipts_T"].pct_change() * 100
 
    return df
 
 
# ── 9. Descriptive Stats (extended with receipts) ─────────────────────────────
def descriptive_stats_receipts(df: pd.DataFrame) -> None:
    """Print summary statistics for the receipts-related columns."""
    print("=" * 65)
    print("DESCRIPTIVE STATISTICS — FEDERAL RECEIPTS")
    print("=" * 65)
 
    cols = ["receipts_T", "deficit_T", "debt_to_receipts", "receipts_growth_pct"]
    labels = {
        "receipts_T":          "Federal Receipts ($ Trillions)",
        "deficit_T":           "Deficit Proxy ($T debt added − receipts)",
        "debt_to_receipts":    "Debt-to-Receipts Ratio (×)",
        "receipts_growth_pct": "YoY Receipts Growth (%)",
    }
    available = [c for c in cols if c in df.columns]
    summary = df[available].describe().T
    summary.index = [labels[c] for c in available]
    print(summary.round(3).to_string())
 
    print("\nCorrelation with debt variables:")
    corr_cols = ["receipts_T", "debt_T", "debt_growth_pct", "deficit_T", "debt_to_receipts"]
    corr_cols = [c for c in corr_cols if c in df.columns]
    corr = df[corr_cols].corr()
    corr.columns = corr.index = corr_cols
    print(corr.round(3).to_string())
    print()
 
 
# ── 10. Receipts Visualisations ───────────────────────────────────────────────
def fig_debt_vs_receipts(df: pd.DataFrame) -> None:
    """
    Fig 7 – Dual-axis line: Debt outstanding vs. Federal Receipts.
    Highlights the widening gap between the two series.
    """
    clean = df.dropna(subset=["receipts_T"])
 
    fig, ax1 = plt.subplots(figsize=(12, 5))
 
    ax1.fill_between(clean["year"], clean["debt_T"], alpha=0.15, color=C_DEBT)
    ax1.plot(clean["year"], clean["debt_T"], color=C_DEBT, lw=2.5,
             label="Debt Outstanding")
    ax1.set_ylabel("Federal Debt ($ Trillions)", color=C_DEBT)
    ax1.tick_params(axis="y", labelcolor=C_DEBT)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.0f}T"))
 
    ax2 = ax1.twinx()
    ax2.plot(clean["year"], clean["receipts_T"], color=C_GROWTH, lw=2.5,
             linestyle="--", label="Federal Receipts")
    ax2.set_ylabel("Federal Receipts ($ Trillions)", color=C_GROWTH)
    ax2.tick_params(axis="y", labelcolor=C_GROWTH)
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.1f}T"))
 
    # Shade crisis periods
    for start, end, lbl, col in [(2008, 2010, "GFC", "lightgrey"),
                                  (2020, 2021, "COVID", "lightyellow")]:
        ax1.axvspan(start, end, alpha=0.3, color=col, label=lbl)
 
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8)
 
    ax1.set_title("U.S. Federal Debt Outstanding vs. Federal Receipts (FY 1977–2025)",
                  fontsize=13, fontweight="bold")
    ax1.set_xlabel("Fiscal Year")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/fig7_debt_vs_receipts.png", dpi=150)
    plt.close()
    print("Saved: fig7_debt_vs_receipts.png")
 
 
def fig_debt_to_receipts_ratio(df: pd.DataFrame) -> None:
    """
    Fig 8 – Debt-to-receipts ratio over time.
    Shows how many years of total revenue would be needed to retire the debt.
    """
    clean = df.dropna(subset=["debt_to_receipts"])
 
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.fill_between(clean["year"], clean["debt_to_receipts"], alpha=0.2, color=C_RATIO)
    ax.plot(clean["year"], clean["debt_to_receipts"], color=C_RATIO, lw=2.5)
 
    # Annotate key years
    for yr in [1981, 2000, 2009, 2020, clean["year"].iloc[-1]]:
        row = clean[clean["year"] == yr]
        if not row.empty:
            val = row["debt_to_receipts"].values[0]
            ax.annotate(f"{yr}\n{val:.1f}×",
                        xy=(yr, val),
                        xytext=(yr + 0.5, val + 0.3),
                        fontsize=7, color=C_RATIO,
                        arrowprops=dict(arrowstyle="-", color=C_RATIO, lw=0.8))
 
    ax.axhline(clean["debt_to_receipts"].mean(), color="black", lw=1,
               linestyle="--",
               label=f"Period mean ({clean['debt_to_receipts'].mean():.1f}×)")
 
    ax.set_title("Debt-to-Receipts Ratio: Years of Revenue Required to Retire Federal Debt",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Fiscal Year")
    ax.set_ylabel("Ratio (×)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}×"))
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/fig8_debt_to_receipts_ratio.png", dpi=150)
    plt.close()
    print("Saved: fig8_debt_to_receipts_ratio.png")
 
 
def fig_deficit_proxy(df: pd.DataFrame) -> None:
    """
    Fig 9 – Stacked bar: annual debt added (deficit proxy) vs. federal receipts.
    Visualises supporting question 2: how does revenue relate to deficit growth?
    """
    clean = df.dropna(subset=["receipts_T", "deficit_T"]).copy()
    debt_added = clean["debt_yoy_change"] / 1e12
 
    fig, ax = plt.subplots(figsize=(13, 5))
 
    bar_w = 0.4
    x = np.arange(len(clean))
 
    ax.bar(x - bar_w / 2, debt_added, width=bar_w, color=C_RATE,
           alpha=0.75, label="Annual Debt Added ($T)")
    ax.bar(x + bar_w / 2, clean["receipts_T"], width=bar_w, color=C_GROWTH,
           alpha=0.75, label="Federal Receipts ($T)")
 
    ax.set_xticks(x)
    ax.set_xticklabels(clean["year"].astype(int), rotation=45, ha="right", fontsize=7)
    ax.axhline(0, color="grey", lw=0.8, linestyle=":")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.1f}T"))
    ax.set_ylabel("$ Trillions")
    ax.set_title(
        "Annual Debt Added (Deficit Proxy) vs. Federal Receipts (FY 1978–2025)",
        fontsize=13, fontweight="bold",
    )
    ax.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/fig9_deficit_proxy.png", dpi=150)
    plt.close()
    print("Saved: fig9_deficit_proxy.png")
 
 
def fig_receipts_coverage(df: pd.DataFrame) -> None:
    """
    Fig 10 – Receipts coverage ratio: receipts / annual debt increase.
    A ratio > 1 means receipts exceeded new borrowing that year.
    A ratio < 1 means the government borrowed more than it collected.
    """
    clean = df.dropna(subset=["receipts_coverage"]).copy()
    # Cap extreme values (e.g. near-zero debt-delta years distort the ratio)
    clean = clean[clean["receipts_coverage"].between(0, 5)]
 
    fig, ax = plt.subplots(figsize=(12, 4))
    colors = [C_GROWTH if v >= 1 else C_RATE for v in clean["receipts_coverage"]]
    ax.bar(clean["year"], clean["receipts_coverage"], color=colors, alpha=0.8)
    ax.axhline(1, color="black", lw=1.5, linestyle="--", label="Break-even (ratio = 1)")
 
    ax.set_title(
        "Receipts Coverage Ratio: Federal Receipts ÷ Annual Debt Increase\n"
        "Green = receipts exceeded new borrowing | Red = borrowing exceeded receipts",
        fontsize=12, fontweight="bold",
    )
    ax.set_xlabel("Fiscal Year")
    ax.set_ylabel("Coverage Ratio")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}×"))
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/fig10_receipts_coverage.png", dpi=150)
    plt.close()
    print("Saved: fig10_receipts_coverage.png")
 
 
def fig_receipts_rate_scatter(df: pd.DataFrame) -> None:
    """
    Fig 11 – Scatter: Fed Funds Rate vs. receipts growth %, coloured by era.
    Addresses supporting question 3: how do interest rates interact with revenue?
    """
    clean = df.dropna(subset=["fed_rate", "receipts_growth_pct", "era"]).copy()
    era_colors = {
        "Reagan/Bush":  "#e41a1c",
        "Clinton/Bush": "#377eb8",
        "GFC Buildup":  "#4daf4a",
        "Post-GFC":     "#984ea3",
        "COVID/Recent": "#ff7f00",
    }
 
    fig, ax = plt.subplots(figsize=(8, 6))
    for era, grp in clean.groupby("era", observed=True):
        ax.scatter(grp["fed_rate"], grp["receipts_growth_pct"],
                   label=str(era), color=era_colors.get(str(era), "grey"),
                   s=70, edgecolors="white", linewidths=0.5, zorder=3)
        for _, row in grp.iterrows():
            ax.annotate(str(int(row["year"])),
                        (row["fed_rate"], row["receipts_growth_pct"]),
                        fontsize=6, alpha=0.6)
 
    mask = clean["fed_rate"].notna() & clean["receipts_growth_pct"].notna()
    slope, intercept, r, p, _ = stats.linregress(
        clean.loc[mask, "fed_rate"], clean.loc[mask, "receipts_growth_pct"]
    )
    x_line = np.linspace(clean["fed_rate"].min(), clean["fed_rate"].max(), 200)
    ax.plot(x_line, slope * x_line + intercept, "k--", lw=1.5,
            label=f"OLS (R²={r**2:.2f}, p={p:.3f})")
 
    ax.axhline(0, color="grey", lw=0.8, linestyle=":")
    ax.set_xlabel("Fed Funds Rate (%)")
    ax.set_ylabel("YoY Receipts Growth (%)")
    ax.set_title("Fed Funds Rate vs. Annual Federal Receipts Growth",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=8)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/fig11_receipts_rate_scatter.png", dpi=150)
    plt.close()
    print("Saved: fig11_receipts_rate_scatter.png")
 
 
def fig_receipts_growth_vs_debt_growth(df: pd.DataFrame) -> None:
    """
    Fig 12 – Line comparison: receipts growth % vs. debt growth % over time.
    When debt growth persistently exceeds receipts growth, debt compounds faster
    than the government's revenue base — a key sustainability signal.
    """
    clean = df.dropna(subset=["receipts_growth_pct", "debt_growth_pct"])
 
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(clean["year"], clean["debt_growth_pct"], color=C_DEBT, lw=2,
            label="Debt Growth %")
    ax.plot(clean["year"], clean["receipts_growth_pct"], color=C_GROWTH, lw=2,
            linestyle="--", label="Receipts Growth %")
    ax.fill_between(
        clean["year"],
        clean["debt_growth_pct"],
        clean["receipts_growth_pct"],
        where=(clean["debt_growth_pct"] > clean["receipts_growth_pct"]),
        interpolate=True, alpha=0.12, color=C_DEBT,
        label="Debt growing faster than receipts",
    )
    ax.fill_between(
        clean["year"],
        clean["debt_growth_pct"],
        clean["receipts_growth_pct"],
        where=(clean["debt_growth_pct"] <= clean["receipts_growth_pct"]),
        interpolate=True, alpha=0.12, color=C_GROWTH,
        label="Receipts growing faster than debt",
    )
    ax.axhline(0, color="grey", lw=0.8, linestyle=":")
    ax.set_title("Annual Growth Rate: Federal Debt vs. Federal Receipts (FY 1978–2025)",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Fiscal Year")
    ax.set_ylabel("Year-over-Year Growth (%)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/fig12_receipts_vs_debt_growth.png", dpi=150)
    plt.close()
    print("Saved: fig12_receipts_vs_debt_growth.png")
 
 
# ── 11. Receipts Regression Analysis ─────────────────────────────────────────
def regression_analysis_receipts(df: pd.DataFrame) -> None:
    """
    OLS regressions addressing supporting questions 2 & 4.
 
    SQ2: How does tax revenue affect budget deficits and debt growth?
    SQ4: To what extent do spending, revenue, and interest rates TOGETHER
         explain long-term debt trends?
    """
    print("=" * 65)
    print("REGRESSION ANALYSIS — FEDERAL RECEIPTS")
    print("=" * 65)
 
    print("\n[SQ2] Receipts ($T) → Annual Debt Added ($T)")
    simple_ols(df["receipts_T"], df["debt_yoy_change"] / 1e12,
               "Receipts ($T)", "Debt Added ($T)")
 
    print("\n[SQ2] Receipts Growth % → Debt Growth %")
    simple_ols(df["receipts_growth_pct"], df["debt_growth_pct"],
               "Receipts Growth %", "Debt Growth %")
 
    print("\n[SQ2] Receipts ($T) → Deficit Proxy ($T)")
    simple_ols(df["receipts_T"], df["deficit_T"],
               "Receipts ($T)", "Deficit ($T)")
 
    print("\n[SQ4] Debt-to-Receipts Ratio → Debt Growth %")
    simple_ols(df["debt_to_receipts"], df["debt_growth_pct"],
               "Debt-to-Receipts (×)", "Debt Growth %")
 
    # Multi-variable OLS: receipts + fed_rate → debt_growth_pct
    print("\n[SQ4] Multiple OLS: Receipts ($T) + Fed Rate (%) → Debt Growth %")
    mask = (
        df["receipts_T"].notna()
        & df["fed_rate"].notna()
        & df["debt_growth_pct"].notna()
    )
    X = df.loc[mask, ["receipts_T", "fed_rate"]].values
    y = df.loc[mask, "debt_growth_pct"].values
    # Add intercept column
    X_int = np.column_stack([np.ones(len(X)), X])
    coeffs, residuals, rank, sv = np.linalg.lstsq(X_int, y, rcond=None)
    y_hat  = X_int @ coeffs
    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2     = 1 - ss_res / ss_tot
    print(f"       intercept    = {coeffs[0]:.4f}")
    print(f"       β_receipts   = {coeffs[1]:.4f}")
    print(f"       β_fed_rate   = {coeffs[2]:.4f}")
    print(f"       R²           = {r2:.4f}  (n={mask.sum()})")
    print("       Interpretation: R² shows how much of debt growth variance is")
    print("       jointly explained by receipts level and the fed funds rate.")
    print()
 
 
# ── 12. Era Summary (extended) ────────────────────────────────────────────────
def era_summary_receipts(df: pd.DataFrame) -> None:
    """Per-era summary including receipts and deficit proxy columns."""
    print("=" * 65)
    print("ERA SUMMARY — WITH FEDERAL RECEIPTS")
    print("=" * 65)
    agg_cols = {
        "years":               ("year", "count"),
        "avg_debt_growth":     ("debt_growth_pct", "mean"),
        "avg_receipts_T":      ("receipts_T", "mean"),
        "avg_deficit_T":       ("deficit_T", "mean"),
        "avg_dtr":             ("debt_to_receipts", "mean"),
        "avg_fed_rate":        ("fed_rate", "mean"),
        "total_debt_added_T":  ("debt_yoy_change", lambda x: x.sum() / 1e12),
    }
    available = {k: v for k, v in agg_cols.items() if v[0] in df.columns}
    summary = (
        df.dropna(subset=["era"])
        .groupby("era", observed=True)
        .agg(**available)
        .round(2)
    )
    summary.columns = [
        "Years", "Avg Debt Growth %", "Avg Receipts $T",
        "Avg Deficit $T", "Avg Debt/Receipts ×",
        "Avg Fed Rate %", "Total Debt Added $T",
    ][:len(summary.columns)]
    print(summary.to_string())
    print()
 
 
# ── 13. Key Findings (extended) ───────────────────────────────────────────────
def print_findings_receipts(df: pd.DataFrame) -> None:
    """Narrative findings for the receipts analysis (SQ2 & SQ4)."""
    print("=" * 65)
    print("KEY FINDINGS — FEDERAL RECEIPTS vs. DEBT")
    print("=" * 65)
 
    latest = df.dropna(subset=["receipts_T"]).iloc[-1]
    worst_coverage = df.dropna(subset=["receipts_coverage"])
    worst_coverage = worst_coverage[worst_coverage["receipts_coverage"].between(0, 5)]
 
    print(f"  Latest receipts (FY {int(latest['year'])}) : ${latest['receipts_T']:.2f}T")
    print(f"  Latest debt outstanding           : ${latest['debt_T']:.2f}T")
    print(f"  Debt-to-receipts ratio            : {latest['debt_to_receipts']:.1f}×")
 
    if not worst_coverage.empty:
        min_row = worst_coverage.loc[worst_coverage["receipts_coverage"].idxmin()]
        print(f"  Worst coverage year               : FY {int(min_row['year'])} "
              f"({min_row['receipts_coverage']:.2f}× — "
              f"borrowed ${(min_row['debt_yoy_change']/1e12):.1f}T, "
              f"collected ${min_row['receipts_T']:.1f}T)")
 
    # Years where debt grew faster than receipts
    both = df.dropna(subset=["receipts_growth_pct", "debt_growth_pct"])
    debt_faster = (both["debt_growth_pct"] > both["receipts_growth_pct"]).sum()
    print(f"  Years debt grew faster than receipts: {debt_faster} of {len(both)}")
 
    # Correlation
    mask = df["receipts_T"].notna() & df["debt_growth_pct"].notna()
    r, p = stats.pearsonr(df.loc[mask, "receipts_T"], df.loc[mask, "debt_growth_pct"])
    sig  = "statistically significant" if p < 0.05 else "not statistically significant"
    print(f"\n  Pearson r (receipts level vs. debt growth %) = {r:.3f} "
          f"({'negative' if r < 0 else 'positive'}, {sig}, p={p:.3f})")
    print("  Interpretation: Higher absolute receipts correlate with lower")
    print("  debt *growth rates* — but the absolute debt level has still")
    print("  outpaced receipts every decade since 1980.")
 
    mask2 = df["receipts_growth_pct"].notna() & df["debt_growth_pct"].notna()
    r2, p2 = stats.pearsonr(df.loc[mask2, "receipts_growth_pct"],
                             df.loc[mask2, "debt_growth_pct"])
    sig2 = "statistically significant" if p2 < 0.05 else "not statistically significant"
    print(f"\n  Pearson r (receipts growth % vs. debt growth %) = {r2:.3f} "
          f"({'negative' if r2 < 0 else 'positive'}, {sig2}, p={p2:.3f})")
    print("  Interpretation: When receipts grow faster (e.g. 1990s expansion),")
    print("  debt growth tends to slow — supporting the SQ2 hypothesis that")
    print("  revenue growth helps contain deficit accumulation.")
    print()