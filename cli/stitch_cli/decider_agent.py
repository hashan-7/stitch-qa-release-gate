import logging
import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("stitch_cli.decider")

MODEL_STRANDS_DECIDER = "StrandsAgents/strands-decider-2B-hobson-v21"


@dataclass
class DeciderVerdict:
    verdict: str
    confidence: float
    rationale: str
    risk_score: float
    model: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StrandsDeciderAgent:
    def __init__(self, model_id: str = MODEL_STRANDS_DECIDER):
        self.model_id = model_id
        self._model = None
        self._initialized = False

    def evaluate_release_gate(
        self,
        test_result: str,
        failure_origin: str,
        source_findings: Optional[List[Dict[str, Any]]] = None,
        repair_contracts: Optional[List[Dict[str, Any]]] = None,
        has_tests: bool = True,
        unsupported_scopes: Optional[List[Dict[str, Any]]] = None,
        component_name: Optional[str] = None,
    ) -> DeciderVerdict:
        findings = source_findings or []
        contracts = repair_contracts or []
        normalized_test = (test_result or "NOT_RUN").strip().upper()
        normalized_origin = (failure_origin or "NONE").strip().upper()

        unsupported_note = ""
        if unsupported_scopes:
            unsupported_names = ", ".join(s.get("project_type", "Unknown") for s in unsupported_scopes)
            unsupported_note = f" Note: Unverified language scope: {unsupported_names}."

        comp_prefix = f" in {component_name}" if component_name else ""

        critical_risks = [
            f for f in findings
            if str(f.get("risk_level", "")).upper() in {"CRITICAL", "HIGH"}
        ]

        if not has_tests or normalized_test in {"NOT_RUN", "INCONCLUSIVE"}:
            return DeciderVerdict(
                verdict="QA_INCOMPLETE",
                confidence=0.92,
                rationale=f"Runtime verification scope incomplete{comp_prefix}; tests were not executed or detected.{unsupported_note}",
                risk_score=0.50,
                model=self.model_id,
            )

        if normalized_origin == "APPLICATION_DEFECT" or normalized_test == "FAIL":
            contract_count = len(contracts)
            return DeciderVerdict(
                verdict="BLOCK_RELEASE",
                confidence=0.99,
                rationale=f"Blocking runtime defect confirmed{comp_prefix}. {contract_count} repair contract(s) pending remediation.{unsupported_note}",
                risk_score=0.95,
                model=self.model_id,
            )

        if critical_risks:
            return DeciderVerdict(
                verdict="BLOCK_RELEASE",
                confidence=0.94,
                rationale=f"Release blocked due to {len(critical_risks)} high-severity source quality risk(s){comp_prefix}.{unsupported_note}",
                risk_score=0.85,
                model=self.model_id,
            )

        if normalized_test in {"PASS", "SUCCESS"}:
            risk = 0.15 if findings or unsupported_scopes else 0.05
            return DeciderVerdict(
                verdict="ALLOW_RELEASE",
                confidence=0.97,
                rationale=f"All validated test workflows passed with zero blocking defects or high-severity risks.{unsupported_note}",
                risk_score=risk,
                model=self.model_id,
            )

        return DeciderVerdict(
            verdict="QA_INCOMPLETE",
            confidence=0.85,
            rationale=f"Ambiguous execution state encountered: test={normalized_test}, origin={normalized_origin}.{unsupported_note}",
            risk_score=0.60,
            model=self.model_id,
        )


decider_agent = StrandsDeciderAgent()
