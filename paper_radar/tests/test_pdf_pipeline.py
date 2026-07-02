from pathlib import Path

import fitz

from paper_radar.models import Paper
from paper_radar.pdf.downloader import PDFDownloader
from paper_radar.pdf.extractor import PDFExtractor, extract_pdf
from paper_radar.storage import PaperStorage


def make_paper(pdf_path: str = "") -> Paper:
    return Paper(
        id="arxiv:2606.00001",
        external_id="2606.00001",
        title="EEG Decoding",
        source="arxiv",
        url="https://arxiv.org/abs/2606.00001",
        pdf_url="https://arxiv.org/pdf/2606.00001.pdf",
        fetched_at="2026-06-10T10:00:00+08:00",
        pdf_path=pdf_path,
    )


def create_pdf(path: Path) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "EEG Decoding\n\nAbstract\nA cross-subject decoding method.\n\n"
        "1 Introduction\nBody text.\n\n2 Methods\nTransformer model.",
    )
    document.save(path)
    document.close()


def test_downloader_skips_existing_pdf(tmp_path):
    storage = PaperStorage(tmp_path / "papers.db")
    paper = make_paper()
    storage.upsert_paper(paper)
    download_dir = tmp_path / "pdfs"
    download_dir.mkdir()
    existing = download_dir / "arxiv_2606.00001.pdf"
    existing.write_bytes(b"%PDF-existing")

    downloader = PDFDownloader(
        storage,
        {
            "pdf_download_dir": str(download_dir),
            "download_timeout": 10,
            "overwrite_existing_pdf": False,
            "allowed_sources": ["arxiv"],
        },
    )
    assert downloader.download(paper) == existing
    saved = storage.get_paper(paper.id)
    assert saved.pdf_download_status == "downloaded"
    assert saved.pdf_path == str(existing)


def test_extract_pdf_and_update_storage(tmp_path):
    pdf_path = tmp_path / "paper.pdf"
    create_pdf(pdf_path)
    paper = make_paper(str(pdf_path))
    extracted = extract_pdf(pdf_path, paper)
    assert extracted.page_count == 1
    assert any("Introduction" in heading for heading in extracted.section_headings)
    assert "cross-subject decoding" in extracted.abstract

    storage = PaperStorage(tmp_path / "papers.db")
    storage.upsert_paper(paper)
    storage.update_pdf_download(paper.id, "downloaded", str(pdf_path))
    paper = storage.get_paper(paper.id)
    extractor = PDFExtractor(
        storage,
        {"extracted_text_dir": str(tmp_path / "texts")},
    )
    output = extractor.extract(paper)
    assert output is not None
    assert "## Body" in output.read_text(encoding="utf-8")
    assert storage.get_paper(paper.id).pdf_extract_status == "extracted"
