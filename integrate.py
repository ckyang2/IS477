from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from lxml import etree
import recordlinkage


PUBMED_XML_PATH = Path("pubmed_retractions_2024.xml")
WOS_JSON_PATH = Path("wos_retractions_2024.json")
OUTPUT_PATH = Path("output/integrated_retractions_2024.csv")

MONTH_MAP = {
    "JAN": 1,
    "JANUARY": 1,
    "FEB": 2,
    "FEBRUARY": 2,
    "MAR": 3,
    "MARCH": 3,
    "APR": 4,
    "APRIL": 4,
    "MAY": 5,
    "JUN": 6,
    "JUNE": 6,
    "JUL": 7,
    "JULY": 7,
    "AUG": 8,
    "AUGUST": 8,
    "SEP": 9,
    "SEPT": 9,
    "SEPTEMBER": 9,
    "OCT": 10,
    "OCTOBER": 10,
    "NOV": 11,
    "NOVEMBER": 11,
    "DEC": 12,
    "DECEMBER": 12,
}


# ---------- generic helpers ----------
def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")
    value = str(value).strip()
    return value or None


def _coalesce(*values: Any) -> str | None:
    for value in values:
        value = _text(value)
        if value is not None:
            return value
    return None


def _nested_get(obj: Any, *path: str) -> Any:
    cur = obj
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return None
    return cur


def _find_first(obj: Any, keys: Iterable[str]) -> Any:
    """Depth-first search for the first matching key in nested dict/list data."""
    if isinstance(obj, dict):
        for key in keys:
            if key in obj and obj[key] not in (None, "", [], {}):
                return obj[key]
        for value in obj.values():
            found = _find_first(value, keys)
            if found not in (None, "", [], {}):
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_first(item, keys)
            if found not in (None, "", [], {}):
                return found
    return None


def normalize_month(value: Any) -> int | None:
    raw = _text(value)
    if raw is None:
        return None

    cleaned = raw.upper().strip()
    cleaned = re.sub(r"\s+", " ", cleaned)

    # Pure numeric month strings such as "01" or "1"
    if re.fullmatch(r"\d{1,2}", cleaned):
        month = int(cleaned)
        return month if 1 <= month <= 12 else None

    # Pick the first month token from strings like "FEB-MAR" or "DEC 31"
    month_match = re.search(
        r"JAN(?:UARY)?|FEB(?:RUARY)?|MAR(?:CH)?|APR(?:IL)?|MAY|JUN(?:E)?|"
        r"JUL(?:Y)?|AUG(?:UST)?|SEP(?:T(?:EMBER)?)?|OCT(?:OBER)?|"
        r"NOV(?:EMBER)?|DEC(?:EMBER)?",
        cleaned,
    )
    if month_match:
        token = month_match.group(0)
        return MONTH_MAP[token]

    # Fallback: strings beginning with digits, e.g. "12 31"
    digit_match = re.match(r"(\d{1,2})", cleaned)
    if digit_match:
        month = int(digit_match.group(1))
        return month if 1 <= month <= 12 else None

    return None


def normalize_string(value: Any) -> str:
    text = _text(value) or ""
    text = text.casefold()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def journal_block_key(value: Any) -> str:
    normalized = normalize_string(value)
    if not normalized:
        return ""
    words = [w for w in re.split(r"\s+", normalized) if w]
    while words and words[0] == "the":
        words.pop(0)
    return words[0] if words else ""


