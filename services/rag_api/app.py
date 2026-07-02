from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from dev_agents.core import apply_patch_task, generate_patch, generate_plan, list_repos, repo_diff, run_safe_test
from scripts.config import CHROMA_HOST, CHROMA_PORT, ensure_dirs
from scripts.path_router import PathPolicyError, resolve_input_file
from scripts.process_file import process
from scripts.query_kb import query_kb
from scripts.video_to_note import video_to_note
from scripts.video_transcribe_to_note import video_transcribe_to_note
from scripts.web_to_note import web_to_note

PAPER_RADAR_ROOT = Path(__file__).resolve().parents[2] / "paper_radar"
if str(PAPER_RADAR_ROOT) not in sys.path:
    sys.path.insert(0, str(PAPER_RADAR_ROOT))

from paper_radar.chat import format_chat_report, format_paper_detail, paper_to_dict
from paper_radar.pipeline import run_daily as run_paper_radar
from paper_radar.storage import PaperStorage
from paper_radar.utils import today_string

app = FastAPI(title="AI Workspace RAG API")


class AskReq(BaseModel):
    question: str
    mode: str = "api"
    source_type: str | None = None
    category: str | None = None
    n_results: int = 6


class FileReq(BaseModel):
    source_type: str
    category: str = "default"
    filename: str
    output_dir: str | None = None
    mode: str = "api"


class WebReq(BaseModel):
    url: str
    category: str = "default"
    output_dir: str | None = None
    mode: str = "api"


class VideoReq(BaseModel):
    url: str
    category: str = "default"
    output_dir: str | None = None
    mode: str = "api"


class TranscribeReq(BaseModel):
    url_or_file: str
    category: str = "default"
    output_dir: str | None = None
    mode: str = "api"
    whisper_model: str = "base"


class DevReq(BaseModel):
    repo_name: str
    task_description: str = ""
    task_type: str = "plan"
    mode: str = "api"


class DevTestReq(BaseModel):
    repo_name: str
    command: str
    allow_shell: bool = False


class DevDiffReq(BaseModel):
    repo_name: str


class DevApplyReq(BaseModel):
    task_id: str
    confirm: bool = False


class PaperRunReq(BaseModel):
    date: str | None = None
    limit_llm: int = 20
    no_llm: bool = True
    report_limit: int = 20


