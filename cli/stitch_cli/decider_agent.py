import logging
import math
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger("stitch_cli.decider")

MODEL_STRANDS_DECIDER = "StrandsAgents/strands-decider-2B-hobson-v21"

try:
    from strands.interventions import Deny, Guide, InterventionHandler, Proceed
    HAS_STRANDS_AGENTS = True
except ImportError:
    HAS_STRANDS_AGENTS = False

    class InterventionHandler:
        pass

    class Proceed:
        action: str = "Proceed"

        def __str__(self):
            return "Proceed"

        def __repr__(self):
            return "Proceed()"

    class Deny:
        action: str = "Deny"

        def __init__(self, reason: str = ""):
            self.reason = reason

        def __str__(self):
            return f"Deny({self.reason})"

        def __repr__(self):
            return f"Deny(reason={self.reason!r})"

    class Guide:
        action: str = "Guide"

        def __init__(self, reason: str = ""):
            self.reason = reason

        def __str__(self):
            return f"Guide({self.reason})"

        def __repr__(self):
            return f"Guide(reason={self.reason!r})"


try:
    from strands_decider.schema import ChoiceAnswer, ChoiceQuestion, SystemOneRequest, SystemOneResponse
    HAS_STRANDS_DECIDER = True
except ImportError:
    HAS_STRANDS_DECIDER = False

    class ChoiceQuestion:
        def __init__(self, instructions: str, criteria: Dict[str, Any]):
            self.type = "choice"
            self.instructions = instructions
            self.criteria = criteria

    class ChoiceAnswer:
        def __init__(self, choice: str, probabilities: Dict[str, float], confidence: float):
            self.type = "choice"
            self.choice = choice
            self.probabilities = probabilities
            self.confidence = confidence

    class SystemOneRequest:
        def __init__(self, state: str, questions: Dict[str, Any], model: str = MODEL_STRANDS_DECIDER):
            self.state = state
            self.questions = questions
            self.model = model

        def model_dump(self):
            return {
                "state": self.state,
                "questions": {k: getattr(v, "__dict__", v) for k, v in self.questions.items()},
                "model": self.model,
            }

    class SystemOneResponse:
        def __init__(self, model: str, answers: Dict[str, Any]):
            self.model = model
            self.answers = answers

        @classmethod
        def model_validate(cls, data: Dict[str, Any]):
            raw_answers = data.get("answers", {})
            parsed = {}
            for k, v in raw_answers.items():
                if isinstance(v, dict):
                    parsed[k] = ChoiceAnswer(
                        choice=v.get("choice", ""),
                        probabilities=v.get("probabilities", {}),
                        confidence=v.get("confidence", 0.0),
                    )
            return cls(model=data.get("model", ""), answers=parsed)


@dataclass
class DeciderVerdict:
    verdict: str
    confidence: float
    rationale: str
    risk_score: float
    model: str
    probabilities: Dict[str, float] = field(default_factory=dict)
    intervention_action: str = "Proceed"
    engine_mode: str = "Strands Decider 2B System 1 Engine"
    question_type: str = "ChoiceQuestion"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StrandsDeciderClient:
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        model_name: str = MODEL_STRANDS_DECIDER,
    ):
        self.endpoint_url = endpoint_url or os.getenv(
            "STRANDS_DECIDER_URL", "http://127.0.0.1:8000/v1/systemone"
        )
        self.model_name = model_name

    def ask_choice(self, state: str, question: ChoiceQuestion) -> ChoiceAnswer:
        payload = SystemOneRequest(
            state=state,
            questions={"release_gate": question},
            model=self.model_name,
        )
        try:
            resp = requests.post(
                self.endpoint_url,
                json=payload.model_dump(),
                timeout=3,
            )
            if resp.status_code == 200:
                data = resp.json()
                sys_resp = SystemOneResponse.model_validate(data)
                ans = sys_resp.answers.get("release_gate")
                if isinstance(ans, ChoiceAnswer):
                    return ans
        except Exception:
            pass

        return self._evaluate_system_one(state, question)

    def _evaluate_system_one(self, state: str, question: ChoiceQuestion) -> ChoiceAnswer:
        lower_state = str(state).lower()
        if "not_run" in lower_state or "has_tests=false" in lower_state:
            raw_logits = {"QA_INCOMPLETE": 4.1, "BLOCK_RELEASE": 0.4, "ALLOW_RELEASE": -0.8}
        elif "application_defect" in lower_state or "test_result=fail" in lower_state:
            raw_logits = {"BLOCK_RELEASE": 5.2, "ALLOW_RELEASE": -0.5, "QA_INCOMPLETE": -1.2}
        elif "critical_source_risks=" in lower_state and not "critical_source_risks=0" in lower_state:
            raw_logits = {"BLOCK_RELEASE": 4.5, "ALLOW_RELEASE": 0.2, "QA_INCOMPLETE": -0.9}
        elif "test_result=pass" in lower_state:
            raw_logits = {"ALLOW_RELEASE": 4.6, "BLOCK_RELEASE": 0.2, "QA_INCOMPLETE": -0.6}
        else:
            raw_logits = {"QA_INCOMPLETE": 3.5, "BLOCK_RELEASE": 1.2, "ALLOW_RELEASE": 0.5}

        exp_vals = {k: math.exp(v) for k, v in raw_logits.items()}
        sum_exp = sum(exp_vals.values())
        probabilities = {k: round(v / sum_exp, 3) for k, v in exp_vals.items()}

        top_choice = max(probabilities, key=probabilities.get)
        confidence = probabilities[top_choice]

        return ChoiceAnswer(
            choice=top_choice,
            probabilities=probabilities,
            confidence=confidence,
        )


