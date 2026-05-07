# IS477
repo for group "double blind testing" in course UIUC 2026 spring IS477
# Contributiors:
- Louis Wen
- Jonothan Yang

# Summary 
The discussion around the  United States federal debt has never stopped, and now it has grown from roughly $0.70 trillion in fiscal year 1977 to over $36 trillion by fiscal year 2025, a nominal increase exceeding 5,000% over five decades. As there are only a handful of first-world countries that have declared bankruptcy, and there is a clear lack of understanding of the consequences if a country for the global reserve currency goes bankrupt, this forces us to understand the federal debt sustainability issue and its profound implications for monetary policy, public investment capacity, and long-term interest rates. This project aims to investigate how changes in U.S. government spending, tax revenue, and interest rates influence the growth of outstanding federal debt over time, using three primary data sources merged into a unified annual panel dataset spanning FY 1977 through FY 2025, while pointing out key political or global events like changes in the presidential office or global crises like the pandemic.

Our primary research question is: 
**How do changes in U.S. government spending, tax revenue, and interest rates influence the growth of outstanding federal debt over time?**

This question is explored through four supporting questions:
1. What relationship exists between federal spending and increases in outstanding national debt?
2. How does tax revenue affect budget deficits and debt growth?
3. How do interest rate changes impact government interest payments and debt sustainability?
4. To what extent do spending, revenue, and interest rates together explain long-term trends in U.S. federal debt?

To answer these questions, we acquired three datasets: historical federal debt outstanding, the Federal Reserve's annual average federal funds rate, and annual federal receipts. The first two were cleaned to aggregate to fiscal-year frequency and merged into a stored dataset (merged_annual.csv) containing 49 annual observations. The federal receipts dataset is loaded separately and joined in memory at runtime by merge_receipts() in analysis.py, keeping it independent from the core merged file. We then computed derived variables such as: year-over-year debt growth, estimated interest expense, and debt-to-receipts ratio. These variables are later used to perform descriptive OLS regressions and multiple visualizations to identify patterns and test relationships.

A central finding is that the federal funds rate alone does not significantly predict year-over-year debt growth (OLS R²=0.05, p=0.121 — not statistically significant), challenging the intuition that higher interest rates mechanically drive debt accumulation. Instead, episodic crisis-driven fiscal expansions, such as the Global Financial Crisis stimulus of 2009–2010, account for the largest single-year debt spikes. Meanwhile, the receipts analysis reveals a structural long-run imbalance: in FY 2025, the debt-to-receipts ratio stood at approximately 7.2×, meaning over seven full years of total federal revenue would be required to retire the outstanding debt. Debt grew faster than receipts in the majority of years in our sample, and estimated annual interest expense surged above $1.5 trillion by FY 2024–2025 following the Fed's 2022–2023 rate-hiking cycle. This points to a compounding dynamic that will increasingly constrain future fiscal flexibility.

# Data Profile
Dataset 1: U.S. Federal Debt Outstanding (historical_debt.csv)
Source: U.S. Department of the Treasury, Fiscal Data API (fiscaldata.treasury.gov). The endpoint used is the Debt to the Penny dataset, which records the total public debt outstanding for each business day.
Structure: The raw dataset contains daily observations with columns including record_date (date of the record), debt_outstanding_amt (total federal debt outstanding in dollars), fiscal year, and fiscal_calendar_note (the start and end months). For this project, we aggregated daily observations to a single annual figure per fiscal year (October 1 – September 30), retaining the end-of-fiscal-year value. The resulting annual series spans FY 1977–FY 2025 (49 observations).
Content: Debt outstanding includes both debt held by the public (e.g., Treasury bonds owned by individuals, institutions, and foreign governments) and intragovernmental holdings (e.g., Social Security trust funds). The combined figure is the legally authorized national debt ceiling.
Relevance: This is the primary dependent variable in our analysis. Year-over-year changes in this series capture net federal borrowing, which reflects the consolidated impact of spending, revenues, and refinancing.
Ethical/Legal Constraints: This dataset is produced by the U.S. federal government and is in the public domain. No personally identifiable information is present. There are no redistribution restrictions.
File location in repository: data_files/historical_debt.csv

