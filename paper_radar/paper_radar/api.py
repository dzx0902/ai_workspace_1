from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from .chat import format_chat_report, format_paper_detail, paper_to_dict
from .pipeline import run_daily
from .storage import PaperStorage
from .utils import today_string

app = FastAPI(title="Paper Radar API")


class PaperRunReq(BaseModel):
    date: str | None = None
    limit_llm: int = 20
    no_llm: bool = True
    report_limit: int = 20


@app.get("/health")
def health():
    PaperStorage()
    return {"ok": True}


@app.get("/papers/daily")
def papers_daily(
    date_value: str | None = Query(default=None, alias="date"),
    limit: int = 20,
):
    report_date = date_value or today_string()
    try:
        date.fromisoformat(report_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="date must use YYYY-MM-DD") from exc
    limit = max(1, min(limit, 30))
    papers = PaperStorage().get_candidates_for_date(report_date)
    return {
        "ok": True,
        "date": report_date,
        "count": len(papers),
        "papers": [paper_to_dict(paper) for paper in papers[:limit]],
        "message": format_chat_report(report_date, papers, limit),
    }


@app.get("/papers/detail/{paper_id:path}")
def paper_detail(paper_id: str):
    paper = PaperStorage().get_paper(paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail=f"Paper not found: {paper_id}")
    return {
        "ok": True,
        "paper": paper_to_dict(paper),
        "message": format_paper_detail(paper),
    }


@app.post("/papers/run")
def papers_run(req: PaperRunReq):
    report_date = req.date or today_string()
    try:
        date.fromisoformat(report_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="date must use YYYY-MM-DD") from exc
    if req.limit_llm < 1 or req.report_limit < 1:
        raise HTTPException(status_code=400, detail="limits must be positive")
    paths = run_daily(report_date, req.limit_llm, req.no_llm)
    papers = PaperStorage().get_candidates_for_date(report_date)
    return {
        "ok": True,
        "date": report_date,
        "paths": [str(path) for path in paths],
        "count": len(papers),
        "message": format_chat_report(report_date, papers, min(req.report_limit, 30)),
    }
