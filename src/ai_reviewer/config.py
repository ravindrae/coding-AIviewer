from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from ai_reviewer.models import Category, Severity


class IgnoreConfig(BaseModel):
    paths: list[str] = Field(default_factory=lambda: ["**/*.lock", "dist/**"])


class LimitsConfig(BaseModel):
    max_files: int = 25
    max_lines_changed: int = 500
    max_runtime_seconds: int = 55
    max_concurrent_llm_calls: int = 5
    max_hunks_per_call: int = 3


class SummaryConfig(BaseModel):
    include_pass_message: bool = True


class ReviewerConfig(BaseModel):
    branches: list[str] = Field(default_factory=lambda: ["main"])
    ignore: IgnoreConfig = Field(default_factory=IgnoreConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    model: str = "claude-3-5-haiku-latest"
    categories: list[str] = Field(
        default_factory=lambda: [
            "security",
            "bug",
            "performance",
            "maintainability",
            "style",
        ]
    )
    severity_threshold: str = "info"
    fail_on: list[str] = Field(default_factory=list)
    summary: SummaryConfig = Field(default_factory=SummaryConfig)

    def allowed_categories(self) -> set[Category]:
        return {Category(c) for c in self.categories if c in Category._value2member_map_}

    def meets_severity_threshold(self, severity: Severity) -> bool:
        threshold = Severity(self.severity_threshold.lower())
        return SEVERITY_ORDER[severity] <= SEVERITY_ORDER[threshold]

    def should_ignore_path(self, path: str) -> bool:
        normalized = path.lstrip("./")
        for pattern in self.ignore.paths:
            if fnmatch.fnmatch(normalized, pattern):
                return True
            if "**/" in pattern:
                suffix = pattern.split("**/")[-1]
                if fnmatch.fnmatch(normalized, suffix):
                    return True
                if fnmatch.fnmatch(os.path.basename(normalized), suffix):
                    return True
            if pattern.endswith("/**"):
                prefix = pattern[:-3]
                if normalized.startswith(prefix):
                    return True
        return False

    def branch_allowed(self, base_branch: str) -> bool:
        return base_branch in self.branches


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    github_token: str = ""
    reviewer_config_path: str = ".reviewer.yml"


def load_config(config_path: str | None = None) -> ReviewerConfig:
    env = EnvSettings()
    path = Path(config_path or env.reviewer_config_path)
    if not path.exists():
        return ReviewerConfig()
    with path.open() as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}
    return ReviewerConfig.model_validate(data)


LANGUAGE_MAP: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C",
    ".hpp": "C++",
    ".swift": "Swift",
    ".scala": "Scala",
    ".sh": "Shell",
    ".bash": "Shell",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".md": "Markdown",
    ".sql": "SQL",
    ".vue": "Vue",
    ".dart": "Dart",
    ".lua": "Lua",
    ".r": "R",
    ".m": "Objective-C",
    ".mm": "Objective-C++",
}


def detect_language(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return LANGUAGE_MAP.get(ext, "Unknown")


# Re-export for convenience in config module
from ai_reviewer.models import SEVERITY_ORDER  # noqa: E402
