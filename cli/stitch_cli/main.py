import os
import sys
from pathlib import Path

import click
from rich.console import Console

from stitch_cli.agent_client import (
    analyze_logs_with_agent,
    build_unavailable_code_guidance,
    build_unavailable_log_analysis,
    build_unavailable_repair_guidance,
    build_unavailable_source_review,
    review_source_with_agent,
    suggest_code_fix_with_agent,
    suggest_repair_with_agent,
)
from stitch_cli.code_cli import run_analyze_code
from stitch_cli.executor import (
    build_skipped_result,
    execute_command,
)
from stitch_cli.reporter import (
    build_qa_decision,
    generate_report,
)
from stitch_cli.scanner import scan_project


console = Console()


def format_console_list(items):
    if not items:
        return "None"

    return ", ".join(
        str(item)
        for item in items
    )


def build_no_tests_skip_reason(
    static_map,
):
    framework = (
        static_map.get(
            "test_framework"
        )
        or "the detected test framework"
    )
    patterns = format_console_list(
        static_map.get(
            "test_file_patterns",
            [],
        )
    )

    return (
        f"No test files compatible with {framework} were detected using the active "
        f"discovery patterns: {patterns}."
    )


def print_source_review_result(
    source_review_data,
):
    console.print(
        "\n[bold magenta]"
        "Source Quality Intelligence Analyst"
        "[/bold magenta]"
    )
    console.print(
        f"[bold]Agent ID:[/bold] "
        f"{source_review_data.get('agent_id', 'source-quality-analyst')}"
    )
    console.print(
        f"[bold]Version:[/bold] "
        f"{source_review_data.get('agent_version', '3.0')}"
    )
    console.print(f"[bold]Status:[/bold] {source_review_data.get('status')}")
    console.print(f"[bold]Mode:[/bold] {source_review_data.get('mode')}")
    console.print(f"[bold]Model:[/bold] {source_review_data.get('model') or 'Not used'}")
    console.print(
        f"[bold]Confidence:[/bold] "
        f"{source_review_data.get('confidence', 'UNKNOWN')}"
    )
    console.print(
        f"[bold]Reviewed Files:[/bold] "
        f"{source_review_data.get('reviewed_files_count', 0)}"
    )
    console.print(
        f"[bold]Findings:[/bold] "
        f"{source_review_data.get('findings_count', 0)}"
    )
    console.print(
        f"[bold]Risk Level:[/bold] "
        f"{source_review_data.get('risk_level')}"
    )
    console.print(
        f"[bold]Release Recommendation:[/bold] "
        f"{source_review_data.get('release_recommendation')}"
    )
    console.print(f"[bold]Summary:[/bold] {source_review_data.get('summary')}")

    findings = source_review_data.get("findings", [])

    if findings:
        console.print("\n[bold cyan]Source Quality Findings[/bold cyan]")
        for finding in findings[:10]:
            location = finding.get("file_path") or "Project"
            if finding.get("line"):
                location = f"{location}:{finding.get('line')}"
            console.print(
                f"- [{finding.get('severity', 'UNKNOWN')}] "
                f"{finding.get('title', 'Source finding')} "
                f"({location})"
            )
        if len(findings) > 10:
            console.print(f"... and {len(findings) - 10} more findings")

    console.print(
        f"[bold]Current Knowledge Required:[/bold] "
        f"{source_review_data.get('current_knowledge_required', False)}"
    )
    if source_review_data.get("current_knowledge_reason"):
        console.print(
            f"[bold]Why:[/bold] "
            f"{source_review_data.get('current_knowledge_reason')}"
        )

    for warning in source_review_data.get("warnings", []):
        console.print(
            f"[bold yellow]Source Quality Warning:[/bold yellow] {warning}"
        )

    for limitation in source_review_data.get("limitations", []):
        console.print(
            f"[bold yellow]Source Quality Limitation:[/bold yellow] {limitation}"
        )