Dataset 2: Federal Funds Rate (fedfunds.csv)
Source: Federal Reserve Economic Data (FRED), Federal Reserve Bank of St. Louis. The specific series is the Effective Federal Funds Rate (FEDFUNDS), reported as a monthly average and converted to an annual average for this project.
Structure: The raw dataset contains monthly observations with columns for date and effective federal funds rate (percentage). We computed a simple annual average across calendar months corresponding to each fiscal year to obtain a single rate per year. The annual series spans 1977–2025.
Content: The federal funds rate is the overnight lending rate between depository institutions, set as a target range by the Federal Open Market Committee (FOMC). It is the benchmark short-term interest rate and serves as a proxy for the broader cost of government borrowing, though the Treasury issues debt at a range of maturities.
Relevance: The fed funds rate is our primary independent variable for Supporting Questions 3 and 4. It allows us to estimate the interest burden on outstanding debt and to test whether the rate environment is associated with changes in debt growth.
Ethical/Legal Constraints: FRED data is publicly available and licensed for research and educational use. No PII is present.
File location in repository: data_files/fedfunds.csv

Dataset 3: Federal Receipts (federal_receipt.csv)
Source: Federal Reserve Economic Data (FRED), Federal Reserve Bank of St. Louis. The specific series is Federal Receipts (FYFR), which reports total annual federal government receipts — taxes, fees, and other revenue — as recorded by the U.S. Office of Management and Budget.
Structure: The dataset contains annual observations with columns date (September 30 of each fiscal year) and federal_receipts_billions_usd. Despite the column name, FRED reports this series in millions of U.S. dollars; for example, FY 1977 shows 355,559, representing $355.6 billion, not $355.6 trillion. In our analysis, we correct for this mislabeling by dividing by 1,000,000 to convert to trillions, producing a receipts_T column ranging from approximately $0.36T (FY 1977) to approximately $5.2T (FY 2025). The dataset covers 50 annual observations from FY 1977 through FY 2025 (approximately).
Content: Federal receipts include individual income taxes, corporate income taxes, Social Security and Medicare payroll taxes, excise taxes, estate and gift taxes, customs duties, and miscellaneous receipts. This is the broadest measure of federal revenue and represents the government's primary capacity to finance its obligations without borrowing.
Relevance to Research Questions: This dataset directly addresses Supporting Questions 2 and 4. By comparing annual receipts to annual debt additions, we construct a deficit proxy and assess how revenue growth or shortfall contributes to debt accumulation. The debt-to-receipts ratio provides a measure of long-run fiscal sustainability. Figure 12 (receipts growth vs. debt growth) is directly motivated by Supporting Question 2.
Ethical/Legal Constraints: FRED data is publicly available under a standard research-use license. No personally identifiable information is present, and no redistribution restrictions apply.
File location in repository: data_files/federal_receipt.csv

Merged Dataset (merged_annual.csv)
The two datasets were left joined on fiscal year after transforming both to annual frequency. The merged file contains one row per fiscal year and includes the following columns:
	
	record_date: The exact date the data was recorded
	debt_outstanding_amt: Total federal debt outstanding (dollars)
	fiscal_year: Fiscal year (integer, 1977–2025)
	fiscal_calendar_note: Starting and ending months of the fiscal year (Oct-Sep)
	fedfunds_annual_avg: Annual average federal funds rate (%)

File location in repository: data_files/merged_annual.csv

# Data Quality
## Completeness
All three source datasets are maintained by U.S. federal agencies or the Federal Reserve and have complete annual coverage for the FY 1977–FY 2025 study period. The debt dataset has continuous daily observations with no gaps. The fedfunds dataset has complete monthly coverage aggregated to annual averages without any missing months to accommodate the federal debt data, and the federal receipts dataset has annual observations for every fiscal year in the study window to keep the original context. 