# ---------- parsing ----------
def parse_pubmed_xml(path: Path) -> pd.DataFrame:
    tree = etree.parse(str(path))
    rows: list[dict[str, Any]] = []

    for article in tree.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID")
        article_title = "".join(article.find(".//ArticleTitle").itertext()).strip() if article.find(".//ArticleTitle") is not None else None
        journal_title = article.findtext(".//Journal/Title") or article.findtext(".//MedlineJournalInfo/MedlineTA")
        pub_year = article.findtext(".//PubDate/Year")
        pub_month = article.findtext(".//PubDate/Month")

        # Fall back to ArticleDate when needed.
        if pub_year is None:
            pub_year = article.findtext(".//ArticleDate/Year")
        if pub_month is None:
            pub_month = article.findtext(".//ArticleDate/Month")

        rows.append(
            {
                "PMID": _text(pmid),
                "UID": None,
                "ArticleTitle": _text(article_title),
                "JournalTitle": _text(journal_title),
                "PubYear": pd.to_numeric(_text(pub_year), errors="coerce"),
                "PubMonth": normalize_month(pub_month),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("No PubMed records were parsed from the XML file.")
    return df


def parse_wos_json(path: Path) -> pd.DataFrame:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    candidates = (
        _nested_get(payload, "Data", "Records", "records", "REC")
        or _nested_get(payload, "Data", "records")
        or _nested_get(payload, "records")
        or _nested_get(payload, "hits")
        or payload
    )

    if isinstance(candidates, dict):
        # Sometimes the response keeps records in a single dict or nested slot.
        candidates = candidates.get("REC") or candidates.get("records") or [candidates]

    if not isinstance(candidates, list):
        raise ValueError("Could not locate a list of Web of Science records in the JSON file.")

    rows: list[dict[str, Any]] = []
    for record in candidates:
        uid = _coalesce(
            _find_first(record, ["UID", "uid", "UT", "ut"]),
        )
        pmid = _coalesce(
            _find_first(record, ["pmid", "PMID"]),
        )
        article_title = _coalesce(
            _find_first(record, ["ArticleTitle", "articleTitle", "title", "Title", "content"]),
        )
        journal_title = _coalesce(
            _find_first(record, ["JournalTitle", "journalTitle", "sourceTitle", "source", "full_title", "title"]),
        )
        pub_year = _coalesce(
            _find_first(record, ["PubYear", "pubyear", "year", "Year", "sortdate"]),
        )
        pub_month = _coalesce(
            _find_first(record, ["PubMonth", "pubmonth", "month", "Month"]),
        )

        # Try to extract year/month from a date string if specific fields were absent.
        if pub_year is None or pub_month is None:
            date_value = _coalesce(_find_first(record, ["pub_date", "pubDate", "date", "sortdate", "early_access_date"]))
            if date_value:
                year_match = re.search(r"\b(19|20)\d{2}\b", date_value)
                if pub_year is None and year_match:
                    pub_year = year_match.group(0)
                if pub_month is None:
                    pub_month = date_value

        rows.append(
            {
                "PMID": _text(pmid),
                "UID": _text(uid),
                "ArticleTitle": _text(article_title),
                "JournalTitle": _text(journal_title),
                "PubYear": pd.to_numeric(_text(pub_year), errors="coerce"),
                "PubMonth": normalize_month(pub_month),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("No Web of Science records were parsed from the JSON file.")
    return df


# ---------- integration ----------
def integrate(pubmed_df: pd.DataFrame, wos_df: pd.DataFrame) -> pd.DataFrame:
    pubmed_df = pubmed_df.copy()
    wos_df = wos_df.copy()

    pubmed_df["PMID"] = pubmed_df["PMID"].astype("string").str.strip()
    wos_df["PMID"] = wos_df["PMID"].astype("string").str.strip()
    pubmed_df["UID"] = pubmed_df["UID"].astype("string")
    wos_df["UID"] = wos_df["UID"].astype("string")

    pubmed_df["ArticleTitle_lower"] = pubmed_df["ArticleTitle"].map(normalize_string)
    pubmed_df["JournalTitle_lower"] = pubmed_df["JournalTitle"].map(normalize_string)
    wos_df["ArticleTitle_lower"] = wos_df["ArticleTitle"].map(normalize_string)
    wos_df["JournalTitle_lower"] = wos_df["JournalTitle"].map(normalize_string)

    pubmed_df["journal_block_key"] = pubmed_df["JournalTitle"].map(journal_block_key)
    wos_df["journal_block_key"] = wos_df["JournalTitle"].map(journal_block_key)

    # Step 1: exact join on PMID.
    joined_df = pubmed_df.merge(
        wos_df,
        on="PMID",
        how="inner",
        suffixes=("_pubmed", "_wos"),
    )

    if not joined_df.empty:
        joined_df = pd.DataFrame(
            {
                "PMID": joined_df["PMID"],
                "UID": joined_df["UID_wos"].combine_first(joined_df["UID_pubmed"]),
                "ArticleTitle": joined_df["ArticleTitle_pubmed"].combine_first(joined_df["ArticleTitle_wos"]),
                "JournalTitle": joined_df["JournalTitle_pubmed"].combine_first(joined_df["JournalTitle_wos"]),
                "PubYear": joined_df["PubYear_pubmed"].combine_first(joined_df["PubYear_wos"]),
                "PubMonth": joined_df["PubMonth_pubmed"].combine_first(joined_df["PubMonth_wos"]),
                "IntegrationMethod": "join",
                "Source": "both",
            }
        )
    else:
        joined_df = pd.DataFrame(columns=["PMID", "UID", "ArticleTitle", "JournalTitle", "PubYear", "PubMonth", "IntegrationMethod", "Source"])

    joined_pmids = set(joined_df["PMID"].dropna().astype(str))
    pubmed_unmatched = pubmed_df.loc[~pubmed_df["PMID"].astype(str).isin(joined_pmids)].copy()
    wos_unmatched = wos_df.loc[~wos_df["PMID"].astype(str).isin(joined_pmids)].copy()

    # Step 2: record linkage on remaining unmatched records.
    linked_df = pd.DataFrame(columns=["PMID", "UID", "ArticleTitle", "JournalTitle", "PubYear", "PubMonth", "IntegrationMethod", "Source"])
    matched_pubmed_idx: set[int] = set()
    matched_wos_idx: set[int] = set()

    if not pubmed_unmatched.empty and not wos_unmatched.empty:
        indexer = recordlinkage.Index()
        indexer.block(left_on="journal_block_key", right_on="journal_block_key")
        candidate_links = indexer.index(pubmed_unmatched, wos_unmatched)

        if len(candidate_links) > 0:
            compare = recordlinkage.Compare()
            compare.string(
                "ArticleTitle_lower",
                "ArticleTitle_lower",
                method="levenshtein",
                threshold=0.80,
                label="article_match",
            )
            compare.string(
                "JournalTitle_lower",
                "JournalTitle_lower",
                method="levenshtein",
                threshold=0.80,
                label="journal_match",
            )
            features = compare.compute(candidate_links, pubmed_unmatched, wos_unmatched)
            accepted = features[(features["article_match"] == 1) & (features["journal_match"] == 1)].copy()

            if not accepted.empty:
                accepted = accepted.reset_index().rename(columns={accepted.index.names[0] or "level_0": "pubmed_idx", accepted.index.names[1] or "level_1": "wos_idx"})
                # Greedy one-to-one matching, highest score first.
                accepted["score"] = accepted["article_match"] + accepted["journal_match"]
                accepted = accepted.sort_values(["score", "pubmed_idx", "wos_idx"], ascending=[False, True, True])

                linked_rows: list[dict[str, Any]] = []
                for _, row in accepted.iterrows():
                    p_idx = int(row["pubmed_idx"])
                    w_idx = int(row["wos_idx"])
                    if p_idx in matched_pubmed_idx or w_idx in matched_wos_idx:
                        continue
                    matched_pubmed_idx.add(p_idx)
                    matched_wos_idx.add(w_idx)

                    p = pubmed_unmatched.loc[p_idx]
                    w = wos_unmatched.loc[w_idx]
                    linked_rows.append(
                        {
                            "PMID": p["PMID"] if pd.notna(p["PMID"]) else w["PMID"],
                            "UID": w["UID"] if pd.notna(w["UID"]) else p["UID"],
                            "ArticleTitle": p["ArticleTitle"] if pd.notna(p["ArticleTitle"]) else w["ArticleTitle"],
                            "JournalTitle": p["JournalTitle"] if pd.notna(p["JournalTitle"]) else w["JournalTitle"],
                            "PubYear": p["PubYear"] if pd.notna(p["PubYear"]) else w["PubYear"],
                            "PubMonth": p["PubMonth"] if pd.notna(p["PubMonth"]) else w["PubMonth"],
                            "IntegrationMethod": "link",
                            "Source": "both",
                        }
                    )

                linked_df = pd.DataFrame(linked_rows)

    pubmed_remaining = pubmed_unmatched.loc[~pubmed_unmatched.index.isin(matched_pubmed_idx)].copy()
    wos_remaining = wos_unmatched.loc[~wos_unmatched.index.isin(matched_wos_idx)].copy()

    # Step 3: append all remaining unmatched records.
    pubmed_appended = pd.DataFrame(
        {
            "PMID": pubmed_remaining["PMID"],
            "UID": pubmed_remaining["UID"],
            "ArticleTitle": pubmed_remaining["ArticleTitle"],
            "JournalTitle": pubmed_remaining["JournalTitle"],
            "PubYear": pubmed_remaining["PubYear"],
            "PubMonth": pubmed_remaining["PubMonth"],
            "IntegrationMethod": "append",
            "Source": "pubmed",
        }
    )
    wos_appended = pd.DataFrame(
        {
            "PMID": wos_remaining["PMID"],
            "UID": wos_remaining["UID"],
            "ArticleTitle": wos_remaining["ArticleTitle"],
            "JournalTitle": wos_remaining["JournalTitle"],
            "PubYear": wos_remaining["PubYear"],
            "PubMonth": wos_remaining["PubMonth"],
            "IntegrationMethod": "append",
            "Source": "wos",
        }
    )

    final_df = pd.concat([joined_df, linked_df, pubmed_appended, wos_appended], ignore_index=True)

    final_df.insert(0, "RecordID", [f"R{i:07d}" for i in range(1, len(final_df) + 1)])
    final_df = final_df[
        [
            "RecordID",
            "PMID",
            "UID",
            "ArticleTitle",
            "JournalTitle",
            "PubYear",
            "PubMonth",
            "IntegrationMethod",
            "Source",
        ]
    ]

    # Controlled vocabulary and type cleanup.
    final_df["IntegrationMethod"] = pd.Categorical(final_df["IntegrationMethod"], categories=["join", "link", "append"])
    final_df["Source"] = pd.Categorical(final_df["Source"], categories=["pubmed", "wos", "both"])
    final_df["PubYear"] = pd.to_numeric(final_df["PubYear"], errors="coerce").astype("Int64")
    final_df["PubMonth"] = pd.to_numeric(final_df["PubMonth"], errors="coerce").astype("Int64")

    # Sanity checks from the prompt.
    assert len(pubmed_df) == len(joined_df) + len(linked_df) + len(pubmed_remaining)
    assert len(wos_df) == len(joined_df) + len(linked_df) + len(wos_remaining)
    assert final_df["RecordID"].is_unique
    assert list(final_df.columns) == [
        "RecordID",
        "PMID",
        "UID",
        "ArticleTitle",
        "JournalTitle",
        "PubYear",
        "PubMonth",
        "IntegrationMethod",
        "Source",
    ]

    return final_df


def main() -> None:
    pubmed_df = parse_pubmed_xml(PUBMED_XML_PATH)
    wos_df = parse_wos_json(WOS_JSON_PATH)
    final_df = integrate(pubmed_df, wos_df)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(OUTPUT_PATH, index=False)

    print(f"Wrote {len(final_df):,} records to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