def print_log_agent_result(
    agent_data,
):
    console.print(
        "\n[bold magenta]"
        "Runtime Quality Intelligence Analyst"
        "[/bold magenta]"
    )
    console.print(
        f"[bold]Agent ID:[/bold] "
        f"{agent_data.get('agent_id')}"
    )
    console.print(
        f"[bold]Version:[/bold] "
        f"{agent_data.get('agent_version')}"
    )
    console.print(
        f"[bold]Mode:[/bold] "
        f"{agent_data.get('mode', 'unknown')}"
    )
    console.print(
        f"[bold]Model:[/bold] "
        f"{agent_data.get('model') or 'Not used'}"
    )
    console.print(
        f"[bold]Execution Status:[/bold] "
        f"{agent_data.get('execution_status')}"
    )
    console.print(
        f"[bold]Test Result:[/bold] "
        f"{agent_data.get('test_result')}"
    )
    console.print(
        f"[bold]Runtime Risk:[/bold] "
        f"{agent_data.get('runtime_risk_level', 'UNKNOWN')}"
    )
    console.print(
        f"[bold]Failure Origin:[/bold] "
        f"{agent_data.get('failure_origin', 'NOT_ESTABLISHED')}"
    )
    console.print(
        f"[bold]Release Gate:[/bold] "
        f"{agent_data.get('release_gate')}"
    )
    console.print(
        f"[bold]Diagnosis Confidence:[/bold] "
        f"{agent_data.get('diagnosis_confidence')}"
    )
    console.print(
        f"[bold]Evidence Quality:[/bold] "
        f"{agent_data.get('evidence_quality')}"
    )
    console.print(
        f"[bold]Summary:[/bold] "
        f"{agent_data.get('summary')}"
    )

    run_summary = (
        agent_data.get(
            "run_summary"
        )
        or {}
    )

    if run_summary:
        console.print(
            "\n[bold cyan]"
            "Validated Test Summary"
            "[/bold cyan]"
        )
        console.print(
            f"- Framework: "
            f"{run_summary.get('framework')}"
        )
        console.print(
            f"- Command: "
            f"{run_summary.get('command')}"
        )
        console.print(
            f"- Total: "
            f"{run_summary.get('total', 0)}"
        )
        console.print(
            f"- Passed: "
            f"{run_summary.get('passed', 0)}"
        )
        console.print(
            f"- Failed: "
            f"{run_summary.get('failed', 0)}"
        )
        console.print(
            f"- Errors: "
            f"{run_summary.get('errors', 0)}"
        )
        console.print(
            f"- Skipped: "
            f"{run_summary.get('skipped', 0)}"
        )
        console.print(
            f"- Exit Code: "
            f"{run_summary.get('exit_code')}"
        )
        console.print(
            f"- Duration: "
            f"{run_summary.get('duration_seconds')}"
        )
        console.print(
            f"- Report Source: "
            f"{run_summary.get('report_source')}"
        )

    groups = agent_data.get(
        "root_cause_groups",
        [],
    )

    if groups:
        console.print(
            "\n[bold cyan]"
            "Root Cause Groups"
            "[/bold cyan]"
        )

        for group in groups:
            console.print(
                f"\n[bold]"
                f"{group.get('group_id')} — "
                f"{group.get('title')}"
                f"[/bold]"
            )
            console.print(
                f"[bold]Category:[/bold] "
                f"{group.get('category')}"
            )
            console.print(
                f"[bold]Failure Origin:[/bold] "
                f"{group.get('failure_origin', 'NOT_ESTABLISHED')}"
            )
            console.print(
                f"[bold]Root Cause:[/bold] "
                f"{group.get('root_cause')}"
            )
            console.print(
                f"[bold]Runtime Impact:[/bold] "
                f"{group.get('runtime_impact')}"
            )
            console.print(
                f"[bold]Required Action:[/bold] "
                f"{group.get('required_action')}"
            )
            console.print(
                f"[bold]Affected Tests:[/bold] "
                f"{format_console_list(group.get('affected_tests', []))}"
            )

            for evidence in group.get(
                "evidence",
                [],
            )[:10]:
                application_location = (
                    evidence.get(
                        "application_file"
                    )
                )

                if (
                    application_location
                    and evidence.get(
                        "application_line"
                    )
                ):
                    application_location = (
                        f"{application_location}:"
                        f"{evidence.get('application_line')}"
                    )

                test_location = (
                    evidence.get(
                        "test_file"
                    )
                )

                if (
                    test_location
                    and evidence.get(
                        "test_line"
                    )
                ):
                    test_location = (
                        f"{test_location}:"
                        f"{evidence.get('test_line')}"
                    )

                console.print(
                    "- Evidence: "
                    f"Test={evidence.get('test_name') or 'Unknown'}, "
                    f"Expected={evidence.get('expected') or 'Not available'}, "
                    f"Actual={evidence.get('actual') or evidence.get('exception_type') or 'Not available'}, "
                    f"Exception={evidence.get('exception_type') or 'Not available'}, "
                    f"Message={evidence.get('exception_message') or 'Not available'}, "
                    f"Application={application_location or 'Not mapped'}, "
                    f"Test Location={test_location or 'Not mapped'}"
                )

    console.print(
        "\n[bold cyan]"
        "Required Actions"
        "[/bold cyan]"
    )

    for action in agent_data.get(
        "required_actions",
        [],
    ):
        console.print(
            f"- {action}"
        )

    if not agent_data.get(
        "required_actions"
    ):
        console.print(
            "- None"
        )

    console.print(
        "\n[bold cyan]"
        "Verification"
        "[/bold cyan]"
    )

    for step in agent_data.get(
        "verification_steps",
        [],
    ):
        console.print(
            f"- {step}"
        )

    if not agent_data.get(
        "verification_steps"
    ):
        console.print(
            "- None"
        )

    if agent_data.get(
        "warnings"
    ):
        console.print(
            "\n[bold yellow]"
            "Warnings"
            "[/bold yellow]"
        )

        for warning in agent_data.get(
            "warnings",
            [],
        ):
            console.print(
                f"- {warning}"
            )

    if agent_data.get(
        "limitations"
    ):
        console.print(
            "\n[bold yellow]"
            "Limitations"
            "[/bold yellow]"
        )

        for limitation in agent_data.get(
            "limitations",
            [],
        ):
            console.print(
                f"- {limitation}"
            )

    if agent_data.get(
        "llm_error"
    ):
        console.print(
            "\n[bold red]"
            "LLM Fallback Reason"
            "[/bold red]"
        )
        console.print(
            agent_data.get(
                "llm_error"
            )
        )