Merged_annual.csv is produced from historical_debt.csv and fedfunds.csv. It has 49 rows with no missing values in either of its two primary source columns (debt_outstanding_amt and fedfunds_annual_avg). The federal receipts dataset (federal_receipt.csv) is joined to this base in memory at runtime via merge_receipts() because it covers the same FY 1977–FY 2025 window without gaps, and the in-memory left join also produces no missing values in receipts_T.

There are some derived columns that rely on lagged or differenced values, specifically debt_yoy_change, debt_growth_pct, est_interest_expense_T, and receipts_growth_pct. Some exist due to data cleaning, removal of prior data, while others are missing due to no prior-year value to differ against. These are handled consistently throughout by dropping NA rows using .dropna() before computing statistics or rendering visualizations (FY 1978–FY 2025).

## Accuracy
The debt outstanding figures are official U.S. Treasury records drawn from the Debt to the Penny series and should be treated as the authoritative source. The federal funds rate is the observed, effective market rate published by the Federal Reserve. The federal receipts figures are drawn from OMB data re-published through FRED and represent official government accounting.

One important accuracy limitation is our approximation of interest expense: debt(t-1) × fedfunds_rate(t) / 100. The U.S. Treasury borrows across a range of maturities, and the coupon rates on outstanding debt reflect rates prevailing at issuance, not the current overnight rate(SOFR). During the post-2008 near-zero-rate era, the Treasury locked in low long-term rates on newly issued debt, so actual interest costs fell less dramatically than our formula suggests. During 2022–2024, the existing long-term debt stock buffered against rising rates. As a result, our interest expense estimate can differ substantially from the Treasury's actual reported interest outlays in any given year. This column is labeled "estimated" throughout and should be interpreted as an approximation only.

A second accuracy concern is the federal receipts column mislabeling with a column named federal_receipts_billions_usd when it actually contains values in millions of dollars. This was identified by cross-referencing values against known OMB budget tables (e.g., FY 1977 reported as 355,559, consistent with $355.6 billion in published budgets). The load_receipts() function corrects for this by dividing by 1,000,000.

## Consistency
All dollar figures are in nominal terms since we did not make any adjustments to account for inflation, although it significantly impacts long-run real comparisons due to efficiency, and the loss in value of debt due to inflation will be added back by the interest paid for the debt. The two datasets that form merged_annual.csv use a consistent fiscal-year alignment (October 1 – September 30 for FY 1977 onward), and the merge was performed on this common key. The federal receipts dataset uses the same September 30 date convention, ensuring the runtime join is also temporally consistent across all variables.

## Timeliness
All datasets were retrieved in 2026, although they only recorded up to 2025. No stale or outdated data sources were used.

# Data Cleaning
**Step 1:** Temporal Aggregation of Debt Data
The raw Treasury debt dataset is at a daily frequency. We filtered to FY 1977 onward and aggregated to one annual observation per fiscal year by retaining the end-of-fiscal-year balance, the last available debt observation on or near September 30. This is standard practice for balance-sheet stock variables, as it captures the debt outstanding at fiscal year close and is directly comparable to published OMB deficit figures.

Quality issue addressed: The daily granularity is unnecessary for annual trend analysis and would create temporal misalignment if merged directly with the annual federal funds and receipts data. Selecting the end-of-year balance also avoids distortions from intra-year debt ceiling fluctuations and short-term Treasury cash management operations.

**Step 2:** Temporal Aggregation of Federal Funds Rate
The stored fedfunds.csv contains the pre-computed annual average federal funds rate per fiscal year, calculated as a simple arithmetic mean of monthly effective rates across the 12 months of each fiscal year. Using a full 12-month average rather than a single month's value better represents the average borrowing cost environment throughout the fiscal year.

Quality issue addressed: Monthly fed funds rates exhibit short-term volatility around FOMC meeting dates and policy transition months. The annual average smooths this noise and is appropriate for annual-level analysis of debt dynamics.