def handle_error(exc: Exception) -> None:
    if isinstance(exc, (PathPolicyError, PermissionError)):
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if isinstance(exc, FileNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
def health():
    try:
        ensure_dirs()
        return {"ok": True, "chroma": {"host": CHROMA_HOST, "port": CHROMA_PORT}}
    except Exception as exc:
        handle_error(exc)


@app.post("/ask")
def ask(req: AskReq):
    try:
        answer = query_kb(req.question, mode=req.mode, source_type=req.source_type, category=req.category, n_results=req.n_results)
        return {"ok": True, "answer": answer}
    except Exception as exc:
        handle_error(exc)


@app.post("/file")
def file(req: FileReq):
    try:
        resolve_input_file(req.filename, source_type=req.source_type)
        result = process(req.filename, note_mode=req.mode, source_type=req.source_type, category=req.category, output_dir=req.output_dir)
        return {"ok": True, "result": result}
    except Exception as exc:
        handle_error(exc)


@app.post("/web")
def web(req: WebReq):
    try:
        return {"ok": True, "result": web_to_note(req.url, mode=req.mode, category=req.category, output_dir=req.output_dir)}
    except Exception as exc:
        handle_error(exc)


@app.post("/video")
def video(req: VideoReq):
    try:
        return {"ok": True, "result": video_to_note(req.url, mode=req.mode, category=req.category, output_dir=req.output_dir)}
    except Exception as exc:
        handle_error(exc)


@app.post("/transcribe")
def transcribe(req: TranscribeReq):
    try:
        result = video_transcribe_to_note(req.url_or_file, note_mode=req.mode, whisper_model=req.whisper_model, category=req.category, output_dir=req.output_dir)
        return {"ok": True, "result": result}
    except Exception as exc:
        handle_error(exc)


@app.get("/dev/repos")
def dev_repos():
    try:
        return {"ok": True, "repos": list_repos()}
    except Exception as exc:
        handle_error(exc)


@app.post("/dev/plan")
def dev_plan(req: DevReq):
    try:
        return {"ok": True, "result": generate_plan(req.repo_name, req.task_description, task_type="plan", mode=req.mode)}
    except Exception as exc:
        handle_error(exc)


@app.post("/dev/patch")
def dev_patch(req: DevReq):
    try:
        return {"ok": True, "result": generate_patch(req.repo_name, req.task_description, mode=req.mode)}
    except Exception as exc:
        handle_error(exc)


@app.post("/dev/review")
def dev_review(req: DevReq):
    try:
        desc = req.task_description or "Review this repository for bugs, risks, and missing tests."
        return {"ok": True, "result": generate_plan(req.repo_name, desc, task_type="review", mode=req.mode)}
    except Exception as exc:
        handle_error(exc)


@app.post("/dev/test")
def dev_test(req: DevTestReq):
    try:
        return {"ok": True, "result": run_safe_test(req.repo_name, req.command, allow_shell=req.allow_shell)}
    except Exception as exc:
        handle_error(exc)


@app.post("/dev/diff")
def dev_diff(req: DevDiffReq):
    try:
        return {"ok": True, "result": repo_diff(req.repo_name)}
    except Exception as exc:
        handle_error(exc)


@app.post("/dev/apply")
def dev_apply(req: DevApplyReq):
    try:
        return {"ok": True, "result": apply_patch_task(req.task_id, confirm=req.confirm)}
    except Exception as exc:
        handle_error(exc)


@app.post("/dev/task")
def dev_task(req: DevReq):
    try:
        if req.task_type == "patch":
            return {"ok": True, "result": generate_patch(req.repo_name, req.task_description, mode=req.mode)}
        return {"ok": True, "result": generate_plan(req.repo_name, req.task_description, task_type=req.task_type, mode=req.mode)}
    except Exception as exc:
        handle_error(exc)


@app.get("/papers/daily")
def papers_daily(
    date_value: str | None = Query(default=None, alias="date"),
    limit: int = 20,
):
    try:
        report_date = date_value or today_string()
        date.fromisoformat(report_date)
        limit = max(1, min(limit, 30))
        papers = PaperStorage().get_candidates_for_date(report_date)
        return {
            "ok": True,
            "date": report_date,
            "count": len(papers),
            "papers": [paper_to_dict(paper) for paper in papers[:limit]],
            "message": format_chat_report(report_date, papers, limit),
        }
    except Exception as exc:
        handle_error(exc)


@app.get("/papers/detail/{paper_id:path}")
def paper_detail(paper_id: str):
    try:
        paper = PaperStorage().get_paper(paper_id)
        if paper is None:
            raise HTTPException(status_code=404, detail=f"Paper not found: {paper_id}")
        return {
            "ok": True,
            "paper": paper_to_dict(paper),
            "message": format_paper_detail(paper),
        }
    except HTTPException:
        raise
    except Exception as exc:
        handle_error(exc)


@app.post("/papers/run")
def papers_run(req: PaperRunReq):
    try:
        report_date = req.date or today_string()
        date.fromisoformat(report_date)
        if req.limit_llm < 1 or req.report_limit < 1:
            raise ValueError("limits must be positive")
        paths = run_paper_radar(report_date, req.limit_llm, req.no_llm)
        papers = PaperStorage().get_candidates_for_date(report_date)
        return {
            "ok": True,
            "date": report_date,
            "paths": [str(path) for path in paths],
            "count": len(papers),
            "message": format_chat_report(report_date, papers, min(req.report_limit, 30)),
        }
    except Exception as exc:
        handle_error(exc)