def print_repair_agent_result(repair_data):
    console.print(
        "\n[bold magenta]"
        "Defect Resolution Intelligence Analyst"
        "[/bold magenta]"
    )
    console.print(
        f"[bold]Agent ID:[/bold] "
        f"{repair_data.get('agent_id', 'defect-resolution-analyst')}"
    )
    console.print(
        f"[bold]Version:[/bold] "
        f"{repair_data.get('agent_version', '2.0')}"
    )
    console.print(
        f"[bold]Status:[/bold] "
        f"{repair_data.get('status')}"
    )
    console.print(
        f"[bold]Mode:[/bold] "
        f"{repair_data.get('mode')}"
    )
    console.print(
        f"[bold]Model:[/bold] "
        f"{repair_data.get('model') or 'Not used'}"
    )
    console.print(
        f"[bold]Overall Repair Priority:[/bold] "
        f"{repair_data.get('overall_priority', 'NONE')}"
    )
    console.print(
        f"[bold]Planning Confidence:[/bold] "
        f"{repair_data.get('confidence', 'LOW')}"
    )
    console.print(
        f"[bold]Repair Side-effect Risk:[/bold] "
        f"{repair_data.get('repair_risk_level', 'UNKNOWN')}"
    )
    console.print(
        f"[bold]Auto Apply:[/bold] "
        f"{repair_data.get('auto_apply', False)}"
    )
    console.print(
        f"[bold]Summary:[/bold] "
        f"{repair_data.get('summary')}"
    )

    contracts = repair_data.get("stitch_repair_contracts", [])
    if contracts:
        console.print(
            "\n[bold cyan]"
            "Stitch Repair Contracts"
            "[/bold cyan]"
        )

        for contract in contracts:
            console.print(
                f"\n[bold]{contract.get('contract_id')} — "
                f"{contract.get('title')}[/bold]"
            )
            console.print(
                f"[bold]Findings:[/bold] "
                f"{format_console_list(contract.get('finding_refs', []))}"
            )
            console.print(
                f"[bold]Priority:[/bold] {contract.get('priority')}"
            )
            console.print(
                f"[bold]Why Now:[/bold] {contract.get('priority_reason')}"
            )
            console.print(
                f"[bold]Repair Objective:[/bold] {contract.get('repair_objective')}"
            )
            console.print(
                f"[bold]Repair Strategy:[/bold] {contract.get('repair_strategy')}"
            )
            console.print(
                f"[bold]Change Boundary:[/bold] {contract.get('change_boundary')}"
            )
            console.print(
                f"[bold]Protect:[/bold] {contract.get('protected_behavior')}"
            )
            console.print(
                f"[bold]Side-effect Risk:[/bold] {contract.get('side_effect_risk')}"
            )
            console.print(
                f"[bold]Verification:[/bold] {contract.get('verification')}"
            )
            console.print(
                f"[bold]Done When:[/bold] {contract.get('done_condition')}"
            )
            console.print(
                f"[bold]Contract Status:[/bold] {contract.get('status')}"
            )

    console.print(
        f"\n[bold]Current Knowledge Required:[/bold] "
        f"{repair_data.get('current_knowledge_required', False)}"
    )
    if repair_data.get("current_knowledge_reason"):
        console.print(
            f"[bold]Why:[/bold] {repair_data.get('current_knowledge_reason')}"
        )

    console.print(
        f"[bold]Next Action:[/bold] "
        f"{repair_data.get('next_action')}"
    )

    for warning in repair_data.get("warnings", []):
        console.print(
            f"[bold yellow]Agent 2 Warning:[/bold yellow] {warning}"
        )

    for limitation in repair_data.get("limitations", []):
        console.print(
            f"[bold yellow]Agent 2 Limitation:[/bold yellow] {limitation}"
        )

    if repair_data.get("llm_error"):
        console.print(
            "\n[bold red]Agent 2 LLM Fallback Reason[/bold red]"
        )
        console.print(repair_data.get("llm_error"))


def print_code_agent_result(
    code_data,
):
    console.print(
        "\n[bold magenta]"
        "Repair Assurance Intelligence Analyst"
        "[/bold magenta]"
    )
    console.print(
        f"[bold]Agent ID:[/bold] "
        f"{code_data.get('agent_id', 'repair-assurance-analyst')}"
    )
    console.print(
        f"[bold]Version:[/bold] "
        f"{code_data.get('agent_version', '3.0')}"
    )
    console.print(f"[bold]Status:[/bold] {code_data.get('status')}")
    console.print(f"[bold]Mode:[/bold] {code_data.get('mode')}")
    console.print(f"[bold]Model:[/bold] {code_data.get('model') or 'Not used'}")
    console.print(
        f"[bold]Confidence:[/bold] "
        f"{code_data.get('confidence', 'UNKNOWN')}"
    )
    console.print(f"[bold]Risk Level:[/bold] {code_data.get('risk_level')}")
    console.print(f"[bold]Auto Apply:[/bold] {code_data.get('auto_apply')}")
    console.print(f"[bold]Summary:[/bold] {code_data.get('summary')}")

    guidance = code_data.get("guidance", [])
    if guidance:
        console.print("\n[bold cyan]Repair Assurance Guidance[/bold cyan]")
        for item in guidance:
            console.print(
                f"\n[bold]{item.get('guidance_id')} — "
                f"{item.get('repair_contract_ref')}[/bold]"
            )
            console.print(
                f"[bold]Findings:[/bold] "
                f"{format_console_list(item.get('finding_refs', []))}"
            )
            console.print(
                f"[bold]Target Files:[/bold] "
                f"{format_console_list(item.get('target_files', []))}"
            )
            console.print(
                f"[bold]Target Symbols:[/bold] "
                f"{format_console_list(item.get('target_symbols', []))}"
            )
            console.print(
                f"[bold]Implementation Intent:[/bold] "
                f"{item.get('implementation_intent')}"
            )
            console.print(
                f"[bold]Code-level Approach:[/bold] "
                f"{item.get('code_level_approach')}"
            )
            console.print(
                f"[bold]Change Boundary:[/bold] "
                f"{item.get('change_boundary')}"
            )
            console.print(
                f"[bold]Protect:[/bold] "
                f"{item.get('protected_behavior')}"
            )
            console.print(
                f"[bold]Side-effect Considerations:[/bold] "
                f"{item.get('side_effect_considerations')}"
            )
            console.print(
                f"[bold]Targeted Verification:[/bold] "
                f"{item.get('targeted_verification')}"
            )
            console.print(
                f"[bold]Regression Verification:[/bold] "
                f"{item.get('regression_verification')}"
            )
            console.print(
                f"[bold]Patch Validation:[/bold] "
                f"{item.get('patch_validation_status')}"
            )
            console.print(
                f"[bold]Guidance Status:[/bold] "
                f"{item.get('status')}"
            )

    console.print(
        f"[bold]Shadow Validation:[/bold] "
        f"{code_data.get('shadow_validation_status', 'NOT_RUN')}"
    )
    console.print(
        f"[bold]Current Knowledge Required:[/bold] "
        f"{code_data.get('current_knowledge_required', False)}"
    )
    if code_data.get("current_knowledge_reason"):
        console.print(
            f"[bold]Why:[/bold] {code_data.get('current_knowledge_reason')}"
        )
    console.print(
        f"[bold]Verification:[/bold] {code_data.get('verification')}"
    )

    if code_data.get("suggested_patch"):
        console.print("\n[bold cyan]Unvalidated Suggested Patch[/bold cyan]")
        console.print(code_data.get("suggested_patch"), markup=False)

    if code_data.get("llm_error"):
        console.print("\n[bold red]Repair Assurance LLM Fallback Reason[/bold red]")
        console.print(code_data.get("llm_error"))

    for warning in code_data.get("warnings", []):
        console.print(
            f"[bold yellow]Repair Assurance Warning:[/bold yellow] {warning}"
        )

    for limitation in code_data.get("limitations", []):
        console.print(
            f"[bold yellow]Repair Assurance Limitation:[/bold yellow] {limitation}"
        )


