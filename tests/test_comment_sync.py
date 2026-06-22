from ai_reviewer.github.comment_sync import build_summary_body, parse_inline_marker
from ai_reviewer.models import Category, Finding, ReviewResult, SUMMARY_MARKER, Severity


def test_finding_fingerprint_stable():
    f = Finding(
        path="src/a.py",
        line=10,
        category=Category.SECURITY,
        severity=Severity.HIGH,
        message="issue",
    )
    assert f.fingerprint == f.fingerprint
    assert f"<!-- ai-reviewer:id={f.fingerprint} -->" in f.comment_body()


def test_parse_inline_marker():
    body = "**[BUG]** (high)\n\nSomething wrong\n\n<!-- ai-reviewer:id=abc123def456 -->"
    assert parse_inline_marker(body) == "abc123def456"
    assert parse_inline_marker("no marker") is None


def test_build_summary_with_findings():
    result = ReviewResult(
        findings=[
            Finding(
                path="a.py",
                line=1,
                category=Category.BUG,
                severity=Severity.HIGH,
                message="bug",
            ),
            Finding(
                path="b.py",
                line=2,
                category=Category.SECURITY,
                severity=Severity.CRITICAL,
                message="sec",
            ),
        ],
        files_reviewed=2,
    )
    body = build_summary_body(result)
    assert SUMMARY_MARKER in body
    assert "**bug**: 1" in body
    assert "**security**: 1" in body


def test_build_summary_pass_message():
    result = ReviewResult(files_reviewed=1)
    body = build_summary_body(result, include_pass=True)
    assert "No issues found" in body
    assert SUMMARY_MARKER in body


def test_review_result_should_fail_ci():
    result = ReviewResult(
        findings=[
            Finding(
                path="a.py",
                line=1,
                category=Category.SECURITY,
                severity=Severity.HIGH,
                message="x",
            )
        ]
    )
    assert result.should_fail_ci(["security"]) is True
    assert result.should_fail_ci(["bug"]) is False