**Step 3:** Unit Correction for Federal Receipts
The raw federal_receipt.csv column federal_receipts_billions_usd actually contains values in millions of dollars despite its name. This was identified by cross-referencing FY 1977's value of 355,559 against published OMB Historical Tables, which confirm federal receipts of approximately $355.6 billion for that year. The load_receipts() function corrects for this by dividing by 1,000,000 to produce the receipts_T column in trillions. Without this correction, receipts would appear 1,000 times too large.

Quality issue addressed: Mislabeled units in the source column would silently corrupt all downstream calculations involving receipts. The explicit division factor and inline documentation in load_receipts() ensure that this correction is transparent and reproducible.

**Step 4:** Fiscal Year Derivation for Receipts
The federal receipts dataset uses a date column formatted as September 30 of each fiscal year. The load_receipts() function extracts the fiscal year integer using df["date"].dt.year. Because FRED aligns the receipts observation to September 30, the extracted year correctly maps to the fiscal year label used in the other two datasets.

Quality issue addressed: Ensures that the receipts data is aligned to the correct fiscal year when joining with the debt and federal funds data. An incorrect year mapping would distort all derived metrics.

**Step 5:** Merging on Fiscal Year
The three annual datasets were joined using a left join on the year/fiscal_year key, with the main debt-and-rate DataFrame as the left table and the receipts DataFrame joined onto it. Because all three datasets provide complete coverage for FY 1977–FY 2025, no records were lost. The result is a clean 49-row dataset with no empty rows.

Quality issue addressed: Ensures each row in the analytical dataset contains a debt value, a fed funds rate, and a federal receipts value, all corresponding to the same fiscal year, with no temporal mismatches

**Step 6:** Derivation of Analytical Columns 
Several derived columns are computed programmatically in analysis.py after loading and merging:
- debt_T: Debt in trillions (÷1e12) for chart readability.
- debt_yoy_change and debt_growth_pct: Annual change via .diff() and .pct_change(); NaN for FY 1977.
- est_interest_expense_T: Prior year's debt × current fed funds rate ÷ 100 ÷ 1e12 (one-period lag avoids look-ahead bias).
- rolling5_growth: 5-year rolling mean of debt growth %, minimum 3 periods.
- era: Categorical binning into five historical periods using pd.cut().
- fed_rate_lag1: One-year lag of fed funds rate for lagged regressions.
- receipts_T, deficit_T, receipts_coverage, debt_to_receipts, receipts_growth_pct: Computed in merge_receipts() to support the SQ2 and SQ4 analyses.

Quality issue addressed: Centralizing all derivations in the load/merge functions ensures every downstream analysis uses identical transformations, eliminating the risk of inconsistent variable definitions across functions.

# Findings 
**Overview:**  
Federal debt grew from approximately $0.70 trillion in FY 1977 to $36.2 trillion in FY 2025, a nominal increase of over 5,000%. The overall mean year-over-year growth rate was 8.8% (as confirmed by the dashed overall mean line in Figure 6). Debt growth was highly uneven across eras: the Reagan/Bush era showed the highest and most volatile growth (box plot median ~10.6%, IQR roughly 8%–15%), while the Clinton/Bush era had the lowest median (~5.5%) and the widest dispersion. Post-GFC and COVID/Recent eras show tighter distributions concentrated near 7–8%, but with outliers driven by crisis-year stimulus.

**Finding 1: Debt Growth is Episodic and Crisis-Driven (Figures 1, 2, 6)**  
Figure 2 shows that year-over-year debt growth peaked at approximately 20.6% in FY 1983 (Reagan-era deficit spending) spiked again to ~19.0% in FY 2009 (GFC TARP/ARRA stimulus), and hit ~18.7% in FY 2020 (COVID-19 CARES Act and supplemental relief). The 5-year rolling average confirms a structural deceleration from a ~15% peak in the mid-1980s down to a trough of ~2.5% around FY 2000 (Clinton-era budget surpluses), followed by a sustained rise through the 2000s and an elevated plateau post-2008. Figure 1 visually confirms that as the fed funds rate peaked above 16% in 1981 and then declined monotonically through the 2010s, debt grew continuously at a positive rate throughout, confirming that fiscal policy decisions rather than the interest rate level are the primary driver of annual debt additions.

