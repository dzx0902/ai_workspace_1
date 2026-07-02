from paper_radar.sources.arxiv_rss import extract_arxiv_id, parse_entry


def test_extract_arxiv_id_removes_version_and_pdf_suffix():
    assert extract_arxiv_id("https://arxiv.org/abs/2401.12345v2") == "2401.12345"
    assert extract_arxiv_id("https://arxiv.org/pdf/2401.12345v3.pdf") == "2401.12345"


def test_parse_entry_handles_html_and_missing_author_list():
    entry = {
        "link": "https://arxiv.org/abs/2401.12345v1",
        "title": "  EEG <b>Decoding</b> ",
        "description": "<p>A neural decoding method.</p>",
        "author": "Ada Lovelace and Alan Turing",
        "published": "Mon, 01 Jan 2024 00:00:00 GMT",
    }
    paper = parse_entry(entry, "q-bio.NC", fetched_at="2026-06-08T10:00:00+08:00")
    assert paper.id == "2401.12345"
    assert paper.title == "EEG Decoding"
    assert paper.authors == ["Ada Lovelace", "Alan Turing"]
    assert paper.pdf_url == "https://arxiv.org/pdf/2401.12345.pdf"
