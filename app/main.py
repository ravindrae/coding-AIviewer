from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ai_reviewer.analysis.engine import ReviewContext, ReviewEngine
from ai_reviewer.config import EnvSettings, load_config
from ai_reviewer.models import ReviewResult

app = FastAPI(title="AI Code Reviewer", version="0.1.0")


class ReviewByPrRequest(BaseModel):
    owner: str
    repo: str
    pull_number: int = Field(..., ge=1)
    base_branch: str = "main"
    config_path: Optional[str] = None
    post_comments: bool = True


class ReviewByDiffRequest(BaseModel):
    diff: str
    base_branch: str = "main"
    config_path: Optional[str] = None
    post_comments: bool = False
    owner: str = "local"
    repo: str = "local"
    pull_number: int = 0


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _get_credentials() -> tuple[str, str]:
    env = EnvSettings()
    api_key = env.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    token = env.github_token or os.environ.get("GITHUB_TOKEN", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
    return api_key, token


@app.post("/review", response_model=ReviewResult)
async def review_pr(request: ReviewByPrRequest) -> ReviewResult:
    api_key, token = _get_credentials()
    if request.post_comments and not token:
        raise HTTPException(status_code=400, detail="GITHUB_TOKEN required to post comments")

    config = load_config(request.config_path)
    ctx = ReviewContext(
        owner=request.owner,
        repo=request.repo,
        pull_number=request.pull_number,
        base_branch=request.base_branch,
        config=config,
        github_token=token or "local",
        anthropic_api_key=api_key,
        post_comments=request.post_comments,
    )
    engine = ReviewEngine(ctx)
    return await engine.run()


@app.post("/review/diff", response_model=ReviewResult)
async def review_diff(request: ReviewByDiffRequest) -> ReviewResult:
    api_key, token = _get_credentials()
    config = load_config(request.config_path)
    ctx = ReviewContext(
        owner=request.owner,
        repo=request.repo,
        pull_number=request.pull_number,
        base_branch=request.base_branch,
        config=config,
        github_token=token or "local",
        anthropic_api_key=api_key,
        diff_text=request.diff,
        post_comments=False,
    )
    engine = ReviewEngine(ctx)
    return await engine.run()
