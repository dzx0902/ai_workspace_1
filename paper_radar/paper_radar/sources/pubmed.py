from __future__ import annotations

import os
import time
import xml.etree.ElementTree as ET
from typing import Any

import requests

from ..models import Paper
from ..utils import clean_text, load_environment, now_iso
from .http import build_session

EUTILS_ROOT = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _text(element: ET.Element | None) -> str:
    return clean_text("".join(element.itertext())) if element is not None else ""


def _published(article: ET.Element) -> str:
    article_date = article.find(".//ArticleDate")
    if article_date is not None:
        year = _text(article_date.find("Year"))
        month = _text(article_date.find("Month")).zfill(2)
        day = _text(article_date.find("Day")).zfill(2)
        if year:
            return "-".join(value for value in (year, month, day) if value)
    pub_date = article.find(".//JournalIssue/PubDate")
    if pub_date is None:
        return ""
    medline_date = _text(pub_date.find("MedlineDate"))
    if medline_date:
        return medline_date
    year = _text(pub_date.find("Year"))
    month = _text(pub_date.find("Month"))
    day = _text(pub_date.find("Day"))
    return "-".join(value for value in (year, month, day) if value)


def parse_article(article: ET.Element, category: str, fetched_at: str) -> Paper:
    pmid = _text(article.find(".//PMID"))
    if not pmid:
        raise ValueError("PubMed article did not contain a PMID")
    title = _text(article.find(".//ArticleTitle")) or "(untitled)"
    authors: list[str] = []
    for author in article.findall(".//AuthorList/Author"):
        collective = _text(author.find("CollectiveName"))
        if collective:
            authors.append(collective)
            continue
        name = " ".join(
            value
            for value in (
                _text(author.find("ForeName")),
                _text(author.find("LastName")),
            )
            if value
        )
        if name:
            authors.append(name)
    abstract_parts = []
    for abstract in article.findall(".//Abstract/AbstractText"):
        label = clean_text(abstract.attrib.get("Label"))
        value = _text(abstract)
        if value:
            abstract_parts.append(f"{label}: {value}" if label else value)
    return Paper(
        id=f"pubmed:{pmid}",
        external_id=pmid,
        title=title,
        authors=authors,
        summary="\n\n".join(abstract_parts),
        source="pubmed",
        source_category=category,
        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        pdf_url="",
        published=_published(article),
        fetched_at=fetched_at,
    )


def fetch_source(
    source: dict[str, Any],
    limit: int | None = None,
    timeout: int = 30,
) -> list[Paper]:
    load_environment()
    query = clean_text(source.get("query"))
    if not query:
        raise ValueError(f"PubMed source {source.get('name')!r} requires query")
    effective_limit = limit if limit is not None else int(source.get("max_results", 100))
    if effective_limit < 1:
        return []

    api_key = os.getenv("NCBI_API_KEY", "").strip()
    common: dict[str, str] = {
        "tool": os.getenv("NCBI_TOOL", "paper_radar"),
    }
    email = os.getenv("NCBI_EMAIL", "").strip()
    if email:
        common["email"] = email
    if api_key:
        common["api_key"] = api_key

    session = build_session()
    search_params = {
        **common,
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": str(effective_limit),
        "sort": str(source.get("sort", "pub date")),
    }
    try:
        search = session.get(
            f"{EUTILS_ROOT}/esearch.fcgi",
            params=search_params,
            timeout=timeout,
        )
        search.raise_for_status()
        ids = search.json().get("esearchresult", {}).get("idlist", [])
    except (requests.RequestException, ValueError) as exc:
        raise RuntimeError(f"PubMed ESearch failed: {exc}") from exc
    if not ids:
        return []

    # Stay below NCBI's unauthenticated request limit.
    time.sleep(0.11 if api_key else 0.34)
    try:
        fetched = session.get(
            f"{EUTILS_ROOT}/efetch.fcgi",
            params={
                **common,
                "db": "pubmed",
                "id": ",".join(ids),
                "retmode": "xml",
            },
            timeout=timeout,
        )
        fetched.raise_for_status()
        root = ET.fromstring(fetched.content)
    except (requests.RequestException, ET.ParseError) as exc:
        raise RuntimeError(f"PubMed EFetch failed: {exc}") from exc

    fetched_at = now_iso()
    category = str(source.get("category", "biomedical"))
    papers = []
    for article in root.findall("./PubmedArticle"):
        try:
            papers.append(parse_article(article, category, fetched_at))
        except ValueError:
            continue
    return papers[:effective_limit]
