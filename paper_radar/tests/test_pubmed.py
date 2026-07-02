import xml.etree.ElementTree as ET

from paper_radar.sources.pubmed import parse_article


def test_parse_pubmed_article_handles_structured_abstract():
    article = ET.fromstring(
        """
        <PubmedArticle>
          <MedlineCitation>
            <PMID>12345678</PMID>
            <Article>
              <ArticleTitle>Foundation models for EEG</ArticleTitle>
              <Abstract>
                <AbstractText Label="BACKGROUND">Why this matters.</AbstractText>
                <AbstractText Label="RESULTS">The model generalizes.</AbstractText>
              </Abstract>
              <AuthorList>
                <Author><ForeName>Ada</ForeName><LastName>Lovelace</LastName></Author>
              </AuthorList>
              <ArticleDate>
                <Year>2026</Year><Month>06</Month><Day>09</Day>
              </ArticleDate>
            </Article>
          </MedlineCitation>
        </PubmedArticle>
        """
    )
    paper = parse_article(article, "brain-signals", "2026-06-10T10:00:00+08:00")
    assert paper.id == "pubmed:12345678"
    assert paper.external_id == "12345678"
    assert paper.authors == ["Ada Lovelace"]
    assert paper.published == "2026-06-09"
    assert "BACKGROUND: Why this matters." in paper.summary
