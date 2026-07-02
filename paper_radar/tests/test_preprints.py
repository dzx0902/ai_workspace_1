from paper_radar.sources.preprints import parse_item


def test_parse_biorxiv_item_returns_unified_paper():
    paper = parse_item(
        {
            "doi": "10.1101/2026.01.02.123456",
            "version": "2",
            "title": "EEG decoding with flow matching",
            "authors": "Ada Lovelace; Alan Turing",
            "abstract": "<p>A decoding study.</p>",
            "category": "neuroscience",
            "date": "2026-01-02",
        },
        "biorxiv",
        "neuroscience",
        "2026-06-10T10:00:00+08:00",
    )
    assert paper.id == "biorxiv:10.1101/2026.01.02.123456"
    assert paper.external_id == "10.1101/2026.01.02.123456"
    assert paper.authors == ["Ada Lovelace", "Alan Turing"]
    assert paper.summary == "A decoding study."
    assert paper.pdf_url.endswith("v2.full.pdf")