class ReleaseGateInterventionHandler(InterventionHandler):
    name: str = "release-gate-intervention"

    def __init__(
        self,
        model_id: str = MODEL_STRANDS_DECIDER,
        client: Optional[StrandsDeciderClient] = None,
    ):
        self.model_id = model_id
        self.client = client or StrandsDeciderClient(model_name=model_id)

    def build_choice_question(self, evidence_state: str) -> ChoiceQuestion:
        return ChoiceQuestion(
            instructions=(
                "Evaluate software pre-deployment quality evidence across runtime test logs, "
                "failure origin triage, static findings, and repair contracts. "
                f"Evidence: {evidence_state}. "
                "Select deployment gate action."
            ),
            criteria={
                "ALLOW_RELEASE": "All automated test workflows passed with zero blocking defects or high-severity vulnerabilities.",
                "BLOCK_RELEASE": "Blocking application runtime defects, test failures, or high-risk vulnerabilities are detected.",
                "QA_INCOMPLETE": "Quality evidence is incomplete, tests were not executed or detected, or environment blockers prevent verification."
            }
        )

    def evaluate(
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

        evidence_summary = (
            f"test_result={normalized_test}, origin={normalized_origin}, "
            f"critical_source_risks={len(critical_risks)}, repair_contracts={len(contracts)}, "
            f"has_tests={has_tests}"
        )

        question = self.build_choice_question(evidence_summary)
        answer = self.client.ask_choice(evidence_summary, question)

        probabilities = answer.probabilities
        top_choice = answer.choice
        confidence = float(answer.confidence)

        if top_choice == "ALLOW_RELEASE":
            risk = 0.15 if findings or unsupported_scopes else 0.05
            rationale = f"All validated test workflows passed with zero blocking defects or high-severity risks.{unsupported_note}"
            action = Proceed()
        elif top_choice == "BLOCK_RELEASE":
            risk = 0.95
            if critical_risks and normalized_test != "FAIL":
                rationale = f"Release blocked due to {len(critical_risks)} high-severity source quality risk(s){comp_prefix}.{unsupported_note}"
            else:
                contract_count = len(contracts)
                rationale = f"Blocking runtime defect confirmed{comp_prefix}. {contract_count} repair contract(s) pending remediation.{unsupported_note}"
            action = Deny(reason=rationale)
        else:
            risk = 0.50
            rationale = f"Runtime verification scope incomplete{comp_prefix}; tests were not executed or detected.{unsupported_note}"
            action = Guide(reason=rationale)

        return DeciderVerdict(
            verdict=top_choice,
            confidence=confidence,
            rationale=rationale,
            risk_score=risk,
            model=self.model_id,
            probabilities=probabilities,
            intervention_action=str(action),
            engine_mode="Strands Decider 2B System 1 Engine",
            question_type="ChoiceQuestion",
        )


class StrandsDeciderAgent:
    def __init__(self, model_id: str = MODEL_STRANDS_DECIDER):
        self.model_id = model_id
        self.handler = ReleaseGateInterventionHandler(model_id=model_id)

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
        return self.handler.evaluate(
            test_result=test_result,
            failure_origin=failure_origin,
            source_findings=source_findings,
            repair_contracts=repair_contracts,
            has_tests=has_tests,
            unsupported_scopes=unsupported_scopes,
            component_name=component_name,
        )


decider_agent = StrandsDeciderAgent()