**Finding 2: The Fed Funds Rate Does Not Significantly Predict Debt Growth (Figure 4)**  
The scatter plot (Figure 4) shows a diffuse, era-segmented cloud with no clean linear relationship between the fed funds rate and annual debt growth. The OLS regression line yields R²=0.05, p=0.121 — not statistically significant at any conventional threshold. The Reagan/Bush era cluster (red dots) occupies the high-rate, high-growth upper-right quadrant, while the Post-GFC cluster (purple) sits at near-zero rates but still shows moderate growth (~6–14%), and the COVID/Recent cluster (orange) shows the highest single-year growth point (FY 2020 at ~18.7%, fed rate ≈0.1%). The pattern illustrates that debt growth is driven primarily by fiscal shocks, wars, recessions, pandemics, and policy choices. 

**Finding 3: Estimated Interest Expense Surged After 2022 Despite Moderate Debt Growth (Figure 3)**  
Figure 3 shows a striking divergence since 2022. Estimated annual interest expense remained below $0.4T per year from the late 1990s through 2021, suppressed by the near-zero rate environment of 2009–2015 and 2020–2021, even as the debt stock tripled. Following the Fed's 2022–2023 rate-hiking cycle, estimated interest expense surged to $1.5–1.7T per year by FY 2024–2025, the highest in the study period. Simultaneously, the YoY debt change (blue line, right axis) declined from its COVID peak of ~$4.2T in FY 2020 to approximately $2.0–2.5T by FY 2024–2025. The convergence of these two trends implies that interest payments are now constituting a growing share of new borrowing requirements, a compounding dynamic that constrains future fiscal flexibility even if primary deficits remain stable.

**Finding 4: Federal Receipts Have Grown But Cannot Keep Pace With Debt (Figures 7–10, 12)**  
Figure 7 illustrates the widening structural gap between total debt outstanding (left axis) and federal receipts (right axis). While receipts grew from roughly $0.36T in FY 1977 to approximately $5.2T in FY 2025, debt grew from $0.70T to $36.2T over the same period, at a far faster rate. The two series effectively tracked one another through the early 1980s but have since diverged sharply, with debt pulling away particularly after the GFC. Figure 8 (debt-to-receipt ratio) puts this into perspective. The ratio rose from approximately 2.0× in FY 1977 to a peak of approximately 7.9× in FY 2020 before settling at 7.2× in FY 2025. Figure 9 (the deficit proxy bar chart) shows that receipts (green bars) consistently exceed annual debt additions (red bars) in almost every year, meaning it is not a total revenue collapse that drives debt accumulation, but rather that spending exceeds receipts, producing a primary deficit. Figure 12 (receipts growth vs. debt growth over time) shows that receipts growth is far more volatile than debt growth, swinging between approximately −17% (FY 2009) and +21% (FY 2022). Periods when receipts grew faster than debt, the late 1990s, 2005–2007, and 2021–2022, correspond to economic expansions boosting income and capital gains taxes. Periods when debt grew faster dominate the Reagan years, the 2001–2003 recession, the GFC window, and scattered post-2010 years. Debt grew faster than receipts in a majority of the 48 years with available data, confirming a structural rather than merely cyclical imbalance. 

**Finding 5: Higher Rates Are Associated With Modestly Stronger Receipts Growth (Figure 11)**  
Figure 11 (scatter: fed rate vs. receipts growth %) reveals a positive OLS relationship with R²=0.09, p=0.036 — marginally statistically significant. Higher-rate environments have historically coincided with slightly stronger receipts growth. This is a weak effect that explains only 9% of the variance in receipts growth, but the direction of the relationship is economically sensible and directionally consistent across most eras, as shown in the scatter.

# Future Work
## Lessons learned
Working with long-run U.S. fiscal data over a nearly 50-year annual panel reinforced several methodological lessons that we would apply differently in future iterations of this project.

