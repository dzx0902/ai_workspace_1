from __future__ import annotations

from .models import Paper


def paper_to_dict(paper: Paper) -> dict:
    return {
        "id": paper.id,
        "external_id": paper.external_id,
        "title": paper.title,
        "authors": paper.authors,
        "summary": paper.summary,
        "source": paper.source,
        "source_category": paper.source_category,
        "url": paper.url,
        "pdf_url": paper.pdf_url,
        "published": paper.published,
        "rule_score": paper.rule_score,
        "matched_keywords": paper.matched_keywords,
        "llm_score": paper.llm_score,
        "llm_category": paper.llm_category,
        "llm_decision": paper.llm_decision,
        "llm_reason": paper.llm_reason,
        "note_priority": paper.note_priority,
        "status": paper.status,
        "pdf_path": paper.pdf_path,
        "pdf_download_status": paper.pdf_download_status,
        "pdf_download_error": paper.pdf_download_error,
        "extracted_text_path": paper.extracted_text_path,
        "pdf_extract_status": paper.pdf_extract_status,
        "pdf_extract_error": paper.pdf_extract_error,
        "paper_note_path": paper.paper_note_path,
        "full_summary_status": paper.full_summary_status,
        "full_summary_error": paper.full_summary_error,
    }


def _decision(paper: Paper) -> str:
    if paper.llm_decision:
        return paper.llm_decision
    if paper.status == "rule_skipped":
        return "skip"
    return "candidate"


def format_chat_report(report_date: str, papers: list[Paper], limit: int = 10) -> str:
    ranked = [paper for paper in papers if _decision(paper) != "skip"]
    ranked.sort(
        key=lambda paper: (
            paper.llm_decision == "read",
            paper.llm_decision == "skim",
            paper.llm_score if paper.llm_score is not None else paper.rule_score or 0,
        ),
        reverse=True,
    )
    selected = ranked[:limit]
    read_count = sum(paper.llm_decision == "read" for paper in papers)
    skim_count = sum(paper.llm_decision == "skim" for paper in papers)
    lines = [
        f"Paper Radar | {report_date}",
        f"共抓取 {len(papers)} 篇，候选 {len(ranked)} 篇，精读 {read_count}，略读 {skim_count}",
        "",
    ]
    if not selected:
        lines.append("今天没有通过初筛的论文。")
        return "\n".join(lines)
    for index, paper in enumerate(selected, 1):
        score = paper.llm_score if paper.llm_score is not None else paper.rule_score or 0
        score_label = f"LLM {score:g}/10" if paper.llm_score is not None else f"规则分 {score:g}"
        reason = paper.llm_reason or "关键词初筛候选"
        lines.extend(
            [
                f"{index}. {paper.title}",
                f"[{paper.source_category}] {_decision(paper)} | {score_label}",
                reason,
                f"原文：{paper.url}",
                f"PDF：{paper.pdf_url}",
                "",
            ]
        )
    lines.append("查看单篇详情：/paper <arXiv ID>")
    return "\n".join(lines).rstrip()


def format_paper_detail(paper: Paper) -> str:
    authors = ", ".join(paper.authors) or "-"
    score = paper.llm_score if paper.llm_score is not None else paper.rule_score or 0
    score_label = f"LLM {score:g}/10" if paper.llm_score is not None else f"规则分 {score:g}"
    reason = paper.llm_reason or "尚未执行 LLM 评分。"
    return "\n".join(
        [
            paper.title,
            f"Paper ID：{paper.id}",
            f"作者：{authors}",
            f"分类：{paper.source_category}",
            f"发布时间：{paper.published or '-'}",
            f"判断：{_decision(paper)} | {score_label}",
            f"理由：{reason}",
            "",
            paper.summary or "无摘要。",
            "",
            f"原文：{paper.url}",
            f"PDF：{paper.pdf_url}",
        ]
    )