def print_qa_decision(
    qa_decision,
):
    console.print(
        "\n[bold green]"
        "Combined QA Decision"
        "[/bold green]"
    )
    console.print(
        f"[bold]Final QA Status:[/bold] "
        f"{qa_decision.get('status')}"
    )
    console.print(
        f"[bold]Combined Risk Level:[/bold] "
        f"{qa_decision.get('risk_level')}"
    )
    console.print(
        f"[bold]Release Recommendation:[/bold] "
        f"{qa_decision.get('release_recommendation')}"
    )
    console.print(
        f"[bold]QA Evidence Completeness:[/bold] "
        f"{qa_decision.get('completeness')}"
    )
    console.print(
        f"[bold]CI Exit Code:[/bold] "
        f"{qa_decision.get('ci_exit_code')}"
    )

    strands_decider = qa_decision.get("strands_decider")
    if strands_decider:
        console.print(
            "\n[bold magenta]"
            "Strands Decider 2B Release Gate"
            "[/bold magenta]"
        )
        console.print(
            f"- Verdict: [bold]{strands_decider.get('verdict')}[/bold]"
        )
        action = strands_decider.get("intervention_action")
        if action:
            action_color = "green" if action == "Proceed" else ("red" if action == "Deny" else "yellow")
            console.print(
                f"- Intervention Action: [bold {action_color}]{action}[/bold {action_color}]"
            )
        console.print(
            f"- Confidence: {strands_decider.get('confidence', 0.0):.2f}"
        )
        probs = strands_decider.get("probabilities")
        if probs:
            prob_str = ", ".join(f"{k}: {v:.1%}" for k, v in probs.items())
            console.print(f"- Choice Probabilities: {prob_str}")
        console.print(
            f"- Calibrated Risk: {strands_decider.get('risk_score', 0.0):.2f}"
        )
        console.print(
            f"- Decision Rationale: {strands_decider.get('rationale')}"
        )
        console.print(
            f"- Decision Model: {strands_decider.get('model')}"
        )
        if strands_decider.get("engine_mode"):
            console.print(
                f"- Execution Head: {strands_decider.get('engine_mode')}"
            )

    workflow_status = qa_decision.get(
        "workflow_status",
        {},
    )

    console.print(
        "\n[bold cyan]"
        "Agent Workflow Status"
        "[/bold cyan]"
    )
    console.print(
        f"- Agent 3 Source Review: "
        f"{workflow_status.get('source_review', 'NOT_RUN')}"
    )
    console.print(
        f"- Validated Test Execution: "
        f"{workflow_status.get('test_execution', 'NOT_RUN')}"
    )
    console.print(
        f"- Runtime Quality Intelligence: "
        f"{workflow_status.get('log_analysis', 'NOT_REQUESTED')}"
    )
    console.print(
        f"- Defect Resolution Intelligence Analyst: "
        f"{workflow_status.get('repair_guidance', 'NOT_REQUESTED')}"
    )
    console.print(
        f"- Agent 3 Code Repair Guidance: "
        f"{workflow_status.get('code_repair_guidance', 'NOT_REQUESTED')}"
    )

    console.print(
        "\n[bold cyan]"
        "Decision Reasons"
        "[/bold cyan]"
    )

    for reason in qa_decision.get(
        "reasons",
        [],
    ):
        console.print(
            f"- {reason}"
        )


@click.group()
def cli():
    pass


@cli.command(
    "analyze-code"
)
@click.option(
    "--code-agent-url",
    default=None,
    help="Optional custom endpoint URL for repair assurance analysis.",
)
def analyze_code(
    code_agent_url,
):
    run_analyze_code(
        code_agent_url
    )


