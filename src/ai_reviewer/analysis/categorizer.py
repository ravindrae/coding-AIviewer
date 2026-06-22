from __future__ import annotations

from typing import Any

from ai_reviewer.config import ReviewerConfig
from ai_reviewer.models import Category, Finding, Severity


def normalize_finding(raw: dict[str, Any], config: ReviewerConfig) -> Finding | None:
    try:
        category = Category(str(raw.get("category", "")).lower())
        severity = Severity(str(raw.get("severity", "info")).lower())
    except ValueError:
        return None

    if category not in config.allowed_categories():
        return None
    if not config.meets_severity_threshold(severity):
        return None

    path = str(raw.get("path", "")).strip()
    message = str(raw.get("message", "")).strip()
    if not path or not message:
        return None

    try:
        line = int(raw.get("line", 0))
    except (TypeError, ValueError):
        return None
    if line <= 0:
        return None

    suggestion = raw.get("suggestion")
    if suggestion is not None:
        suggestion = str(suggestion).strip() or None

    return Finding(
        path=path,
        line=line,
        category=category,
        severity=severity,
        message=message,
        suggestion=suggestion,
    )


def categorize_findings(
    raw_findings: list[dict[str, Any]],
    config: ReviewerConfig,
) -> list[Finding]:
    results: list[Finding] = []
    seen: set[tuple[str, int, str]] = set()

    for raw in raw_findings:
        finding = normalize_finding(raw, config)
        if finding is None:
            continue
        key = (finding.path, finding.line, finding.category.value)
        if key in seen:
            continue
        seen.add(key)
        results.append(finding)

    results.sort(key=lambda f: (f.path, f.line, f.category.value))
    return results
