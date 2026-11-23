"""
supervisor_agent.py — Supervisor Agent: Workflow Coordinator (Stage 4).

Responsibility: Orchestrate the three specialist agents in the correct
dependency order, pass their outputs to the Underwriting Preparation Agent,
and return a complete workflow result with metadata.

This module contains NO financial logic. It delegates every domain concern
to the appropriate specialist agent and surfaces errors with clear attribution.

IMPORTANT: The completed report is prepared for human review only.
It must never be used to automatically approve or reject credit.
"""

from typing import Any

from app.agents.cash_flow_agent import run_cash_flow_agent
from app.agents.financial_risk_agent import run_financial_risk_agent
from app.agents.document_agent import run_document_agent
from app.agents.underwriting_agent import run_underwriting_preparation_agent

# Type alias for the structured result returned by this supervisor.
SupervisorResult = dict[str, Any]

# Canonical names used in workflow metadata — must match agent "agent" fields.
_AGENT_NAMES = [
    "Cash Flow Agent",
    "Financial Risk Agent",
    "Document Agent",
    "Underwriting Preparation Agent",
]


def _validate_inputs(business_data: Any, document_data: Any) -> None:
    """
    Raise ValueError early if either top-level input is not a non-empty dict.

    We validate structure before touching any agent so that the error message
    identifies the bad input, not a confusing downstream KeyError.
    """
    if not isinstance(business_data, dict) or not business_data:
        raise ValueError(
            "business_data must be a non-empty dictionary. "
            "Provide structured financial data matching the sample_business.json schema."
        )
    if not isinstance(document_data, dict) or not document_data:
        raise ValueError(
            "document_data must be a non-empty dictionary. "
            "Provide structured document status data matching the sample_documents.json schema."
        )


def run_supervisor_review(
    business_data: dict,
    document_data: dict,
) -> SupervisorResult:
    """
    Coordinate the full credit review workflow across all specialist agents.

    Execution order
    ---------------
    1. Cash Flow Agent     — calculates liquidity metrics from business_data.
    2. Financial Risk Agent — interprets metrics; must receive Cash Flow output.
    3. Document Agent      — checks document completeness from document_data.
    4. Underwriting Agent  — combines all three specialist outputs into a report.

    Parameters
    ----------
    business_data : dict
        Structured financial data matching the sample_business.json schema.
    document_data : dict
        Structured document status data matching the sample_documents.json schema.

    Returns
    -------
    SupervisorResult
        A structured dictionary containing:
        - workflow_status: "completed" or "failed"
        - business_name: extracted from business_data
        - agents_executed: list of agent names that were called
        - agent_statuses: dict mapping each agent name to its status
        - final_report: the full UnderwritingReport (or None on failure)
        - human_review_requirement: mandatory advisory statement (always present)
        - error: error message string (only present when workflow_status is "failed")

    Raises
    ------
    ValueError
        If business_data or document_data are missing or structurally invalid
        before any agent is called.
    """
    _validate_inputs(business_data, document_data)

    business_name: str = business_data.get("business_name", "Unknown")
    agents_executed: list[str] = []
    agent_statuses: dict[str, str] = {}

    # --- Step 1: Cash Flow Agent --------------------------------------------
    # Must run first; its liquidity_metrics output is required by the Risk Agent.
    try:
        cash_flow_findings = run_cash_flow_agent(business_data)
        agents_executed.append(cash_flow_findings["agent"])
        agent_statuses[cash_flow_findings["agent"]] = cash_flow_findings["status"]
    except Exception as exc:
        return _failed_result(
            business_name=business_name,
            agents_executed=agents_executed,
            agent_statuses=agent_statuses,
            failed_agent="Cash Flow Agent",
            error=exc,
        )

    # --- Step 2: Financial Risk Agent ---------------------------------------
    # Receives business_data AND the liquidity_metrics produced by Step 1.
    try:
        risk_findings = run_financial_risk_agent(
            business_data,
            cash_flow_findings["liquidity_metrics"],
        )
        agents_executed.append(risk_findings["agent"])
        agent_statuses[risk_findings["agent"]] = risk_findings["status"]
    except Exception as exc:
        return _failed_result(
            business_name=business_name,
            agents_executed=agents_executed,
            agent_statuses=agent_statuses,
            failed_agent="Financial Risk Agent",
            error=exc,
        )

    # --- Step 3: Document Agent ---------------------------------------------
    # Independent of the financial agents; uses document_data only.
    try:
        document_findings = run_document_agent(document_data)
        agents_executed.append(document_findings["agent"])
        agent_statuses[document_findings["agent"]] = document_findings["status"]
    except Exception as exc:
        return _failed_result(
            business_name=business_name,
            agents_executed=agents_executed,
            agent_statuses=agent_statuses,
            failed_agent="Document Agent",
            error=exc,
        )

    # --- Step 4: Underwriting Preparation Agent -----------------------------
    # Receives business_data and all three specialist findings.
    try:
        final_report = run_underwriting_preparation_agent(
            business_data,
            cash_flow_findings,
            risk_findings,
            document_findings,
        )
        agents_executed.append(final_report["agent"])
        agent_statuses[final_report["agent"]] = final_report["status"]
    except Exception as exc:
        return _failed_result(
            business_name=business_name,
            agents_executed=agents_executed,
            agent_statuses=agent_statuses,
            failed_agent="Underwriting Preparation Agent",
            error=exc,
        )

    return {
        "workflow_status": "completed",
        "business_name": business_name,
        "agents_executed": agents_executed,
        "agent_statuses": agent_statuses,
        "final_report": final_report,
        # Always carry the human-review requirement at the top level so it is
        # visible even before the caller inspects the full report.
        "human_review_requirement": final_report["human_review_requirement"],
    }


# ---------------------------------------------------------------------------
# Internal helper — build a consistent failure result.
# ---------------------------------------------------------------------------

def _failed_result(
    *,
    business_name: str,
    agents_executed: list[str],
    agent_statuses: dict[str, str],
    failed_agent: str,
    error: Exception,
) -> SupervisorResult:
    """
    Return a workflow result that clearly surfaces which agent failed and why.

    We never produce a "completed" status when an agent raised an exception —
    an incomplete report must not be presented as a finished review.
    """
    agent_statuses[failed_agent] = "failed"
    return {
        "workflow_status": "failed",
        "business_name": business_name,
        "agents_executed": agents_executed,
        "agent_statuses": agent_statuses,
        "final_report": None,
        "failed_agent": failed_agent,
        # Include the error type and message for debugging.
        # Do not include a stack trace here; logs should capture that separately.
        "error": f"{type(error).__name__}: {error}",
        # The advisory statement is always present, even on failure.
        "human_review_requirement": (
            "THIS REPORT IS PREPARED FOR HUMAN REVIEW ONLY. "
            "It must not be used to automatically approve or reject any credit "
            "application. All lending decisions must be made by a qualified "
            "human underwriter. This system uses fictional financial data."
        ),
    }
