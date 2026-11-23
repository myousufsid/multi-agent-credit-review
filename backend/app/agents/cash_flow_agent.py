"""
cash_flow_agent.py — Agent 1: Cash Flow Analysis (Stage 3).

Responsibility: Extract financial figures from business data, delegate all
arithmetic to the shared calculation engine, and return structured short-term
liquidity findings for human underwriter review.

This agent never makes lending decisions. Its output is advisory only.
"""

from decimal import Decimal
from typing import Any

from app.services.financial_calculations import (
    calculate_liquidity_metrics,
    LiquidityMetrics,
)

# Type alias for the structured output returned by this agent.
CashFlowFindings = dict[str, Any]

# ---------------------------------------------------------------------------
# Required top-level keys in the business_data dictionary.
# These match the structure of sample_business.json exactly.
# ---------------------------------------------------------------------------
_REQUIRED_KEYS = {"credit_line", "bank_balance", "upcoming_obligations", "receivables"}


def _validate_business_data(business_data: dict) -> None:
    """
    Raise ValueError if any required section is absent from business_data.

    We check structure here so that downstream code can safely use dict access
    without further guard clauses.
    """
    missing = _REQUIRED_KEYS - set(business_data.keys())
    if missing:
        raise ValueError(
            f"business_data is missing required sections: {sorted(missing)}"
        )

    credit_line = business_data["credit_line"]
    if "limit" not in credit_line or "currently_used" not in credit_line:
        raise ValueError(
            "business_data['credit_line'] must contain 'limit' and 'currently_used'."
        )

    obligations = business_data["upcoming_obligations"]
    if "payroll" not in obligations or "vendor_payments" not in obligations:
        raise ValueError(
            "business_data['upcoming_obligations'] must contain "
            "'payroll' and 'vendor_payments'."
        )

    receivables = business_data["receivables"]
    if "incoming_amount" not in receivables or "expected_in_days" not in receivables:
        raise ValueError(
            "business_data['receivables'] must contain "
            "'incoming_amount' and 'expected_in_days'."
        )


def run_cash_flow_agent(business_data: dict) -> CashFlowFindings:
    """
    Analyse the short-term cash flow position of a business.

    Parameters
    ----------
    business_data : dict
        Structured financial data matching the sample_business.json schema.

    Returns
    -------
    CashFlowFindings
        A structured dictionary containing:
        - agent metadata (name, status)
        - liquidity_metrics: full output from calculate_liquidity_metrics()
        - findings: plain-language observations for the underwriter
        - supporting_evidence: key numbers that back each finding
        - unresolved_questions: items requiring further investigation

    Raises
    ------
    ValueError
        If business_data is missing required sections or contains invalid values.
    """
    _validate_business_data(business_data)

    # --- Delegate all arithmetic to the shared calculation engine -----------
    # We read directly from the nested JSON structure so there is no field
    # mapping duplication between this agent and the calculation engine.
    metrics: LiquidityMetrics = calculate_liquidity_metrics(
        credit_limit=business_data["credit_line"]["limit"],
        credit_used=business_data["credit_line"]["currently_used"],
        bank_balance=business_data["bank_balance"],
        payroll=business_data["upcoming_obligations"]["payroll"],
        vendor_payments=business_data["upcoming_obligations"]["vendor_payments"],
        incoming_receivables=business_data["receivables"]["incoming_amount"],
        receivables_in_days=business_data["receivables"]["expected_in_days"],
    )

    # --- Build findings based on the calculated metrics ---------------------
    findings: list[str] = []
    supporting_evidence: dict[str, Any] = {}
    unresolved_questions: list[str] = []

    # Finding 1: Short-term obligations vs. bank balance
    findings.append(
        f"Upcoming payment obligations total "
        f"${metrics['upcoming_obligations']:,} "
        f"(payroll ${business_data['upcoming_obligations']['payroll']:,} + "
        f"vendor payments ${business_data['upcoming_obligations']['vendor_payments']:,})."
    )
    supporting_evidence["upcoming_obligations"] = metrics["upcoming_obligations"]
    supporting_evidence["bank_balance"] = Decimal(str(business_data["bank_balance"]))

    # Finding 2: Immediate funding gap
    if metrics["immediate_funding_gap"] > Decimal("0"):
        findings.append(
            f"The current bank balance of ${business_data['bank_balance']:,} "
            f"does not cover upcoming obligations. "
            f"An immediate funding gap of ${metrics['immediate_funding_gap']:,} exists."
        )
        supporting_evidence["immediate_funding_gap"] = metrics["immediate_funding_gap"]
        unresolved_questions.append(
            "How does the business plan to cover the immediate funding gap "
            f"of ${metrics['immediate_funding_gap']:,} before obligations fall due?"
        )
    else:
        findings.append(
            "The current bank balance is sufficient to cover upcoming obligations."
        )

    # Finding 3: Remaining gap after drawing available credit
    if metrics["remaining_funding_gap"] > Decimal("0"):
        findings.append(
            f"Even after utilising available credit "
            f"(${metrics['available_credit']:,}), a remaining funding gap "
            f"of ${metrics['remaining_funding_gap']:,} persists."
        )
        supporting_evidence["available_credit"] = metrics["available_credit"]
        supporting_evidence["remaining_funding_gap"] = metrics["remaining_funding_gap"]
        unresolved_questions.append(
            "What additional funding sources does the business have to close "
            f"the remaining gap of ${metrics['remaining_funding_gap']:,}?"
        )
    else:
        findings.append(
            "Available credit is sufficient to cover any funding gap if drawn."
        )

    # Finding 4: Receivables — informational, not counted as available cash
    findings.append(
        f"Incoming receivables of ${metrics['incoming_receivables']:,} are "
        f"expected in {metrics['receivables_in_days']} days. "
        "These are future funds and have NOT been counted as immediately "
        "available cash in this analysis."
    )
    supporting_evidence["incoming_receivables"] = metrics["incoming_receivables"]
    supporting_evidence["receivables_in_days"] = metrics["receivables_in_days"]
    unresolved_questions.append(
        f"Are the ${metrics['incoming_receivables']:,} in expected receivables "
        "confirmed and reliable? Late or partial collection could affect the "
        "business's ability to recover its liquidity position."
    )

    return {
        "agent": "Cash Flow Agent",
        "status": "completed",
        "liquidity_metrics": metrics,
        "findings": findings,
        "supporting_evidence": supporting_evidence,
        "unresolved_questions": unresolved_questions,
    }