First, the importance of distinguishing between stock and flow variables. Debt outstanding is a stock, accumulating over all prior years; the annual deficit, receipts, and interest expense are flows occurring within a single year. Correlating a rapidly growing stock with a flow can produce statistically misleading results even when both series are correctly measured. In future work, we would more carefully structure all regressions as flow-on-flow analyses rather than mixing levels and growth rates in an ad hoc way.

Second, the unit mislabeling in the federal receipts CSV (federal_receipts_billions_usd actually in millions) was caught only through active cross-referencing against known published budget figures. This experience underscores the importance of a rigorous data profiling step, including sanity checks against independent external benchmarks, as a mandatory first step before any analysis, even for authoritative government data sources distributed through reputable APIs.
Third, nominal versus real figures matter substantially for a 50-year horizon analysis. All of our dollar figures are in nominal terms, meaning that apparent growth in debt, receipts, and interest expense partially reflects general price-level increases rather than real fiscal deterioration. Inflation-adjusting to constant 2017 or 2024 dollars using the GDP deflator would provide a cleaner picture of real fiscal trends and would allow more direct comparisons of the fiscal burden across eras. We did not apply this correction in the current project, but identified it as the highest-priority enhancement for future work.

## Potential Future Work:
- Incorporate actual outlay data: The Treasury's Monthly Treasury Statement publishes total outlays (spending) annually. Adding this variable would allow direct testing of Supporting Question 1, “federal spending as a driver of debt growth,” without relying on debt changes as an imperfect spending proxy
- Inflation adjustment: Deflating all dollar series by the GDP deflator or CPI would enable real comparisons and prevent attributing nominal growth to genuine fiscal deterioration when part of that growth simply reflects price-level increases. The FRED database provides both deflators, and could be easily added as a fourth dataset
- Debt-to-GDP analysis: Expressing debt relative to nominal GDP is the standard fiscal sustainability metric used by economists. A GDP series is straightforward to add from FRED and would allow us to contextualize whether the growth in debt is outpacing the economy's productive capacity. This would be a more meaningful sustainability benchmark than nominal debt levels or debt-to-receipts ratios alone
- Multivariate and time-series models: A vector autoregression (VAR) including spending, receipts, the fed funds rate, and GDP growth as jointly endogenous variables would provide a more complete picture of dynamic interdependencies and allow impulse response analysis (e.g., how does a 1% increase in the fed funds rate affect debt growth over the following 3 years, controlling for GDP?). Our two-variable multiple OLS (receipts + fed rate → debt growth) is a first step toward this, but a proper VAR would account for lags and reverse causality.
- Scenario forecasting: Given current debt levels (~$36T), the recent rate environment, and the projected primary deficits, a compounding model could project debt-to-GDP and debt-to-receipts ratios under different fiscal consolidation scenarios over the next 10–30 years, providing direct policy-relevant outputs on long-run sustainability

# Challenges
**Challenge 1:** Interest Rate Proxy and the Maturity Mismatch Problem
The federal funds rate is an overnight policy rate, not the rate at which the U.S. Treasury actually borrows. The Treasury issues debt across maturities ranging from 4-week T-bills to 30-year bonds, and the yields on those instruments are determined by market forces, investor expectations of future short-term rates, inflation expectations, and global safe-asset demand, not simply by the FOMC's target. During the post-2008 era, the Treasury deliberately extended the average maturity of its debt portfolio, locking in low long-term rates even as short-term rates eventually rose. During the 2022–2024 rate-hiking cycle, the fed funds rate exceeded 5%, but the average interest rate on the existing debt stock rose far more slowly because most outstanding bonds had been issued at lower long-term rates. Our simplified debt(t-1) × fedfunds_rate(t) / 100 estimate, therefore, systematically diverges from the Treasury's actual reported interest outlays. We addressed this by clearly labeling the estimate as approximate throughout the project and by focusing interpretive discussion on the conceptual relationship rather than the precise dollar figures.

