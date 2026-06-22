from ai_reviewer.config import ReviewerConfig, load_config
from ai_reviewer.github.diff_parser import parse_diff
from tests.fixtures import SAMPLE_DIFF


def test_parse_diff_extracts_files_and_hunks():
    config = ReviewerConfig()
    files = parse_diff(SAMPLE_DIFF, config)
    paths = {f.path for f in files}
    assert "src/app.py" in paths
    assert "src/utils.ts" in paths
    assert "package-lock.json" not in paths
    assert "yarn.lock" not in paths


def test_parse_diff_hunk_line_numbers():
    config = ReviewerConfig()
    files = parse_diff(SAMPLE_DIFF, config)
    app_file = next(f for f in files if f.path == "src/app.py")
    assert len(app_file.hunks) == 1
    hunk = app_file.hunks[0]
    assert hunk.new_start == 10
    assert hunk.language == "Python"
    assert "password" in hunk.content


def test_parse_diff_respects_max_files():
    config = ReviewerConfig()
    config.limits.max_files = 1
    files = parse_diff(SAMPLE_DIFF, config)
    assert len(files) == 1


def test_load_config_from_file():
    config = load_config(".reviewer.yml")
    assert "main" in config.branches
    assert config.model == "claude-3-5-haiku-latest"
