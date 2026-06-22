from __future__ import annotations

import hashlib
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Category(str, Enum):
    SECURITY = "security"
    BUG = "bug"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    STYLE = "style"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFO: 4,
}


class DiffHunk(BaseModel):
    path: str
    language: str
    old_start: int
    new_start: int
    new_line_count: int
    content: str
    lines_changed: int = 0


class DiffFile(BaseModel):
    path: str
    language: str
    hunks: list[DiffHunk] = Field(default_factory=list)
    is_deleted: bool = False
    is_binary: bool = False
    lines_changed: int = 0


class Finding(BaseModel):
    path: str
    line: int
    category: Category
    severity: Severity
    message: str
    suggestion: str | None = None

    @property
    def fingerprint(self) -> str:
        raw = f"{self.path}|{self.line}|{self.category.value}"
        return hashlib.sha1(raw.encode()).hexdigest()[:12]

    def comment_body(self) -> str:
        parts = [
            f"**[{self.category.value.upper()}]** ({self.severity.value})",
            "",
            self.message,
        ]
        if self.suggestion:
            parts.extend(["", f"**Suggestion:** {self.suggestion}"])
        parts.append("")
        parts.append(f"<!-- ai-reviewer:id={self.fingerprint} -->")
        return "\n".join(parts)

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.lower().strip()
        return v

    @field_validator("severity", mode="before")
    @classmethod
    def normalize_severity(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.lower().strip()
        return v


class ReviewResult(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    files_reviewed: int = 0
    files_skipped: int = 0
    truncated: bool = False
    skip_reason: str | None = None

    def count_by_category(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self.findings:
            counts[f.category.value] = counts.get(f.category.value, 0) + 1
        return counts

    def should_fail_ci(self, fail_on: list[str]) -> bool:
        if not fail_on:
            return False
        fail_set = {item.lower() for item in fail_on}
        for finding in self.findings:
            if finding.category.value in fail_set or finding.severity.value in fail_set:
                return True
        return False


SUMMARY_MARKER = "<!-- ai-reviewer:summary -->"
INLINE_MARKER_RE = re.compile(r"<!-- ai-reviewer:id=([a-f0-9]+) -->")
