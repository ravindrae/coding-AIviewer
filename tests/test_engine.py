from unittest.mock import AsyncMock, patch

import pytest

from ai_reviewer.analysis.engine import ReviewContext, ReviewEngine
from ai_reviewer.config import ReviewerConfig
from ai_reviewer.models import Category, Finding, Severity
from tests.fixtures import SAMPLE_DIFF


@pytest.mark.asyncio
async def test_engine_run_with_diff_no_comments():
    config = ReviewerConfig()
    ctx = ReviewContext(
        owner="test",
        repo="repo",
        pull_number=1,
        base_branch="main",
        config=config,
        github_token="token",
        anthropic_api_key="key",
        diff_text=SAMPLE_DIFF,
        post_comments=False,
    )

    mock_findings = [
        Finding(
            path="src/app.py",
            line=12,
            category=Category.SECURITY,
            severity=Severity.HIGH,
            message="Hardcoded secret",
        )
    ]

    engine = ReviewEngine(ctx)
    with patch.object(
        engine.llm,
        "analyze_hunks",
        new=AsyncMock(return_value=mock_findings),
    ):
        result = await engine.run()

    assert result.files_reviewed >= 1
    assert len(result.findings) >= 1
    assert result.findings[0].category == Category.SECURITY


@pytest.mark.asyncio
async def test_engine_skips_disallowed_branch():
    config = ReviewerConfig(branches=["main"])
    ctx = ReviewContext(
        owner="test",
        repo="repo",
        pull_number=1,
        base_branch="feature-x",
        config=config,
        github_token="token",
        anthropic_api_key="key",
        diff_text=SAMPLE_DIFF,
        post_comments=False,
    )
    engine = ReviewEngine(ctx)
    result = await engine.run()
    assert result.skip_reason is not None
    assert "feature-x" in result.skip_reason
