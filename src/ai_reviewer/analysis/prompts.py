from __future__ import annotations

from ai_reviewer.config import ReviewerConfig
from ai_reviewer.models import DiffFile, DiffHunk


def build_system_prompt(config: ReviewerConfig) -> str:
    categories = ", ".join(config.categories)
    return f"""You are an expert code reviewer analyzing pull request diffs.

Review the provided code changes and report actionable issues only.
Categories (use exactly one per finding): {categories}

Severity levels: critical, high, medium, low, info

Rules:
- Focus on real bugs, security issues, performance problems, and meaningful maintainability concerns.
- Skip nitpicks and style issues unless they hurt readability significantly.
- Only report issues in lines that were added or modified (the diff hunk).
- Use the line number from the NEW file side of the diff.
- Minimum severity to report: {config.severity_threshold}
- If no issues found in a batch, return an empty findings list.
- Be concise in messages; include a short suggestion when helpful.
"""


def build_batch_prompt(file: DiffFile, hunks: list[DiffHunk]) -> str:
    sections = [
        f"File: {file.path}",
        f"Language: {file.language}",
        "",
        "Review these diff hunks:",
    ]
    for hunk in hunks:
        sections.extend(["", hunk.content])
    return "\n".join(sections)


FINDINGS_TOOL = {
    "name": "report_findings",
    "description": "Report code review findings from the analyzed diff hunks.",
    "input_schema": {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path"},
                        "line": {
                            "type": "integer",
                            "description": "Line number in the new file",
                        },
                        "category": {
                            "type": "string",
                            "enum": [
                                "security",
                                "bug",
                                "performance",
                                "maintainability",
                                "style",
                            ],
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low", "info"],
                        },
                        "message": {"type": "string"},
                        "suggestion": {"type": "string"},
                    },
                    "required": ["path", "line", "category", "severity", "message"],
                },
            }
        },
        "required": ["findings"],
    },
}
