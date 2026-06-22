from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from ai_reviewer.config import ReviewerConfig
from ai_reviewer.github.comment_sync import CommentSync
from ai_reviewer.github.diff_parser import parse_diff
from ai_reviewer.github.client import GitHubClient
from ai_reviewer.llm.anthropic import AnthropicClient
from ai_reviewer.models import DiffFile, DiffHunk, Finding, ReviewResult


@dataclass
class ReviewContext:
    owner: str
    repo: str
    pull_number: int
    base_branch: str
    config: ReviewerConfig
    github_token: str
    anthropic_api_key: str
    diff_text: str | None = None
    post_comments: bool = True


@dataclass
class _Batch:
    file: DiffFile
    hunks: list[DiffHunk]


class ReviewEngine:
    def __init__(self, ctx: ReviewContext) -> None:
        self.ctx = ctx
        self.llm = AnthropicClient(ctx.anthropic_api_key, ctx.config)

    async def run(self) -> ReviewResult:
        config = self.ctx.config

        if not config.branch_allowed(self.ctx.base_branch):
            return ReviewResult(
                skip_reason=f"Base branch `{self.ctx.base_branch}` is not configured for review."
            )

        async with GitHubClient(
            self.ctx.github_token, self.ctx.owner, self.ctx.repo
        ) as gh:
            diff_text = self.ctx.diff_text
            if diff_text is None:
                diff_text = await gh.get_pull_diff(self.ctx.pull_number)

            files = parse_diff(diff_text, config)
            if not files:
                result = ReviewResult(
                    files_reviewed=0,
                    skip_reason="No reviewable changes in diff.",
                )
                if self.ctx.post_comments:
                    sync = CommentSync(gh)
                    await sync.sync(
                        self.ctx.pull_number,
                        [],
                        result,
                        include_pass_message=config.summary.include_pass_message,
                    )
                return result

            batches = self._build_batches(files, config.limits.max_hunks_per_call)
            deadline = time.monotonic() + config.limits.max_runtime_seconds
            truncated = False
            findings: list[Finding] = []
            seen: set[tuple[str, int, str]] = set()

            semaphore = asyncio.Semaphore(config.limits.max_concurrent_llm_calls)

            async def process_batch(batch: _Batch) -> list[Finding]:
                nonlocal truncated
                if time.monotonic() >= deadline:
                    truncated = True
                    return []
                async with semaphore:
                    if time.monotonic() >= deadline:
                        truncated = True
                        return []
                    try:
                        return await asyncio.wait_for(
                            self.llm.analyze_hunks(batch.file, batch.hunks),
                            timeout=max(1, deadline - time.monotonic()),
                        )
                    except (asyncio.TimeoutError, Exception):
                        truncated = True
                        return []

            tasks = [process_batch(b) for b in batches]
            batch_results = await asyncio.gather(*tasks)

            for batch_findings in batch_results:
                for finding in batch_findings:
                    key = (finding.path, finding.line, finding.category.value)
                    if key in seen:
                        continue
                    seen.add(key)
                    findings.append(finding)

            result = ReviewResult(
                findings=findings,
                files_reviewed=len(files),
                truncated=truncated,
            )

            if self.ctx.post_comments:
                sync = CommentSync(gh)
                await sync.sync(
                    self.ctx.pull_number,
                    findings,
                    result,
                    include_pass_message=config.summary.include_pass_message,
                )

            return result

    def _build_batches(self, files: list[DiffFile], max_hunks: int) -> list[_Batch]:
        batches: list[_Batch] = []
        for file in files:
            hunks = file.hunks
            for i in range(0, len(hunks), max_hunks):
                batches.append(_Batch(file=file, hunks=hunks[i : i + max_hunks]))
        return batches