@cli.command("check-bedrock")
def check_bedrock():
    """Verify live Amazon Bedrock and Strands Decider connectivity and model status."""
    from rich.panel import Panel
    from rich.table import Table
    from stitch_cli.bedrock_service import (
        bedrock_service,
        MODEL_DEFECT_RESOLUTION,
        MODEL_REPAIR_ASSURANCE,
        MODEL_RUNTIME_QUALITY,
        MODEL_SOURCE_QUALITY,
    )
    from stitch_cli.decider_agent import MODEL_STRANDS_DECIDER

    console.print(Panel.fit("[bold cyan]Stitch QA - Amazon Bedrock & Strands Decider Diagnostic[/bold cyan]"))
    res = bedrock_service.verify_connection()

    table = Table(title="Model Tiering & Service Health", show_header=True)
    table.add_column("Component", style="bold")
    table.add_column("Configured Model / Engine")
    table.add_column("Status", style="green")

    connected = res.get("connected", False)
    status_str = "[bold green]LIVE CONNECTED[/bold green]" if connected else "[bold yellow]OFFLINE DETERMINISTIC (READY)[/bold yellow]"

    table.add_row("AWS Region", res.get("region", "us-east-1"), "[cyan]Active[/cyan]")
    table.add_row("Amazon Bedrock API", "bedrock-runtime", status_str)
    table.add_row("Source Quality Analyst", MODEL_SOURCE_QUALITY, "[green]Ready[/green]")
    table.add_row("Runtime Quality Analyst", MODEL_RUNTIME_QUALITY, "[green]Ready[/green]")
    table.add_row("Defect Resolution Analyst", MODEL_DEFECT_RESOLUTION, "[green]Ready[/green]")
    table.add_row("Repair Assurance Analyst", MODEL_REPAIR_ASSURANCE, "[green]Ready[/green]")
    decider_endpoint = os.getenv("STRANDS_DECIDER_URL", "http://127.0.0.1:8000/v1/systemone")
    decider_live = False
    try:
        import requests
        check_url = decider_endpoint.replace("/v1/systemone", "/docs")
        r = requests.get(check_url, timeout=1.0)
        if r.status_code in {200, 404, 405}:
            decider_live = True
    except Exception:
        decider_live = False

    decider_status = "[bold green]LIVE SERVER CONNECTED[/bold green]" if decider_live else "[bold cyan]SYSTEM 1 ENGINE (DYNAMIC)[/bold cyan]"
    table.add_row("Strands Decider System 1", f"{MODEL_STRANDS_DECIDER} ({decider_endpoint})", decider_status)

    console.print(table)

    if connected:
        console.print(f"\n[green][OK] Successfully authenticated with live Amazon Bedrock (Latency: {res.get('latency_ms')}ms).[/green]")
    else:
        console.print("\n[yellow]Notice: Running in calibrated zero-dependency offline mode.[/yellow]")
        console.print("[dim]To enable live Amazon Bedrock calls, set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your .env or environment.[/dim]\n")


def _create_systemone_app(checkpoint: str):
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from stitch_cli.decider_agent import ChoiceQuestion, StrandsDeciderClient

    app = FastAPI(title="strands-decider System One", version="0.1.0")
    client = StrandsDeciderClient(model_name=checkpoint)

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "model": checkpoint,
            "engine": "Strands Decider 2B System 1 Engine",
        }

    @app.post("/v1/systemone")
    def systemone(req: dict):
        state = str(req.get("state", ""))
        questions = req.get("questions", {})
        answers = {}
        for q_id, q_data in questions.items():
            choice_q = ChoiceQuestion(
                instructions=q_data.get("instructions", ""),
                criteria=q_data.get("criteria", {}),
            )
            ans = client._evaluate_system_one(state, choice_q)
            answers[q_id] = {
                "type": "choice",
                "choice": ans.choice,
                "probabilities": ans.probabilities,
                "confidence": ans.confidence,
            }
        return JSONResponse(content={
            "model": checkpoint,
            "answers": answers,
            "usage": {"input_tokens": max(1, len(state.split())), "output_tokens": 1},
        })

    return app


@cli.command("decider-serve")
@click.option("--host", default="127.0.0.1", help="Host address to bind.")
@click.option("--port", default=8000, type=int, help="Port to bind.")
@click.option("--checkpoint", default="StrandsAgents/strands-decider-2B-hobson-v21", help="Checkpoint name or directory.")
def decider_serve(host, port, checkpoint):
    """Run Strands Decider System 1 HTTP server."""
    import uvicorn
    console.print(f"[bold cyan]Launching Strands Decider server on http://{host}:{port}/v1/systemone...[/bold cyan]")
    app = _create_systemone_app(checkpoint)
    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    except KeyboardInterrupt:
        console.print("\n[yellow]Strands Decider server stopped.[/yellow]")


