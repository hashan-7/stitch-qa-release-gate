import pytest
from stitch_cli.decider_agent import (
    ReleaseGateInterventionHandler,
    StrandsDeciderAgent,
)
from strands.interventions import InterventionHandler


def test_decider_blocks_on_failing_tests():
    agent = StrandsDeciderAgent()
    verdict = agent.evaluate_release_gate(
        test_result="FAIL",
        failure_origin="APPLICATION_DEFECT",
        repair_contracts=[{"contract_id": "RPC-1"}],
        has_tests=True,
    )
    assert verdict.verdict == "BLOCK_RELEASE"
    assert verdict.confidence >= 0.95
    assert verdict.risk_score >= 0.90
    assert "Blocking runtime defect" in verdict.rationale
    assert "Deny" in verdict.intervention_action
    assert "BLOCK_RELEASE" in verdict.probabilities
    assert verdict.probabilities["BLOCK_RELEASE"] > 0.90


def test_decider_allows_on_passing_tests():
    agent = StrandsDeciderAgent()
    verdict = agent.evaluate_release_gate(
        test_result="PASS",
        failure_origin="NONE",
        source_findings=[],
        has_tests=True,
    )
    assert verdict.verdict == "ALLOW_RELEASE"
    assert verdict.confidence >= 0.95
    assert verdict.risk_score < 0.20
    assert "zero blocking defects" in verdict.rationale
    assert "Proceed" in verdict.intervention_action
    assert "ALLOW_RELEASE" in verdict.probabilities
    assert verdict.probabilities["ALLOW_RELEASE"] > 0.90


def test_decider_incomplete_on_no_tests():
    agent = StrandsDeciderAgent()
    verdict = agent.evaluate_release_gate(
        test_result="NOT_RUN",
        failure_origin="NONE",
        has_tests=False,
    )
    assert verdict.verdict == "QA_INCOMPLETE"
    assert verdict.confidence >= 0.90
    assert "incomplete" in verdict.rationale.lower()
    assert "Guide" in verdict.intervention_action
    assert "QA_INCOMPLETE" in verdict.probabilities


def test_decider_blocks_on_critical_source_risk():
    agent = StrandsDeciderAgent()
    critical_findings = [
        {"rule_id": "SQL_INJECTION", "risk_level": "CRITICAL", "message": "Raw query execution"}
    ]
    verdict = agent.evaluate_release_gate(
        test_result="PASS",
        failure_origin="NONE",
        source_findings=critical_findings,
        has_tests=True,
    )
    assert verdict.verdict == "BLOCK_RELEASE"
    assert "high-severity source quality risk" in verdict.rationale
    assert "Deny" in verdict.intervention_action


def test_release_gate_intervention_handler_strands_contract():
    handler = ReleaseGateInterventionHandler()
    assert isinstance(handler, InterventionHandler)
    assert handler.name == "release-gate-intervention"

    question = handler.build_choice_question("test_result=FAIL")
    assert question.type == "choice"
    assert "ALLOW_RELEASE" in question.criteria
    assert "BLOCK_RELEASE" in question.criteria
    assert "QA_INCOMPLETE" in question.criteria
