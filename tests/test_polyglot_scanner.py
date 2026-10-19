import pytest
from pathlib import Path
from stitch_cli.scanner import detect_all_project_types, scan_project
from stitch_cli.decider_agent import StrandsDeciderAgent, DeciderVerdict


def test_detect_all_project_types_single_python():
    files = ["requirements.txt", "calculator.py", "tests/test_calc.py"]
    res = detect_all_project_types(files)
    assert res["primary"] == "Python Project"
    assert res["supported"] == ["Python Project"]
    assert res["unsupported"] == []
    assert "Python Project" in res["all"]


def test_detect_all_project_types_single_maven():
    files = ["pom.xml", "src/main/java/App.java", "src/test/java/AppTest.java"]
    res = detect_all_project_types(files)
    assert res["primary"] == "Java Maven Project"
    assert res["supported"] == ["Java Maven Project"]
    assert res["unsupported"] == []


def test_detect_all_project_types_polyglot():
    files = [
        "pom.xml",
        "src/main/java/App.java",
        "requirements.txt",
        "calculator.py",
        "tests/test_calc.py",
        "Cargo.toml",
        "src/lib.rs",
    ]
    res = detect_all_project_types(files)
    assert "Java Maven Project" in res["supported"]
    assert "Python Project" in res["supported"]
    assert "Rust Project" in res["unsupported"]
    assert len(res["supported"]) == 2
    assert len(res["unsupported"]) == 1


def test_scan_project_polyglot_structure(tmp_path):
    (tmp_path / "pom.xml").write_text("<project></project>", encoding="utf-8")
    java_dir = tmp_path / "src" / "main" / "java"
    java_dir.mkdir(parents=True)
    (java_dir / "App.java").write_text("class App {}", encoding="utf-8")

    (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")

    (tmp_path / "Cargo.toml").write_text('[package]\nname = "demo"\n', encoding="utf-8")
    (tmp_path / "src" / "lib.rs").write_text("pub fn run() {}\n", encoding="utf-8")

    scan = scan_project(tmp_path)
    assert scan["is_polyglot"] is True
    assert "Java Maven Project" in scan["supported_project_types"]
    assert "Python Project" in scan["supported_project_types"]
    assert "Rust Project" in scan["unsupported_project_types"]
    assert len(scan["profiles"]) == 2
    assert len(scan["unsupported_scopes"]) == 1
    assert scan["unsupported_scopes"][0]["project_type"] == "Rust Project"


def test_strands_decider_polyglot_defect_blocking():
    agent = StrandsDeciderAgent()
    verdict = agent.evaluate_release_gate(
        test_result="FAIL",
        failure_origin="APPLICATION_DEFECT",
        source_findings=[],
        repair_contracts=[{"contract_id": "RC-1"}],
        has_tests=True,
        unsupported_scopes=[{"project_type": "Rust Project"}],
        component_name="Python Project",
    )
    assert verdict.verdict == "BLOCK_RELEASE"
    assert verdict.confidence == 0.99
    assert "Python Project" in verdict.rationale
    assert "Rust Project" in verdict.rationale
    assert "1 repair contract(s)" in verdict.rationale


def test_strands_decider_polyglot_all_passing():
    agent = StrandsDeciderAgent()
    verdict = agent.evaluate_release_gate(
        test_result="PASS",
        failure_origin="NONE",
        source_findings=[],
        repair_contracts=[],
        has_tests=True,
        unsupported_scopes=[{"project_type": "Rust Project"}],
        component_name="Multi-Ecosystem",
    )
    assert verdict.verdict == "ALLOW_RELEASE"
    assert verdict.confidence == 0.97
    assert "Rust Project" in verdict.rationale
