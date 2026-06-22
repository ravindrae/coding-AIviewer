from ai_reviewer.analysis.categorizer import categorize_findings, normalize_finding
from ai_reviewer.config import ReviewerConfig
from ai_reviewer.models import Category, Severity


def test_normalize_finding_valid():
    config = ReviewerConfig()
    raw = {
        "path": "src/app.py",
        "line": 12,
        "category": "security",
        "severity": "high",
        "message": "Hardcoded password",
        "suggestion": "Use environment variables",
    }
    finding = normalize_finding(raw, config)
    assert finding is not None
    assert finding.category == Category.SECURITY
    assert finding.severity == Severity.HIGH
    assert finding.suggestion == "Use environment variables"


def test_normalize_finding_rejects_unknown_category():
    config = ReviewerConfig(categories=["bug", "security"])
    raw = {
        "path": "a.py",
        "line": 1,
        "category": "style",
        "severity": "low",
        "message": "nit",
    }
    assert normalize_finding(raw, config) is None


def test_normalize_finding_respects_severity_threshold():
    config = ReviewerConfig(severity_threshold="medium")
    raw = {
        "path": "a.py",
        "line": 1,
        "category": "bug",
        "severity": "info",
        "message": "minor",
    }
    assert normalize_finding(raw, config) is None


def test_categorize_findings_deduplicates():
    config = ReviewerConfig()
    raw = [
        {
            "path": "a.py",
            "line": 5,
            "category": "bug",
            "severity": "high",
            "message": "first",
        },
        {
            "path": "a.py",
            "line": 5,
            "category": "bug",
            "severity": "high",
            "message": "duplicate",
        },
    ]
    findings = categorize_findings(raw, config)
    assert len(findings) == 1
    assert findings[0].message == "first"
