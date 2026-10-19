import os
from pathlib import Path
from stitch_cli.reporter import write_github_step_summary, generate_report


def test_write_github_step_summary_when_env_not_set(monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    result = write_github_step_summary("# Sample Report")
    assert result is False


def test_write_github_step_summary_when_env_set(monkeypatch, tmp_path):
    summary_file = tmp_path / "step_summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    result = write_github_step_summary("# Sample Report 1")
    assert result is True
    assert summary_file.exists()
    content = summary_file.read_text(encoding="utf-8")
    assert "# Sample Report 1" in content

    # Test appending second block
    result2 = write_github_step_summary("## Second Section")
    assert result2 is True
    content2 = summary_file.read_text(encoding="utf-8")
    assert "# Sample Report 1" in content2
    assert "## Second Section" in content2


def test_generate_report_writes_to_github_step_summary(monkeypatch, tmp_path):
    summary_file = tmp_path / "step_summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    scan_result = {
        "project_path": str(project_dir),
        "project_type": "Python Project",
        "total_files": 1,
        "total_folders": 1,
        "ignored_items": 0,
        "files": ["app.py"],
    }
    execution_result = {
        "status": "PASSED",
        "command": "python -m pytest",
        "command_profile": "PYTHON_PYTEST",
        "execution_policy": "BUILT_IN_ONLY",
        "execution_strategy": "ARGUMENT_LIST",
        "shell_enabled": False,
        "command_args": ["-m", "pytest"],
        "executable": "python",
        "validation_status": "VALIDATED",
        "success": True,
        "exit_code": 0,
        "stdout": "1 passed",
        "stderr": "",
        "runtime_evidence": {
            "execution_status": "COMPLETED",
            "test_result": "PASS",
            "evidence_quality": "STRUCTURED",
            "report_source": "JUNIT_XML",
            "test_summary": {"total": 1, "passed": 1, "failed": 0, "errors": 0, "skipped": 0},
        },
    }

    report_path = generate_report(scan_result, execution_result=execution_result)
    assert report_path.exists()
    assert summary_file.exists()
    summary_content = summary_file.read_text(encoding="utf-8")
    assert "Stitch QA Report" in summary_content
    assert "Executive QA Summary" in summary_content
