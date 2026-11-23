"""
underwriting_agent.py — Agent 4: Underwriting Preparation (Stage 3).

Responsibility: Combine the structured findings produced by the three
specialist agents into a single, readable underwriting preparation report.
This agent does NOT perform any financial calculations — it aggregates and
formats existing findings only.

IMPORTANT: This report is prepared for human review. It must never be used
to automatically approve or reject a credit application. All lending decisions
must be made by a qualified human underwriter.
"""

from typing import Any

from app.agents.cash_flow_agent import CashFlowFindings
from app.agents.financial_risk_agent import RiskFindings
from app.agents.document_agent import DocumentFindings

# Type alias for the structured output returned by this agent.
UnderwritingReport = dict[str, Any]


def _validate_cash_flow_findings(cash_flow_findings: CashFlowFindings) -> None:
    required = {"agent", "status", "liquidity_metrics", "findings",
                "supporting_evidence", "unresolved_questions"}
    missing = required - set(cash_flow_findings.keys())
    if missing:
        raise ValueError(
            f"cash_flow_findings is missing required keys: {sorted(missing)}"
        )


def _validate_risk_findings(risk_findings: RiskFindings) -> None:
    required = {"agent", "status", "warning_signs", "positive_indicators",
                "supporting_evidence", "unresolved_questions"}
    missing = required - set(risk_findings.keys())
    if missing:
        raise ValueError(
            f"risk_findings is missing required keys: {sorted(missing)}"
        )


def _validate_document_findings(document_findings: DocumentFindings) -> None:
    required = {"agent", "status", "is_complete", "received_documents",
                "missing_documents", "findings", "unresolved_questions"}
    missing = required - set(document_findings.keys())
    if missing:
        raise ValueError(
            f"document_findings is missing required keys: {sorted(missing)}"
        )


def _validate_business_data(business_data: dict) -> None:
    if "business_name" not in business_data:
        raise ValueError("business_data must contain 'business_name'.")


def run_underwriting_preparation_agent(
    business_data: dict,
    cash_flow_findings: CashFlowFindings,
    risk_findings: RiskFindings,
    document_findings: DocumentFindings,
) -> UnderwritingReport:
    """
    Combine specialist agent findings into a structured underwriting preparation report.

    Parameters
    ----------
    business_data : dict
        Structured financial data matching the sample_business.json schema.
    cash_flow_findings : CashFlowFindings
        Output from run_cash_flow_agent().
    risk_findings : RiskFindings
        Output from run_financial_risk_agent().
    document_findings : DocumentFindings
        Output from run_document_agent().

    Returns
    -------
    UnderwritingReport
        A structured dictionary containing:
        - business_overview: name and data snapshot
        - liquidity_analysis: summary of cash flow findings and metrics
        - financial_indicators: warning signs and positive indicators
        - document_completeness: document status summary
        - all_unresolved_questions: aggregated questions from all agents
        - supporting_evidence: key numbers drawn from agent findings
        - human_review_requirement: mandatory advisory statement
        - source_findings: the original agent outputs, preserved in full

    Raises
    ------
    ValueError
        If any required keys are missing from the input findings.
    """
    _validate_business_data(business_data)
    _validate_cash_flow_findings(cash_flow_findings)
    _validate_risk_findings(risk_findings)
    _validate_document_findings(document_findings)

    metrics = cash_flow_findings["liquidity_metrics"]

    # --- Business overview --------------------------------------------------
    business_overview = {
        "business_name": business_data.get("business_name", "Unknown"),
        "credit_limit": business_data.get("credit_line", {}).get("limit"),
        "credit_used": business_data.get("credit_line", {}).get("currently_used"),
        "bank_balance": business_data.get("bank_balance"),
    }

    # --- Liquidity analysis summary -----------------------------------------
    # Carry forward calculated metrics and cash flow agent findings verbatim.
    # We do not restate or recalculate them.
    liquidity_analysis = {
        "summary": cash_flow_findings["findings"],
        "metrics": {
            "available_credit": metrics.get("available_credit"),
            "credit_utilization_pct": metrics.get("credit_utilization_pct"),
            "upcoming_obligations": metrics.get("upcoming_obligations"),
            "immediate_funding_gap": metrics.get("immediate_funding_gap"),
            "immediate_liquidity": metrics.get("immediate_liquidity"),
            "remaining_funding_gap": metrics.get("remaining_funding_gap"),
            "incoming_receivables": metrics.get("incoming_receivables"),
            "receivables_in_days": metrics.get("receivables_in_days"),
        },
    }

    # --- Financial indicators -----------------------------------------------
    financial_indicators = {
        "warning_signs": risk_findings["warning_signs"],
        "positive_indicators": risk_findings["positive_indicators"],
    }

    # --- Document completeness ----------------------------------------------
    document_completeness = {
        "is_complete": document_findings["is_complete"],
        "received_documents": document_findings["received_documents"],
        "missing_documents": document_findings["missing_documents"],
        "summary": document_findings["findings"],
    }

    # --- Aggregate all unresolved questions from every agent ----------------
    # Questions are labelled with their source agent for traceability.
    all_unresolved_questions: list[dict[str, str]] = []
    for question in cash_flow_findings["unresolved_questions"]:
        all_unresolved_questions.append(
            {"source": cash_flow_findings["agent"], "question": question}
        )
    for question in risk_findings["unresolved_questions"]:
        all_unresolved_questions.append(
            {"source": risk_findings["agent"], "question": question}
        )
    for question in document_findings["unresolved_questions"]:
        all_unresolved_questions.append(
            {"source": document_findings["agent"], "question": question}
        )

    # --- Merge supporting evidence from all agents --------------------------
    supporting_evidence: dict[str, Any] = {}
    supporting_evidence.update(cash_flow_findings.get("supporting_evidence", {}))
    supporting_evidence.update(risk_findings.get("supporting_evidence", {}))

    return {
        "agent": "Underwriting Preparation Agent",
        "status": "completed",
        "business_overview": business_overview,
        "liquidity_analysis": liquidity_analysis,
        "financial_indicators": financial_indicators,
        "document_completeness": document_completeness,
        "all_unresolved_questions": all_unresolved_questions,
        "supporting_evidence": supporting_evidence,
        # The original agent outputs are preserved so the full audit trail
        # is available to the human underwriter.
        "source_findings": {
            "cash_flow": cash_flow_findings,
            "risk": risk_findings,
            "documents": document_findings,
        },
        # This statement must always be present and must never be removed.
        "human_review_requirement": (
            "THIS REPORT IS PREPARED FOR HUMAN REVIEW ONLY. "
            "It must not be used to automatically approve or reject any credit "
            "application. All lending decisions must be made by a qualified "
            "human underwriter. This system uses fictional financial data."
        ),
    }
