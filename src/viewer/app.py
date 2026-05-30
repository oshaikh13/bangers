from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from viewer.data import (
    REPO_ROOT,
    build_manifest,
    default_run_name,
    list_banger_indexes,
    list_discovery_runs,
    list_generic_qa_items,
    list_goal_intervals,
    list_questions,
    load_all_goals,
    load_banger,
    load_combined,
    load_generic_qa,
    load_goal,
    load_logs_window,
    load_question,
    resolve_run_path,
)

STATIC_DIR = REPO_ROOT / "viewer" / "static"


def create_app(default_discovery_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="Discovery Viewer")
    app.state.default_run = (
        default_discovery_dir.name
        if default_discovery_dir is not None
        else default_run_name()
    )

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/runs")
    def get_runs() -> dict:
        runs = list_discovery_runs()
        return {
            "default_run": app.state.default_run,
            "runs": [
                {
                    "name": run.name,
                    "goal_count": run.goal_count,
                    "stages": {
                        "goals": run.has_goals,
                        "combined": run.has_combined,
                        "bangers": run.has_bangers,
                        "questions": run.has_questions,
                        "generic_qa": run.has_generic_qa,
                    },
                }
                for run in runs
            ],
        }

    @app.get("/api/runs/{run_name}/manifest")
    def get_manifest(run_name: str) -> dict:
        run_path = _run_path_or_404(run_name)
        return build_manifest(run_path)

    @app.get("/api/runs/{run_name}/goals")
    def get_goals(run_name: str) -> dict:
        run_path = _run_path_or_404(run_name)
        return {"items": list_goal_intervals(run_path)}

    @app.get("/api/runs/{run_name}/goals/all")
    def get_all_goals(run_name: str) -> dict:
        run_path = _run_path_or_404(run_name)
        try:
            items = load_all_goals(run_path)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"items": items, "count": len(items)}

    @app.get("/api/runs/{run_name}/goals/{interval}")
    def get_goal(run_name: str, interval: int) -> dict:
        run_path = _run_path_or_404(run_name)
        try:
            goals = load_goal(run_path, interval)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"interval_index": interval, "goals": goals}

    @app.get("/api/runs/{run_name}/combined")
    def get_combined(run_name: str) -> dict:
        run_path = _run_path_or_404(run_name)
        try:
            items = load_combined(run_path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"items": items}

    @app.get("/api/runs/{run_name}/bangers")
    def get_bangers(run_name: str) -> dict:
        run_path = _run_path_or_404(run_name)
        return {"items": list_banger_indexes(run_path)}

    @app.get("/api/runs/{run_name}/bangers/{combined_index}")
    def get_banger(run_name: str, combined_index: int) -> dict:
        run_path = _run_path_or_404(run_name)
        try:
            banger = load_banger(run_path, combined_index)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"combined_index": combined_index, "banger": banger}

    @app.get("/api/runs/{run_name}/questions")
    def get_questions(run_name: str) -> dict:
        run_path = _run_path_or_404(run_name)
        try:
            items = list_questions(run_path)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"items": items}

    @app.get("/api/runs/{run_name}/questions/{question_id}")
    def get_question(run_name: str, question_id: str) -> dict:
        run_path = _run_path_or_404(run_name)
        try:
            item = load_question(run_path, question_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return item

    @app.get("/api/runs/{run_name}/generic-qa")
    def get_generic_qa_items(run_name: str) -> dict:
        run_path = _run_path_or_404(run_name)
        return {"items": list_generic_qa_items(run_path)}

    @app.get("/api/runs/{run_name}/generic-qa/{qa_type}/{interval}")
    def get_generic_qa_detail(run_name: str, qa_type: str, interval: int) -> dict:
        run_path = _run_path_or_404(run_name)
        try:
            item = load_generic_qa(run_path, qa_type, interval)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"qa_type": qa_type, "interval_index": interval, "item": item}

    @app.get("/api/logs-window")
    def get_logs_window(ts: float, before: int = 200, after: int = 200) -> dict:
        if before < 0 or after < 0:
            raise HTTPException(
                status_code=400, detail="before/after must be non-negative"
            )
        return load_logs_window(ts, before, after)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


def _run_path_or_404(run_name: str) -> Path:
    try:
        return resolve_run_path(run_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
