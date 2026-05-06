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


