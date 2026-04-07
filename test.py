"""
integrate.py - Data Integration: Retraction Data
Combines PubMed XML and Web of Science JSON retraction records into a unified dataset.
"""

import os
import pandas as pd
from lxml import etree
import recordlinkage
import json

# ── Paths ────────────────────────────────────────────────────────────────────
PUBMED_XML_PATH = "/Users/jonathanyang/Downloads/IS_477/Data/pubmed_retractions_2024.xml"
WOS_JSON_PATH   = "/Users/jonathanyang/Downloads/IS_477/Data/wos_retractions_2024.json"
OUTPUT_PATH     = "/Users/jonathanyang/Downloads/IS_477/out.csv"

# ── 1. Month normalisation ───────────────────────────────────────────────────
MONTH_MAP = {
    "JAN": 1,  "FEB": 2,  "MAR": 3,  "APR": 4,
    "MAY": 5,  "JUN": 6,  "JUL": 7,  "AUG": 8,
    "SEP": 9,  "OCT": 10, "NOV": 11, "DEC": 12,
    # numeric strings
    "01": 1, "02": 2, "03": 3, "04": 4, "05": 5, "06": 6,
    "07": 7, "08": 8, "09": 9, "10": 10, "11": 11, "12": 12,
}

def normalize_month(raw):
    """Return an integer 1-12 (or None) from any raw month token."""
    if raw is None:
        return None
    raw = str(raw).strip()
    # Handle ranges like "FEB-MAR" → use first token
    token = raw.replace("–", "-").split("-")[0].strip()
    # Strip trailing digits like "DEC 31" → "DEC"
    token = token.split()[0].strip().upper()
    return MONTH_MAP.get(token, None)


# ── 2. Parse PubMed XML ──────────────────────────────────────────────────────
def parse_pubmed_xml(path):
    tree = etree.parse(str(path))
    root = tree.getroot()

    records = []
    for article in root.iter("PubmedArticle"):
        # PMID
        pmid_el = article.find(".//PMID")
        pmid = pmid_el.text.strip() if pmid_el is not None else None

        # Article title
        title_el = article.find(".//ArticleTitle")
        article_title = "".join(title_el.itertext()).strip() if title_el is not None else None

        # Journal title
        journal_el = article.find(".//Journal/Title")
        journal_title = journal_el.text.strip() if journal_el is not None else None

        # Publication year
        pub_year_el = article.find(".//PubDate/Year")
        pub_year = pub_year_el.text.strip() if pub_year_el is not None else None

        # Publication month
        pub_month_el = article.find(".//PubDate/Month")
        pub_month_raw = pub_month_el.text.strip() if pub_month_el is not None else None
        pub_month = normalize_month(pub_month_raw)

        records.append({
            "PMID":         pmid,
            "UID":          None,
            "ArticleTitle": article_title,
            "JournalTitle": journal_title,
            "PubYear":      pub_year,
            "PubMonth":     pub_month,
        })

    return pd.DataFrame(records)


# ── 3. Parse WOS JSON ────────────────────────────────────────────────────────
def parse_wos_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # This API returns a flat list of records directly — no nested
    # "Data"/"Records"/"REC" wrapper used by the older WOS XML API.
    if isinstance(data, list):
        raw_records = data
    elif "Data" in data:
        raw_records = data["Data"].get("Records", {}).get("records", {}).get("REC", [])
    elif "records" in data:
        raw_records = data["records"]
    else:
        raw_records = next((v for v in data.values() if isinstance(v, list)), [])

    records = []
    for rec in raw_records:
        # ── UID ──────────────────────────────────────────────────────────────
        # Key is lowercase "uid", not "UID"
        uid = rec.get("uid") or None

        # ── Title ─────────────────────────────────────────────────────────────
        # Title is a plain string at rec["title"], not nested under
        # static_data → summary → titles → title[]
        article_title = rec.get("title") or None

        # ── Journal / source title ────────────────────────────────────────────
        # Source info lives in rec["source"], not in summary pub_info
        source = rec.get("source", {})
        journal_title = source.get("sourceTitle") or None

        # ── Publication date ──────────────────────────────────────────────────
        # publishYear is an int and publishMonth is a string, both in rec["source"]
        pub_year_raw = source.get("publishYear")
        pub_year = str(pub_year_raw) if pub_year_raw is not None else None

        pub_month_raw = source.get("publishMonth") or None
        pub_month = normalize_month(pub_month_raw)

        # ── PMID ──────────────────────────────────────────────────────────────
        # Identifiers is a flat dict {doi, issn, pmid, ...}, not a nested
        # list under static_data → item → identifier → identifier[]
        identifiers = rec.get("identifiers", {})
        pmid_raw = identifiers.get("pmid")
        pmid = str(pmid_raw).strip() if pmid_raw else None

        records.append({
            "PMID":         pmid,
            "UID":          uid,
            "ArticleTitle": article_title,
            "JournalTitle": journal_title,
            "PubYear":      pub_year,
            "PubMonth":     pub_month,
        })

    return pd.DataFrame(records)


