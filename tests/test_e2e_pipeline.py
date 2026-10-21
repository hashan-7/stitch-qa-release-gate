import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
PYTHON_EXE = sys.executable


def run_stitch_cli(*args):
    cmd = [PYTHON_EXE, "-m", "stitch_cli.main", *args]
    result = subprocess.run(
        cmd,
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
    )
    return result


def test_e2e_passing_project_allows_release():
    target = FIXTURES_DIR / "test-docker-pytest-pass"
    res = run_stitch_cli("scan", "--run", str(target))
    assert res.returncode == 0
    assert "ALLOW_RELEASE" in res.stdout
    assert "Strands Decider 2B Release Gate" in res.stdout
    report_file = target / "STITCH_QA_REPORT.md"
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "Strands Decider 2B Release Gate" in content
    assert "ALLOW_RELEASE" in content


def test_e2e_failing_project_blocks_release():
    target = FIXTURES_DIR / "test-project"
    res = run_stitch_cli("scan", "--run", "--analyze", "--repair", "--code-fix", str(target))
    assert res.returncode == 1
    assert "BLOCK_RELEASE" in res.stdout
    assert "Strands Decider 2B Release Gate" in res.stdout
    report_file = target / "STITCH_QA_REPORT.md"
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "Strands Decider 2B Release Gate" in content
    assert "BLOCK_RELEASE" in content


def test_e2e_source_only_project_marks_incomplete():
    target = FIXTURES_DIR / "test-project-python-source-only"
    res = run_stitch_cli("scan", "--run", str(target))
    assert res.returncode == 1
    assert "QA_INCOMPLETE" in res.stdout
    assert "Strands Decider 2B Release Gate" in res.stdout


def test_e2e_unsupported_project_exits_cleanly():
    target = FIXTURES_DIR / "test-project-php-unsupported"
    res = run_stitch_cli("scan", "--run", str(target))
    assert res.returncode == 0
    assert "Skipping execution" in res.stdout