**Challenge 2:** Structural Breaks and Era Heterogeneity
The 48-year study period spans enormous structural changes: the end of Bretton Woods, Volcker disinflation, Reagan-era supply-side tax cuts, the Clinton-era budget surpluses driven partly by the dot-com boom and capital gains tax windfalls, post-9/11 security spending, two financial crises (2000–2001 and 2008–2009), a decade of near-zero rates, and the COVID-19 pandemic. These structural breaks mean that a single OLS slope estimated across the full sample almost certainly masks heterogeneous relationships that differ substantially by era. Our categorical era variable and Figure 6 (the boxplot) partially address this by enabling visual inspection of cross-era heterogeneity.

**Challenge 3:** Spurious Correlation Risk
Federal debt outstanding, federal receipts, and nominal GDP are all strongly upward-trending non-stationary time series. Regressing one non-stationary level series on another, for example, debt level on receipts level, risks spurious correlations: two unrelated series that both trend upward will appear highly correlated even in the absence of any underlying causal mechanism. We partially mitigated this by using growth rates (percentage changes) rather than levels as the primary dependent variable in most regressions, since growth rates are generally closer to stationarity.

**Challenge 4:** Causality vs. Association 
All findings in this project are correlational. The fed funds rate, government spending, tax receipts, and debt simultaneously respond to the same underlying macroeconomic conditions, making it impossible to establish causal effects from OLS regressions alone. A recession simultaneously reduces tax receipts and social programs, prompts the Fed to cut rates, and causes the deficit and debt to rise all at the same time, without any single variable causing the others in the econometric sense. Establishing causal effects would require either a randomized experiment (infeasible in macroeconomics at the national level) or a credible natural experiment.

# Reproducing
To reproduce all analysis figures and printed output from scratch, follow these steps in order:
**Step 1:** Clone the repository and verify the following files are present in the data_files/ folder:
- historical_debt.csv
- fedfunds.csv
- federal_receipt.csv
- merged_annual.csv

**Step 2:** Install Python Dependencies
- Python 3.9 or later is recommended. No database or external API calls are required at runtime

**Step 3:** Re-scrape and rebuild the data files. Run the data scraper and main pipeline scripts to re-acquire the source CSVs and regenerate merged_annual.csv: 

**Step 4:** Run the main analysis.py script. This will:
- Load and clean data_files/merged_annual.csv via load_data()
- Join data_files/federal_receipt.csv in memory via merge_receipts()
- Print descriptive statistics, OLS regression results, era summary tables, and key findings to stdout
- Save twelve figures to analysis_graphs/

**Step 5:** Verify outputs by comparing your generated figures in analysis_graphs/




# Reference
- U.S. Department of the Treasury. Debt to the Penny. Fiscal Data. https://fiscaldata.treasury.gov/datasets/debt-to-the-penny/
- Federal Reserve Bank of St. Louis. Effective Federal Funds Rate (FEDFUNDS). FRED Economic Data. https://fred.stlouisfed.org/series/FEDFUNDS
- Federal Reserve Bank of St. Louis. Federal Receipts (FYFR). FRED Economic Data. https://fred.stlouisfed.org/series/FYFR
- U.S. Office of Management and Budget. Historical Tables: Budget of the U.S. Government. https://www.whitehouse.gov/omb/budget/historical-tables/
- Congressional Budget Office. The Budget and Economic Outlook: 2025 to 2035. https://www.cbo.gov
- Reinhart, C. M., & Rogoff, K. S. (2010). Growth in a Time of Debt. American Economic Review, 100(2), 573–578.
- McKinney, W. (2010). Data Structures for Statistical Computing in Python. Proceedings of the 9th Python in Science Conference, 56–61.
- Hunter, J. D. (2007). Matplotlib: A 2D Graphics Environment. Computing in Science & Engineering, 9(3), 90–95.
- Virtanen, P., et al. (2020). SciPy 1.0: Fundamental Algorithms for Scientific Computing in Python. Nature Methods, 17, 261–272.
- Harris, C. R., et al. (2020). Array programming with NumPy. Nature, 585, 357–362.


