




# Timeline (Updated Progress Report):
## 1. Project Setup and Planning (Phase 1 — March 12–March 20):
The project plan was finalized during this phase. Team roles were assigned: Jonathan leads dataset identification and acquisition, while Louis leads exploratory analysis and research question development. The initial Markdown documentation structure was prepared, including the project overview, research questions, dataset descriptions, timeline, constraints, and known gaps. The primary research question and four supporting questions were defined and documented. Ethical considerations around data licensing and terms of use were identified, particularly given that the datasets originate from U.S. government sources (U.S. Treasury and the Federal Reserve via FRED), which are generally in the public domain.

## 2. Data Acquisition and Storage (Phase 2 — March 21–April 5):
Both primary datasets have been successfully acquired and are present in the repository:

historical.csv — sourced from the U.S. Treasury's Fiscal Data portal (Historical Debt Outstanding), providing an annual summary of total U.S. federal debt outstanding from 1789 to the present.
funds.csv — sourced from the Federal Reserve Economic Data (FRED) platform (Federal Funds Effective Rate), capturing the overnight interbank lending rate as a proxy for broader interest rate conditions.

These two datasets have been merged into a single CSV  (merged_annual.csv) file using a shared time attribute (year), forming the integrated base dataset for analysis. A data scraping script was also written and is functional, enabling automated data retrieval from the web rather than relying solely on manual downloads. This supports reproducibility by enabling future team members or reviewers to re-fetch the data programmatically.
A preliminary data quality assessment was begun during this phase. One key structural issue identified early was that the fiscal year definition in the Historical Debt Outstanding dataset changed across different historical periods — January-start (1789–1842), July-start (1842–1977), and October-start (1977–present) — which will need to be handled during cleaning to ensure consistent time alignment across datasets.

## 3. Data Cleaning, Transformation, and Enrichment (Phase 3 — April 5 –April 20) 
This phase is currently underway. Now that the two datasets have been merged, the team is beginning to address schema differences, inconsistent time granularities (monthly for FRED vs. annual for Treasury), and any missing or null values in the combined dataset. The fiscal year boundary shifts noted above will require careful handling to avoid misaligning records from different eras.
Preliminary exploratory analysis using Python (Pandas, Matplotlib) is being planned. No final visualizations have been produced yet, but the cleaned and integrated dataset will serve as the foundation for trend analysis in Phase 4.
## 4. Analysis, Visualization, and Workflow Reproducibility (Phase 4 — April 20 – May 1 ) Started
This phase has not begun. Planned deliverables include correlation analysis between fiscal variables and debt growth, time-series visualizations, and finalization of an automated end-to-end reproducible workflow with a clear Git commit history.
## 5. Final Report and Documentation (Phase 5 — April 26–May 3)
 Final report writing, metadata compilation, and repository cleanup are scheduled for the final week before submission on May 3.

## Changes to Plan:
The core scope and research questions remain unchanged from the original plan. However, a few adjustments have been made based on early experience:

Data scraper scope narrowed: The original plan described using Python scripts or notebooks for workflow automation broadly. In practice, the data scraper was scoped specifically to automate fetching from FRED and the Treasury portal. A tool to remove redundant data columns was initially included in the scraper but was removed after causing issues (described below).
Integration earlier than planned: Merging funds.csv and historical.csv into a single dataset happened earlier in Phase 2 than originally scoped, which is a positive development and provides more time for cleaning in Phase 3.

## Challenges:
### 1. GitHub SSH Connection Issues:
Early in the project, team members encountered difficulties establishing SSH connections to the GitHub repository, which initially prevented pushing commits and collaborating through version control. This was resolved by regenerating SSH keys on both machines, adding the public keys to the respective GitHub accounts, and verifying the connection using ssh -T git@github.com. Collaboration via Git has been smooth since this fix was applied.

### 2.  FRED API Key Setup
Accessing the Federal Reserve Economic Data (FRED) API required registering for an API key through the St. Louis Fed's developer portal. There was a delay in obtaining and configuring the key, which briefly stalled automated data retrieval. The issue was resolved once both team members registered for keys and stored them securely in the project environment outside of version control to avoid exposing credentials in the repository. Going forward, the README will include instructions for obtaining and configuring a FRED API key so that others can reproduce the data fetching workflow.
### 3. Data Fetcher Code 
During development of the data scraper, a component designed to automatically remove certain columns from the fetched data, introduced errors that corrupted the output during testing. Rather than spending significant time debugging an optional feature at this stage, the team made the pragmatic decision to remove the problematic component from the scraper entirely. The core fetching and saving functionality works correctly. The removed feature may be revisited in Phase 3 if time permits, but it is not critical to the project's primary deliverables.



## Contribution:

### Jonathan: 
I have been the primary driver of the data acquisition and pipeline infrastructure for this project. He took the lead on identifying suitable datasets from official government sources, including the U.S. Treasury Fiscal Data portal and the FRED database, and evaluated each for relevance, licensing compatibility, and structural suitability for integration. Jonathan was responsible for writing the data scraper script that automates the retrieval of both the Historical Debt Outstanding and Federal Funds Effective Rate datasets, reducing reliance on manual downloads and improving reproducibility. He also handled the technical setup of the GitHub repository, including resolving the SSH connection issues encountered early in the project, and has maintained a consistent commit history reflecting ongoing data work.


### Louis: 
I focused primarily on the analytical and research design dimensions of the project. I led the development of the project's research questions, refining the primary question and crafting the four supporting questions that frame the scope of the analysis. I have been responsible for exploring the datasets to understand their structure, variable definitions, and potential analytical value, and have guided decisions about which fiscal variables are most relevant to the project's goals. I contributed to the project plan documentation, including the constraints and gaps sections, which reflect a careful and nuanced understanding of the data's limitations. As the project moves into Phase 3, I will take the lead on exploratory data analysis, identifying early patterns and informing the design of the visualizations that will be developed in Phase 4.


