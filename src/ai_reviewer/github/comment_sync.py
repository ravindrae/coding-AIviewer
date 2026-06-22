from __future__ import annotations

from ai_reviewer.github.client import GitHubClient
from ai_reviewer.models import (
    INLINE_MARKER_RE,
    SUMMARY_MARKER,
    Finding,
    ReviewResult,
)


def parse_inline_marker(body: str) -> str | None:
    match = INLINE_MARKER_RE.search(body)
    return match.group(1) if match else None


def build_summary_body(result: ReviewResult, include_pass: bool = True) -> str:
    lines = ["## AI Code Review Summary", ""]

    if result.skip_reason:
        lines.append(f"_{result.skip_reason}_")
        lines.append("")
    elif result.truncated:
        lines.append("_Review was truncated due to time or size limits._")
        lines.append("")

    if not result.findings:
        if include_pass:
            lines.append("No issues found in the reviewed changes.")
        else:
            lines.append("Review complete.")
    else:
        counts = result.count_by_category()
        lines.append(f"Found **{len(result.findings)}** issue(s):")
        lines.append("")
        for category, count in sorted(counts.items()):
            lines.append(f"- **{category}**: {count}")
        lines.append("")
        lines.append("See inline comments for details.")

    lines.extend(["", SUMMARY_MARKER])
    return "\n".join(lines)


class CommentSync:
    def __init__(self, client: GitHubClient) -> None:
        self.client = client

    async def sync(
        self,
        pull_number: int,
        findings: list[Finding],
        result: ReviewResult,
        include_pass_message: bool = True,
    ) -> None:
        await self._sync_inline_comments(pull_number, findings)
        await self._sync_summary(pull_number, result, include_pass_message)

    async def _sync_inline_comments(
        self,
        pull_number: int,
        findings: list[Finding],
    ) -> None:
        existing = await self.client.list_review_comments(pull_number)
        bot_comments = [
            c for c in existing if parse_inline_marker(c.get("body", "")) is not None
        ]

        existing_by_id: dict[str, dict] = {}
        for comment in bot_comments:
            marker_id = parse_inline_marker(comment.get("body", ""))
            if marker_id:
                existing_by_id[marker_id] = comment

        desired: dict[str, Finding] = {f.fingerprint: f for f in findings}
        to_create: list[Finding] = []
        to_delete: list[int] = []

        for fp, finding in desired.items():
            if fp in existing_by_id:
                existing_body = existing_by_id[fp].get("body", "")
                new_body = finding.comment_body()
                if existing_body.strip() != new_body.strip():
                    await self.client.update_review_comment(existing_by_id[fp]["id"], new_body)
            else:
                to_create.append(finding)

        for fp, comment in existing_by_id.items():
            if fp not in desired:
                to_delete.append(comment["id"])

        for comment_id in to_delete:
            await self.client.delete_review_comment(comment_id)

        if to_create:
            review_comments = [
                {
                    "path": f.path,
                    "line": f.line,
                    "side": "RIGHT",
                    "body": f.comment_body(),
                }
                for f in to_create
            ]
            await self.client.create_pull_review(
                pull_number,
                body="AI code review inline comments.",
                comments=review_comments,
                event="COMMENT",
            )

    async def _sync_summary(
        self,
        pull_number: int,
        result: ReviewResult,
        include_pass_message: bool,
    ) -> None:
        body = build_summary_body(result, include_pass=include_pass_message)
        issue_comments = await self.client.list_issue_comments(pull_number)

        summary_comment = None
        for comment in issue_comments:
            if SUMMARY_MARKER in comment.get("body", ""):
                summary_comment = comment
                break

        if summary_comment:
            await self.client.update_issue_comment(summary_comment["id"], body)
        else:
            await self.client.create_issue_comment(pull_number, body)