# ─── 4. Integration ───────────────────────────────────────────────────────────
def get_first_journal_word(title):
    """Return first word of journal title (lower-case), excluding 'the'."""
    if not isinstance(title, str):
        return ""
    words = [w for w in title.lower().split() if w != "the"]
    return words[0] if words else ""


def integrate(pubmed_df, wos_df):
    # ── Stage 1: Exact join on PMID ──────────────────────────────────────────
    pm_with_pmid  = pubmed_df[pubmed_df["PMID"].notna()].copy()
    wos_with_pmid = wos_df[wos_df["PMID"].notna()].copy()

    joined = pd.merge(
        pm_with_pmid, wos_with_pmid,
        on="PMID", how="inner", suffixes=("_pm", "_wos")
    )

    joined_records = []
    for _, row in joined.iterrows():
        joined_records.append({
            "PMID":              row["PMID"],
            "UID":               row["UID_wos"] if pd.notna(row.get("UID_wos")) else row.get("UID_pm"),
            "ArticleTitle":      row["ArticleTitle_pm"] if pd.notna(row.get("ArticleTitle_pm")) else row.get("ArticleTitle_wos"),
            "JournalTitle":      row["JournalTitle_pm"] if pd.notna(row.get("JournalTitle_pm")) else row.get("JournalTitle_wos"),
            "PubYear":           row["PubYear_pm"]      if pd.notna(row.get("PubYear_pm"))      else row.get("PubYear_wos"),
            "PubMonth":          row["PubMonth_pm"]     if pd.notna(row.get("PubMonth_pm"))     else row.get("PubMonth_wos"),
            "IntegrationMethod": "join",
            "Source":            "both",
        })

    joined_df = pd.DataFrame(joined_records)

    # Identify unmatched records
    joined_pmids = set(joined["PMID"].dropna())
    pubmed_unmatched = pubmed_df[~pubmed_df["PMID"].isin(joined_pmids)].copy()
    wos_unmatched    = wos_df[~wos_df["PMID"].isin(joined_pmids)].copy()

    # ── Stage 2: Record linkage on remaining unmatched ───────────────────────
    pm_rl  = pubmed_unmatched.reset_index(drop=True).copy()
    wos_rl = wos_unmatched.reset_index(drop=True).copy()

    # Lower-case helper columns
    pm_rl["article_lower"]  = pm_rl["ArticleTitle"].fillna("").str.lower()
    pm_rl["journal_lower"]  = pm_rl["JournalTitle"].fillna("").str.lower()
    pm_rl["journal_first"]  = pm_rl["JournalTitle"].apply(get_first_journal_word)
    wos_rl["article_lower"] = wos_rl["ArticleTitle"].fillna("").str.lower()
    wos_rl["journal_lower"] = wos_rl["JournalTitle"].fillna("").str.lower()
    wos_rl["journal_first"] = wos_rl["JournalTitle"].apply(get_first_journal_word)

    indexer = recordlinkage.Index()
    indexer.block("journal_first")
    candidate_links = indexer.index(pm_rl, wos_rl)

    compare = recordlinkage.Compare()
    compare.string("article_lower", "article_lower",
                   method="levenshtein", threshold=0.80, label="title_sim")
    compare.string("journal_lower", "journal_lower",
                   method="levenshtein", threshold=0.80, label="journal_sim")
    features = compare.compute(candidate_links, pm_rl, wos_rl)

    # Match if both title AND journal similarity are satisfied
    matches = features[(features["title_sim"] == 1) & (features["journal_sim"] == 1)]

    linked_records = []
    pm_linked_idx  = set()
    wos_linked_idx = set()

    # Keep only first match per pm record (highest combined score)
    best_matches = (
        matches.reset_index()
        .sort_values(["title_sim", "journal_sim"], ascending=False)
        .drop_duplicates(subset="level_0")
        .drop_duplicates(subset="level_1")
    )

    for _, row in best_matches.iterrows():
        pi = int(row["level_0"])
        wi = int(row["level_1"])
        pm_row  = pm_rl.iloc[pi]
        wos_row = wos_rl.iloc[wi]
        linked_records.append({
            "PMID":              pm_row["PMID"],
            "UID":               wos_row["UID"],
            "ArticleTitle":      pm_row["ArticleTitle"] if pd.notna(pm_row["ArticleTitle"]) else wos_row["ArticleTitle"],
            "JournalTitle":      pm_row["JournalTitle"] if pd.notna(pm_row["JournalTitle"]) else wos_row["JournalTitle"],
            "PubYear":           pm_row["PubYear"]      if pd.notna(pm_row["PubYear"])      else wos_row["PubYear"],
            "PubMonth":          pm_row["PubMonth"]     if pd.notna(pm_row["PubMonth"])     else wos_row["PubMonth"],
            "IntegrationMethod": "link",
            "Source":            "both",
        })
        pm_linked_idx.add(pi)
        wos_linked_idx.add(wi)

    linked_df = pd.DataFrame(linked_records)

    # ── Stage 3: Append remaining unmatched ─────────────────────────────────
    pubmed_unmatched2 = pm_rl[~pm_rl.index.isin(pm_linked_idx)].copy()
    wos_unmatched2    = wos_rl[~wos_rl.index.isin(wos_linked_idx)].copy()

    def make_append_df(df, source):
        out = df[["PMID", "UID", "ArticleTitle", "JournalTitle", "PubYear", "PubMonth"]].copy()
        out["IntegrationMethod"] = "append"
        out["Source"] = source
        return out

    pubmed_append_df = make_append_df(pubmed_unmatched2, "pubmed")
    wos_append_df    = make_append_df(wos_unmatched2,    "wos")

    # ── Sanity checks ────────────────────────────────────────────────────────
    assert len(pubmed_df) == len(joined_df) + len(linked_df) + len(pubmed_unmatched2), \
        "PubMed record count mismatch!"
    assert len(wos_df) == len(joined_df) + len(linked_df) + len(wos_unmatched2), \
        "WOS record count mismatch!"

    # ── Combine ──────────────────────────────────────────────────────────────
    final_df = pd.concat(
        [joined_df, linked_df, pubmed_append_df, wos_append_df],
        ignore_index=True
    )

    # Add unique RecordID and reorder columns
    final_df.insert(0, "RecordID", range(1, len(final_df) + 1))

    column_order = [
        "RecordID", "PMID", "UID", "ArticleTitle", "JournalTitle",
        "PubYear", "PubMonth", "IntegrationMethod", "Source"
    ]
    final_df = final_df[column_order]

    return final_df


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    os.makedirs("output", exist_ok=True)

    print("Parsing PubMed XML...")
    pubmed_df = parse_pubmed_xml(PUBMED_XML_PATH)
    print(f"  → {len(pubmed_df)} PubMed records")

    print("Parsing WOS JSON...")
    wos_df = parse_wos_json(WOS_JSON_PATH)
    print(f"  → {len(wos_df)} WOS records")

    # print("outputted pubmed_df")
    # pubmed_df.to_csv("/Users/jonathanyang/Downloads/pub", index=False)

    # print("output wos_df")
    # wos_df.to_csv("/Users/jonathanyang/Downloads/wos", index=False)
    print("Integrating datasets...")
    final_df = integrate(pubmed_df, wos_df)

    counts = final_df["IntegrationMethod"].value_counts()
    print(f"  join:   {counts.get('join',  0)}")
    print(f"  link:   {counts.get('link',  0)}")
    print(f"  append: {counts.get('append',0)}")
    print(f"  Total:  {len(final_df)}")

    final_df.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
