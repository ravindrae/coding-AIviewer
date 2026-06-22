# AI Code Reviewer

AI-powered pull request code reviewer for GitHub Actions. Analyzes PR diffs with Anthropic Claude, posts categorized inline comments and a summary, and keeps comments idempotent across re-runs.

## Features

- Triggers on pull request events (opened, synchronize, reopened)
- Reads PR diff and analyzes changed hunks only
- Categorizes findings: security, bug, performance, maintainability, style
- Posts inline review comments and a summary comment
- Configurable target branches and ignore paths
- Idempotent comments (no duplicate spam on re-runs)
- Target: under 60 seconds, low API cost, multi-language support

## Quick start

### 1. Add secret

Add `ANTHROPIC_API_KEY` to your repository or organization secrets.

### 2. Copy workflow

Copy [`.github/workflows/pr-review.yml`](.github/workflows/pr-review.yml) and [`.github/actions/ai-review/action.yml`](.github/actions/ai-review/action.yml) into your repo, or reference this repo as a reusable action.

### 3. Configure

Copy [`.reviewer.yml`](.reviewer.yml) to your repo root and adjust branches, ignore paths, and limits.

## Configuration

See [`.reviewer.yml`](.reviewer.yml) for all options. Key settings:

| Setting | Description |
|---------|-------------|
| `branches` | PR base branches to review |
| `ignore.paths` | Glob patterns to skip |
| `limits.max_files` | Max files per review |
| `limits.max_runtime_seconds` | Hard timeout (default 55s) |
| `model` | Anthropic model ID |
| `fail_on` | Categories/severities that fail CI |

Environment variables: `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, `REVIEWER_CONFIG_PATH`.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[api,dev]"

# CLI (requires GITHUB_TOKEN and ANTHROPIC_API_KEY)
export GITHUB_TOKEN=ghp_...
export ANTHROPIC_API_KEY=sk-ant-...
ai-reviewer review --repo owner/repo --pr 123

# FastAPI (optional)
uvicorn app.main:app --reload
```

## License

MIT