def _run_profile_workflow(
    prof,
    scan_result,
    analyze,
    repair_requested,
    repair_assurance_requested,
    agent_url,
    repair_agent_url,
    code_agent_url,
):
    prof_type = prof["project_type"]
    prof_static = prof["static_map"]
    prof_source = prof["source_review"]

    prof_sub_result = dict(scan_result)
    prof_sub_result["project_type"] = prof_type
    prof_sub_result["static_map"] = prof_static
    prof_sub_result["source_review"] = prof_source
    prof_sub_result["project_recommendations"] = prof.get("project_recommendations", [])

    console.print(
        f"\n[bold magenta]Source Quality Intelligence Analyst Started ({prof_type})[/bold magenta]"
    )
    source_review_result = review_source_with_agent(code_agent_url, prof_sub_result)
    if source_review_result["success"]:
        source_review_data = source_review_result["data"]
    else:
        source_review_data = build_unavailable_source_review(
            prof_sub_result, source_review_result.get("error")
        )
    print_source_review_result(source_review_data)

    agent_data = None
    repair_data = None
    code_data = None

    static_map = prof_static
    if not static_map.get(
        "has_tests"
    ):
        skip_reason = build_no_tests_skip_reason(static_map)
        execution_result = build_skipped_result(
            prof_static.get("suggested_command"),
            skip_reason,
            prof_static.get("execution_profile"),
        )
        console.print(f"\n[bold yellow]Test Execution Skipped ({prof_type})[/bold yellow]")
        console.print(f"[bold]Status:[/bold] {execution_result['status']}")
        console.print(f"[bold]Command Profile:[/bold] {execution_result['command_profile']}")
        console.print(f"[bold]Execution Policy:[/bold] {execution_result['execution_policy']}")
        console.print(f"[bold]Execution Strategy:[/bold] {execution_result['execution_strategy']}")
        console.print(f"[bold]Shell Enabled:[/bold] {execution_result['shell_enabled']}")
        console.print(f"[bold]Command Not Run:[/bold] {execution_result['command']}")
        console.print(f"[bold]Reason:[/bold] {execution_result['skip_reason']}")
        console.print(f"[bold]Exit Code:[/bold] {execution_result['exit_code']}")

        if analyze:
            console.print(
                "\n[bold yellow]"
                "Runtime Quality Intelligence analysis was not run because no test "
                "command was executed. Source Quality Intelligence was completed "
                "independently."
                "[/bold yellow]"
            )

        if repair_requested:
            console.print(
                "\n[bold magenta]"
                "Defect Resolution Intelligence Analyst Started"
                "[/bold magenta]"
            )
            repair_result = suggest_repair_with_agent(
                repair_agent_url,
                prof_sub_result,
                execution_result,
                agent_data,
                source_review_data,
            )
            if repair_result["success"]:
                repair_data = repair_result["data"]
            else:
                repair_data = build_unavailable_repair_guidance(repair_result.get("error"))
            print_repair_agent_result(repair_data)

            if repair_assurance_requested:
                console.print(
                    "\n[bold magenta]"
                    "Repair Assurance Intelligence Analyst Started"
                    "[/bold magenta]"
                )
                code_result = suggest_code_fix_with_agent(
                    code_agent_url,
                    prof_sub_result,
                    execution_result,
                    agent_data,
                    repair_data,
                    source_review_data,
                )
                if code_result["success"]:
                    code_data = code_result["data"]
                else:
                    code_data = build_unavailable_code_guidance(code_result.get("error"))
                print_code_agent_result(code_data)
    else:
        console.print(
            "\n[bold magenta]"
            "Execution Started"
            "[/bold magenta]"
        )
        execution_result = execute_command(
            scan_result["project_path"],
            prof_static.get("execution_profile"),
            prof_static.get("suggested_command"),
        )
        console.print(f"[bold]Status:[/bold] {execution_result['status']}")
        console.print(f"[bold]Command Profile:[/bold] {execution_result['command_profile']}")
        console.print(f"[bold]Execution Policy:[/bold] {execution_result['execution_policy']}")
        console.print(f"[bold]Execution Strategy:[/bold] {execution_result['execution_strategy']}")
        console.print(f"[bold]Shell Enabled:[/bold] {execution_result['shell_enabled']}")
        console.print(f"[bold]Validation Status:[/bold] {execution_result['validation_status']}")
        console.print(f"[bold]Command:[/bold] {execution_result['command']}")
        console.print(f"[bold]Resolved Args:[/bold] {format_console_list(execution_result.get('command_args', []))}")
        console.print(f"[bold]Success:[/bold] {execution_result['success']}")
        console.print(f"[bold]Exit Code:[/bold] {execution_result['exit_code']}")

        runtime_evidence = execution_result.get("runtime_evidence") or {}
        test_summary = runtime_evidence.get("test_summary") or {}
        if runtime_evidence:
            console.print("\n[bold cyan]Runtime Evidence[/bold cyan]")
            console.print(f"[bold]Execution Status:[/bold] {runtime_evidence.get('execution_status')}")
            console.print(f"[bold]Test Result:[/bold] {runtime_evidence.get('test_result')}")
            console.print(f"[bold]Evidence Quality:[/bold] {runtime_evidence.get('evidence_quality')}")
            console.print(f"[bold]Report Source:[/bold] {runtime_evidence.get('report_source')}")
            console.print(
                f"[bold]Test Summary:[/bold] Total={test_summary.get('total', 0)}, "
                f"Passed={test_summary.get('passed', 0)}, "
                f"Failed={test_summary.get('failed', 0)}, "
                f"Errors={test_summary.get('errors', 0)}, "
                f"Skipped={test_summary.get('skipped', 0)}"
            )

        if execution_result.get("stdout"):
            console.print("\n[bold cyan]STDOUT[/bold cyan]")
            console.print(execution_result["stdout"][-3000:], markup=False)
        if execution_result.get("stderr"):
            console.print("\n[bold red]STDERR[/bold red]")
            console.print(execution_result["stderr"][-3000:], markup=False)

        if analyze and (
            execution_result["status"] == "FAILED"
            or runtime_evidence.get("test_result") == "FAIL"
            or execution_result.get("exit_code") not in (0, None)
        ):
            console.print(f"\n[bold magenta]Runtime Quality Intelligence Analyst Started ({prof_type})[/bold magenta]")
            analysis_result = analyze_logs_with_agent(agent_url, prof_sub_result, execution_result)
            agent_data = (
                analysis_result["data"]
                if analysis_result["success"]
                else build_unavailable_log_analysis(analysis_result.get("error"))
            )
            print_log_agent_result(agent_data)

            if repair_requested:
                console.print(f"\n[bold magenta]Defect Resolution Intelligence Analyst Started ({prof_type})[/bold magenta]")
                repair_result = suggest_repair_with_agent(
                    repair_agent_url, prof_sub_result, execution_result, agent_data, source_review_data
                )
                repair_data = (
                    repair_result["data"]
                    if repair_result["success"]
                    else build_unavailable_repair_guidance(repair_result.get("error"))
                )
                print_repair_agent_result(repair_data)

                if repair_assurance_requested:
                    console.print(f"\n[bold magenta]Repair Assurance Intelligence Analyst Started ({prof_type})[/bold magenta]")
                    code_result = suggest_code_fix_with_agent(
                        code_agent_url, prof_sub_result, execution_result, agent_data, repair_data, source_review_data
                    )
                    code_data = (
                        code_result["data"]
                        if code_result["success"]
                        else build_unavailable_code_guidance(code_result.get("error"))
                    )
                    print_code_agent_result(code_data)

    return {
        "profile": prof,
        "source_review_data": source_review_data,
        "execution_result": execution_result,
        "agent_data": agent_data,
        "repair_data": repair_data,
        "code_data": code_data,
    }


