import pytest
from stitch_cli.bedrock_service import (
    BedrockService,
    MODEL_DEFECT_RESOLUTION,
    MODEL_REPAIR_ASSURANCE,
    MODEL_RUNTIME_QUALITY,
    MODEL_SOURCE_QUALITY,
)


def test_bedrock_service_initializes_in_mock_mode():
    service = BedrockService()
    assert service.is_mock is True


def test_extract_json_from_code_blocks():
    service = BedrockService()
    fenced_json = "```json\n{\"status\": \"OK\", \"confidence\": 0.98}\n```"
    result = service._extract_json(fenced_json)
    assert result == {"status": "OK", "confidence": 0.98}

    unfenced_json = "Here is the response: {\"valid\": true} hope it helps"
    result_unfenced = service._extract_json(unfenced_json)
    assert result_unfenced == {"valid": True}


def test_mock_source_review():
    service = BedrockService()
    payload = {
        "source_files": [{"path": "src/app.py", "lines": 25}],
    }
    result = service.invoke(MODEL_SOURCE_QUALITY, "system prompt", payload)
    assert "findings" in result
    assert result["risk_level"] == "LOW"
    assert result["release_recommendation"] == "PROCEED"


def test_mock_runtime_analysis_on_pass():
    service = BedrockService()
    payload = {
        "runtime_evidence": {
            "test_result": "PASS",
            "failures": [],
        }
    }
    result = service.invoke(MODEL_RUNTIME_QUALITY, "system prompt", payload)
    assert result["test_result"] == "PASS"
    assert result["failure_origin"] == "NONE"
    assert len(result["root_cause_groups"]) == 0


def test_mock_runtime_analysis_on_fail():
    service = BedrockService()
    payload = {
        "runtime_evidence": {
            "test_result": "FAIL",
            "failures": [
                {
                    "test_name": "test_div_by_zero",
                    "exception_type": "ZeroDivisionError",
                    "traceback_excerpt": "line 12 in div: return a / b",
                }
            ],
        }
    }
    result = service.invoke(MODEL_RUNTIME_QUALITY, "system prompt", payload)
    assert result["test_result"] == "FAIL"
    assert result["failure_origin"] == "APPLICATION_DEFECT"
    assert len(result["root_cause_groups"]) == 1
    assert "ZeroDivisionError" in result["primary_root_cause"]


def test_mock_defect_resolution():
    service = BedrockService()
    payload = {
        "root_cause_groups": [
            {"group_id": "RCG-1", "primary_cause": "Division error"}
        ]
    }
    result = service.invoke(MODEL_DEFECT_RESOLUTION, "system prompt", payload)
    assert "repair_contracts" in result
    assert len(result["repair_contracts"]) == 1
    assert result["repair_contracts"][0]["priority"] == "P1"


def test_mock_repair_assurance():
    service = BedrockService()
    payload = {
        "repair_contracts": [
            {"contract_id": "RPC-1", "repair_objective": "Fix div zero"}
        ]
    }
    result = service.invoke(MODEL_REPAIR_ASSURANCE, "system prompt", payload)
    assert "guidance" in result
    assert result["remediation_ready"] is True


def test_mock_repair_assurance_targets_dynamic_source_file():
    service = BedrockService()
    payload = {
        "source_files": [{"path": "app.py"}],
        "repair_contracts": [
            {"contract_id": "RPC-1", "repair_objective": "Fix division by zero"}
        ],
    }
    result = service.invoke(MODEL_REPAIR_ASSURANCE, "system prompt", payload)
    assert result["guidance"][0]["target_files"] == ["app.py"]
    assert "src/main.py" not in result["guidance"][0]["target_files"]


def test_bedrock_service_verify_connection_offline():
    service = BedrockService()
    diag = service.verify_connection()
    assert diag["connected"] is False
    assert diag["mode"] == "bedrock-deterministic-offline"
    assert "region" in diag
