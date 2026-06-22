from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Optional

import typer

from ai_reviewer.analysis.engine import ReviewContext, ReviewEngine
from ai_reviewer.config import EnvSettings, load_config

app = typer.Typer(help="AI-powered code reviewer for GitHub Pull Requests")


def _load_event_context(event_path: str) -> dict:
    with Path(event_path).open() as f:
        return json.load(f)


def _resolve_pr_context(
    repo: Optional[str],
    pr: Optional[int],
    event_path: Optional[str],
) -> tuple[str, str, int, str]:
    if repo and pr:
        owner, name = repo.split("/", 1)
        base_branch = "main"
        return owner, name, pr, base_branch

    event_file = event_path or os.environ.get("GITHUB_EVENT_PATH", "")
    if not event_file or not Path(event_file).exists():
        typer.echo("Error: provide --repo and --pr, or run inside GitHub Actions.", err=True)
        raise typer.Exit(code=1)

    event = _load_event_context(event_file)
    pull_request = event.get("pull_request")
    if not pull_request:
        typer.echo("Error: event is not a pull_request event.", err=True)
        raise typer.Exit(code=1)

    repo_full = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo_full:
        repo_full = event.get("repository", {}).get("full_name", "")
    if not repo_full:
        typer.echo("Error: could not determine repository.", err=True)
        raise typer.Exit(code=1)

    owner, name = repo_full.split("/", 1)
    pull_number = int(pull_request["number"])
    base_branch = pull_request.get("base", {}).get("ref", "main")
    return owner, name, pull_number, base_branch


@app.command()
def review(
    repo: Optional[str] = typer.Option(
        None, help="Repository in owner/name format"
    ),
    pr: Optional[int] = typer.Option(None, help="Pull request number"),
    config_path: Optional[str] = typer.Option(
        None, help="Path to .reviewer.yml"
    ),
    event_path: Optional[str] = typer.Option(
        None, help="Path to GitHub event JSON"
    ),
    dry_run: bool = typer.Option(
        False, help="Analyze only; do not post comments"
    ),
) -> None:
    """Review a pull request and post AI-generated comments."""
    env = EnvSettings()
    config = load_config(config_path)

    if not env.anthropic_api_key:
        typer.echo("Error: ANTHROPIC_API_KEY is required.", err=True)
        raise typer.Exit(code=1)

    github_token = env.github_token or os.environ.get("GITHUB_TOKEN", "")
    if not github_token and not dry_run:
        typer.echo("Error: GITHUB_TOKEN is required to post comments.", err=True)
        raise typer.Exit(code=1)

    owner, name, pull_number, base_branch = _resolve_pr_context(repo, pr, event_path)

    typer.echo(f"Reviewing {owner}/{name} PR #{pull_number} (base: {base_branch})")

    ctx = ReviewContext(
        owner=owner,
        repo=name,
        pull_number=pull_number,
        base_branch=base_branch,
        config=config,
        github_token=github_token or "dry-run",
        anthropic_api_key=env.anthropic_api_key,
        post_comments=not dry_run,
    )

    engine = ReviewEngine(ctx)
    result = asyncio.run(engine.run())

    if result.skip_reason:
        typer.echo(result.skip_reason)

    typer.echo(
        f"Review complete: {len(result.findings)} finding(s), "
        f"{result.files_reviewed} file(s) reviewed"
    )
    if result.truncated:
        typer.echo("Note: review was truncated due to time or size limits.")

    for finding in result.findings:
        typer.echo(
            f"  [{finding.category.value}/{finding.severity.value}] "
            f"{finding.path}:{finding.line} - {finding.message}"
        )

    if result.should_fail_ci(config.fail_on):
        typer.echo("Failing CI due to configured fail_on rules.", err=True)
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
