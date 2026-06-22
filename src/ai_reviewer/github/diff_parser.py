from __future__ import annotations

import re

from ai_reviewer.config import ReviewerConfig, detect_language
from ai_reviewer.models import DiffFile, DiffHunk

DIFF_FILE_HEADER = re.compile(r"^diff --git a/.+ b/(.+)$")
DIFF_NEW_FILE = re.compile(r"^\+\+\+ b/(.+)$")
HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def parse_diff(diff_text: str, config: ReviewerConfig) -> list[DiffFile]:
    if not diff_text.strip():
        return []

    files: list[DiffFile] = []
    current_path: str | None = None
    current_language = "Unknown"
    is_deleted = False
    is_binary = False
    hunks: list[DiffHunk] = []
    lines_changed = 0

    def flush_file() -> None:
        nonlocal current_path, hunks, lines_changed, is_deleted, is_binary, current_language
        if current_path is None:
            return
        if is_deleted or is_binary:
            current_path = None
            hunks = []
            lines_changed = 0
            is_deleted = False
            is_binary = False
            return
        if config.should_ignore_path(current_path):
            current_path = None
            hunks = []
            lines_changed = 0
            return
        if hunks:
            files.append(
                DiffFile(
                    path=current_path,
                    language=current_language,
                    hunks=hunks,
                    lines_changed=lines_changed,
                )
            )
        current_path = None
        hunks = []
        lines_changed = 0
        is_deleted = False
        is_binary = False

    lines = diff_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("diff --git"):
            flush_file()
            match = DIFF_FILE_HEADER.match(line)
            if match:
                current_path = match.group(1)
                current_language = detect_language(current_path)
            i += 1
            continue

        if line.startswith("deleted file mode"):
            is_deleted = True
            i += 1
            continue

        if line.startswith("Binary files"):
            is_binary = True
            i += 1
            continue

        if line.startswith("+++ "):
            new_match = DIFF_NEW_FILE.match(line)
            if new_match:
                current_path = new_match.group(1)
                current_language = detect_language(current_path)
            elif line == "+++ /dev/null":
                is_deleted = True
            i += 1
            continue

        hunk_match = HUNK_HEADER.match(line)
        if hunk_match and current_path and not is_deleted and not is_binary:
            old_start = int(hunk_match.group(1))
            new_start = int(hunk_match.group(2))
            new_count = int(hunk_match.group(3) or "1")
            hunk_lines: list[str] = [line]
            hunk_changed = 0
            new_line = new_start
            i += 1
            while i < len(lines):
                hline = lines[i]
                if hline.startswith("diff --git") or hline.startswith("@@ "):
                    break
                hunk_lines.append(hline)
                if hline.startswith("+") and not hline.startswith("+++"):
                    hunk_changed += 1
                    new_line += 1
                elif hline.startswith("-") and not hline.startswith("---"):
                    hunk_changed += 1
                elif hline.startswith(" ") or hline.startswith("\\"):
                    new_line += 1
                i += 1
            content = "\n".join(hunk_lines)
            lines_changed += hunk_changed
            hunks.append(
                DiffHunk(
                    path=current_path,
                    language=current_language,
                    old_start=old_start,
                    new_start=new_start,
                    new_line_count=new_count,
                    content=content,
                    lines_changed=hunk_changed,
                )
            )
            continue

        i += 1

    flush_file()
    return _apply_limits(files, config)


def _apply_limits(files: list[DiffFile], config: ReviewerConfig) -> list[DiffFile]:
    filtered: list[DiffFile] = []
    total_lines = 0
    for f in files:
        if len(filtered) >= config.limits.max_files:
            break
        if total_lines + f.lines_changed > config.limits.max_lines_changed:
            remaining = config.limits.max_lines_changed - total_lines
            if remaining <= 0:
                break
        filtered.append(f)
        total_lines += f.lines_changed
    return filtered