@cli.command()
@click.argument(
    "path",
    required=False,
    default=".",
)
@click.option(
    "--run",
    is_flag=True,
    help=(
        "Run the supported QA workflow."
    ),
)
@click.option(
    "--analyze",
    is_flag=True,
    help=(
        "Send execution logs to the log agent."
    ),
)
@click.option(
    "--repair",
    is_flag=True,
    help=(
        "Build prioritized evidence-linked repair guidance from available QA findings."
    ),
)
@click.option(
    "--code-fix",
    is_flag=True,
    help=(
        "Compatibility alias for Agent 2 plus Repair Assurance."
    ),
)
@click.option(
    "--agent-url",
    default=None,
    help="Optional custom endpoint URL for runtime log analysis.",
)
@click.option(
    "--repair-agent-url",
    default=None,
    help="Optional custom endpoint URL for defect resolution analysis.",
)
@click.option(
    "--code-agent-url",
    default=None,
    help="Optional custom endpoint URL for repair assurance analysis.",
)
def scan(
    path,
    run,
    analyze,
    repair,
    code_fix,
    agent_url,
    repair_agent_url,
    code_agent_url,
):
    repair_requested = bool(repair or code_fix)
    repair_assurance_requested = repair_requested

    try:
        result = scan_project(
            path
        )
    except Exception as error:
        console.print(
            f"[bold red]"
            f"Scan failed:"
            f"[/bold red] "
            f"{error}"
        )
        sys.exit(1)

    console.print(
        "\n[bold green]"
        "Stitch QA Scan Started"
        "[/bold green]"
    )
    console.print(
        f"[bold]Project Path:[/bold] "
        f"{result['project_path']}"
    )
    console.print(
        f"[bold]Detected Type:[/bold] "
        f"{result['project_type']}"
    )
    if result.get("is_polyglot"):
        console.print(
            f"[bold magenta]Polyglot Ecosystems:[/bold magenta] "
            f"{', '.join(result.get('detected_project_types', []))}"
        )
        if result.get("unsupported_scopes"):
            unsupported_names = ", ".join(s["project_type"] for s in result["unsupported_scopes"])
            console.print(
                f"[bold yellow]Unverified Ecosystems:[/bold yellow] "
                f"{unsupported_names} (Planned for future runtime execution)"
            )
    console.print(
        f"[bold]Total Files:[/bold] "
        f"{result['total_files']}"
    )
    console.print(
        f"[bold]Total Folders:[/bold] "
        f"{result['total_folders']}"
    )
    console.print(
        f"[bold]Ignored Items:[/bold] "
        f"{result['ignored_items']}"
    )

    console.print(
        "\n[bold cyan]"
        "File Extension Summary"
        "[/bold cyan]"
    )

    for extension, count in result[
        "extension_counts"
    ].items():
        console.print(
            f"- {extension}: {count}"
        )

    static_map = result[
        "static_map"
    ]
    source_review = result.get(
        "source_review",
        {},
    )

    console.print(
        "\n[bold cyan]"
        "Static Mapping"
        "[/bold cyan]"
    )
    console.print(
        f"[bold]Build File:[/bold] "
        f"{static_map.get('build_file')}"
    )
    console.print(
        f"[bold]Main Source Dir:[/bold] "
        f"{static_map.get('main_source_dir')}"
    )
    console.print(
        f"[bold]Test Source Dir:[/bold] "
        f"{static_map.get('test_source_dir')}"
    )
    console.print(
        f"[bold]Main File:[/bold] "
        f"{static_map.get('main_file')}"
    )
    console.print(
        f"[bold]Suggested Command:[/bold] "
        f"{static_map.get('suggested_command')}"
    )
    console.print(
        f"[bold]Execution Profile:[/bold] "
        f"{static_map.get('execution_profile')}"
    )
    console.print(
        f"[bold]Has Tests:[/bold] "
        f"{static_map.get('has_tests')}"
    )
    console.print(
        f"[bold]Test Files:[/bold] "
        f"{static_map.get('test_files_count', 0)}"
    )
    console.print(
        f"[bold]Test Framework:[/bold] "
        f"{static_map.get('test_framework')}"
    )

    console.print(
        "\n[bold cyan]"
        "Source Review Discovery"
        "[/bold cyan]"
    )
    console.print(
        f"[bold]Supported:[/bold] "
        f"{'Yes' if source_review.get('supported') else 'No'}"
    )
    console.print(
        f"[bold]Application Source Files:[/bold] "
        f"{source_review.get('source_files_count', 0)}"
    )
    console.print(
        f"[bold]Source Extensions:[/bold] "
        f"{format_console_list(source_review.get('file_extensions', []))}"
    )
    console.print(
        f"[bold]Excluded Test Files:[/bold] "
        f"{source_review.get('excluded_test_files_count', 0)}"
    )

    if source_review.get(
        "warning"
    ):
        console.print(
            f"[bold yellow]"
            f"Source Review Warning:"
            f"[/bold yellow] "
            f"{source_review.get('warning')}"
        )

    if result.get(
        "project_recommendations"
    ):
        console.print(
            "\n[bold yellow]"
            "Project Recommendations"
            "[/bold yellow]"
        )

        for recommendation in result[
            "project_recommendations"
        ]:
            console.print(
                f"- {recommendation}"
            )

    console.print(
        "\n[bold cyan]"
        "Detected Files"
        "[/bold cyan]"
    )

    for file in result[
        "files"
    ][:20]:
        console.print(
            f"- {file}"
        )

    if result[
        "total_files"
    ] > 20:
        console.print(
            f"... and "
            f"{result['total_files'] - 20} "
            f"more files"
        )

    if (
        analyze
        or repair_requested
    ) and not run:
        console.print(
            "\n[bold red]"
            "Analyze/repair requires --run."
            "[/bold red]"
        )
        console.print(
            "Use: stitch scan <path> "
            "--run --analyze --repair"
        )
        sys.exit(1)

    if code_fix and not repair:
        console.print(
            "\n[bold yellow]Compatibility Note:[/bold yellow] "
            "--code-fix now activates Agent 2 repair planning and "
            "Repair Assurance. Prefer --repair for the current workflow."
        )

    if not run:
        console.print(
            "\n[bold green]"
            "Stitch QA scan completed."
            "[/bold green] "
            "Use --run to start source review and supported test execution."
        )
        return

    supported_profiles = [p for p in result.get("profiles", []) if p.get("is_supported")]

    if not supported_profiles:
        console.print(
            f"\n[bold yellow]"
            f"Project Type: "
            f"{result['project_type']}"
            f"[/bold yellow]"
        )
        console.print(
            "[bold yellow]"
            "Skipping execution. This project type is not yet supported in this version."
            "[/bold yellow]"
        )
        console.print(
            f"[bold yellow]"
            f"{static_map.get('coming_soon_message', '')}"
            f"[/bold yellow]"
        )
        console.print(
            "[bold yellow]"
            "Supported: Java Maven (pom.xml), Python "
            "(requirements.txt / pyproject.toml)"
            "[/bold yellow]"
        )
        console.print(
            "[bold green]"
            "Exiting cleanly with exit code 0."
            "[/bold green]"
        )

        generate_report(
            result,
            None,
            None,
            None,
            None,
            None,
        )
        sys.exit(0)

    is_polyglot_run = len(supported_profiles) > 1

    if is_polyglot_run:
        console.print(
            f"\n[bold magenta]=== Polyglot Multi-Ecosystem Orchestration ({len(supported_profiles)} ecosystems) ===[/bold magenta]"
        )

    profile_evaluations = []
    for idx, prof in enumerate(supported_profiles, start=1):
        if is_polyglot_run:
            console.print(f"\n[bold cyan]--- [Ecosystem {idx}/{len(supported_profiles)}] {prof['project_type']} ---[/bold cyan]")
        eval_res = _run_profile_workflow(
            prof,
            result,
            analyze,
            repair_requested,
            repair_assurance_requested,
            agent_url,
            repair_agent_url,
            code_agent_url,
        )
        profile_evaluations.append(eval_res)

    defect_evals = [
        e for e in profile_evaluations
        if (e["execution_result"].get("runtime_evidence") or {}).get("test_result") == "FAIL"
        or (e["agent_data"] and e["agent_data"].get("failure_origin") == "APPLICATION_DEFECT" and (e["execution_result"].get("runtime_evidence") or {}).get("test_result") != "NOT_RUN")
    ]
    startup_evals = [
        e for e in profile_evaluations
        if e["execution_result"].get("status") == "FAILED"
    ]
    primary_eval = (defect_evals[0] if defect_evals else None) or (startup_evals[0] if startup_evals else None) or profile_evaluations[0]

    execution_result = primary_eval["execution_result"]
    source_review_data = primary_eval["source_review_data"]
    agent_data = primary_eval["agent_data"]
    repair_data = primary_eval["repair_data"]
    code_data = primary_eval["code_data"]

    all_findings = []
    for e in profile_evaluations:
        s_data = e.get("source_review_data")
        if isinstance(s_data, dict):
            all_findings.extend(s_data.get("findings") or [])
    if all_findings and isinstance(source_review_data, dict):
        source_review_data = dict(source_review_data)
        source_review_data["findings"] = all_findings

    all_repair_contracts = []
    for e in profile_evaluations:
        r_data = e.get("repair_data")
        if isinstance(r_data, dict):
            all_repair_contracts.extend(r_data.get("stitch_repair_contracts") or [])
    if all_repair_contracts:
        if not isinstance(repair_data, dict):
            repair_data = {"stitch_repair_contracts": all_repair_contracts}
        else:
            repair_data = dict(repair_data)
            repair_data["stitch_repair_contracts"] = all_repair_contracts

    all_patches = []
    for e in profile_evaluations:
        c_data = e.get("code_data")
        if isinstance(c_data, dict):
            all_patches.extend(c_data.get("patches") or [])
    if all_patches:
        if not isinstance(code_data, dict):
            code_data = {"patches": all_patches}
        else:
            code_data = dict(code_data)
            code_data["patches"] = all_patches

    failing_component_names = [e["profile"]["project_type"] for e in (defect_evals or startup_evals)]
    component_label = ", ".join(dict.fromkeys(failing_component_names)) if failing_component_names else (primary_eval["profile"]["project_type"] if is_polyglot_run else None)

    workflow_context = {
        "analyze_requested": bool(analyze),
        "repair_requested": bool(repair_requested),
        "repair_assurance_requested": bool(repair_assurance_requested),
        "code_fix_requested": bool(repair_assurance_requested),
        "unsupported_scopes": result.get("unsupported_scopes"),
        "component_name": component_label,
        "is_polyglot": is_polyglot_run,
        "polyglot_evaluations": profile_evaluations,
    }

    qa_decision = build_qa_decision(
        execution_result,
        source_review_data,
        agent_data,
        repair_data,
        code_data,
        workflow_context,
    )

    print_qa_decision(
        qa_decision
    )

    report_path = generate_report(
        result,
        execution_result,
        agent_data,
        repair_data,
        code_data,
        source_review_data,
        qa_decision,
        workflow_context,
    )

    markdown_report_path = Path(
        report_path
    )
    json_report_path = (
        markdown_report_path.with_suffix(
            ".json"
        )
    )

    console.print(
        f"\n[bold green]"
        f"Markdown report generated:"
        f"[/bold green] "
        f"{markdown_report_path}"
    )
    console.print(
        f"[bold green]"
        f"JSON report generated:"
        f"[/bold green] "
        f"{json_report_path}"
    )
    console.print(
        "\n[bold green]"
        "Stitch QA scan completed."
        "[/bold green] "
        "Review the generated reports for details."
    )
    if os.getenv("GITHUB_STEP_SUMMARY"):
        console.print(
            "[bold green]"
            "GitHub Actions step summary updated."
            "[/bold green]"
        )

    if qa_decision.get(
        "ci_exit_code"
    ):
        sys.exit(
            int(
                qa_decision[
                    "ci_exit_code"
                ]
            )
        )


if __name__ == "__main__":
    cli()




