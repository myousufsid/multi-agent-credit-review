"""
financial_risk_agent.py — Agent 2: Financial Risk Analysis (Stage 3).

Responsibility: Examine existing liquidity metrics and business data for
warning signs and positive indicators. This agent does NOT perform raw
financial calculations — it interprets the structured output produced by
the Cash Flow Agent and the shared calculation engine.

This agent never calculates a credit score or makes lending decisions.
All findings are advisory and require qualified human review.
"""

from decimal import Decimal
from typing import Any

from app.services.financial_calculations import LiquidityMetrics

# Type alias for the structured output returned by this agent.
RiskFindings = dict[str, Any]

# ---------------------------------------------------------------------------
# Configurable thresholds — illustrative values for this prototype only.
# These are NOT underwriting policy and must not be used to approve or reject
# credit applications.
# ---------------------------------------------------------------------------
ELEVATED_UTILIZATION_THRESHOLD_PCT = Decimal("80.00")


def _validate_inputs(business_data: dict, liquidity_metrics: LiquidityMetrics) -> None:
    """
    Raise ValueError if required keys are absent from either input.
    """
    required_business = {"credit_line", "receivables"}
    missing_business = required_business - set(business_data.keys())
    if missing_business:
        raise ValueError(
            f"business_data is missing required sections: {sorted(missing_business)}"
        )

    required_metrics = {
        "credit_utilization_pct",
        "credit_over_limit_amount",
        "remaining_funding_gap",
        "available_credit",
        "incoming_receivables",
        "receivables_in_days",
        "upcoming_obligations",
        "immediate_liquidity",
    }
    missing_metrics = required_metrics - set(liquidity_metrics.keys())
    if missing_metrics:
        raise ValueError(
            f"liquidity_metrics is missing required keys: {sorted(missing_metrics)}"
        )


def run_financial_risk_agent(
    business_data: dict,
    liquidity_metrics: LiquidityMetrics,
) -> RiskFindings:
    """
    Identify financial warning signs and positive indicators from existing metrics.

    Parameters
    ----------
    business_data : dict
        Structured financial data matching the sample_business.json schema.
    liquidity_metrics : LiquidityMetrics
        Pre-calculated metrics produced by calculate_liquidity_metrics().

    Returns
    -------
    RiskFindings
        A structured dictionary containing:
        - agent metadata (name, status)
        - warning_signs: list of identified concerns
        - positive_indicators: list of favourable observations
        - supporting_evidence: key numbers referenced in findings
        - unresolved_questions: items requiring further investigation

    Raises
    ------
    ValueError
        If required keys are missing from either input.
    """
    _validate_inputs(business_data, liquidity_metrics)

    warning_signs: list[str] = []
    positive_indicators: list[str] = []
    supporting_evidence: dict[str, Any] = {}
    unresolved_questions: list[str] = []

    utilization = liquidity_metrics["credit_utilization_pct"]
    over_limit = liquidity_metrics["credit_over_limit_amount"]
    remaining_gap = liquidity_metrics["remaining_funding_gap"]
    receivables = liquidity_metrics["incoming_receivables"]
    receivables_days = liquidity_metrics["receivables_in_days"]

    # --- Warning: Elevated credit utilization --------------------------------
    # We flag this as a potential concern for the underwriter's attention.
    # The threshold is illustrative; actual policy thresholds must be set by
    # qualified underwriting staff.
    supporting_evidence["credit_utilization_pct"] = utilization
    supporting_evidence["elevated_utilization_threshold_pct"] = (
        ELEVATED_UTILIZATION_THRESHOLD_PCT
    )

    if utilization >= ELEVATED_UTILIZATION_THRESHOLD_PCT:
        warning_signs.append(
            f"Credit utilization is {utilization}%, which meets or exceeds the "
            f"illustrative elevated threshold of {ELEVATED_UTILIZATION_THRESHOLD_PCT}%. "
            "High utilization reduces the cushion available for unexpected expenses."
        )
        unresolved_questions.append(
            f"What is driving the high credit utilization of {utilization}%? "
            "Is this a temporary peak or an ongoing pattern?"
        )
    else:
        positive_indicators.append(
            f"Credit utilization of {utilization}% is below the "
            f"illustrative elevated threshold of {ELEVATED_UTILIZATION_THRESHOLD_PCT}%."
        )

    # --- Warning: Credit line exceeded ---------------------------------------
    if over_limit > Decimal("0"):
        warning_signs.append(
            f"The credit line has been exceeded by ${over_limit:,}. "
            "This requires immediate attention and explanation."
        )
        supporting_evidence["credit_over_limit_amount"] = over_limit
        unresolved_questions.append(
            f"How did the credit line become over-limit by ${over_limit:,}, "
            "and what is the plan to bring it back within limits?"
        )

    # --- Warning: Remaining funding gap after credit -------------------------
    if remaining_gap > Decimal("0"):
        warning_signs.append(
            f"A remaining funding gap of ${remaining_gap:,} persists even after "
            "accounting for available credit. The business may not be able to "
            "meet near-term obligations without additional funds."
        )
        supporting_evidence["remaining_funding_gap"] = remaining_gap
        unresolved_questions.append(
            f"How does the business intend to cover the ${remaining_gap:,} "
            "remaining funding gap?"
        )
    else:
        positive_indicators.append(
            "No remaining funding gap: available liquidity covers upcoming obligations."
        )

    # --- Positive indicator: Incoming receivables ----------------------------
    # Receivables are a potentially positive sign but are not guaranteed.
    if receivables > Decimal("0"):
        positive_indicators.append(
            f"The business has ${receivables:,} in incoming receivables expected "
            f"in {receivables_days} days. If collected in full and on time, "
            "these could significantly improve the liquidity position."
        )
        supporting_evidence["incoming_receivables"] = receivables
        supporting_evidence["receivables_in_days"] = receivables_days
        unresolved_questions.append(
            f"What is the creditworthiness and payment history of the customers "
            f"behind the ${receivables:,} in expected receivables? "
            "Are any receivables at risk of being late or uncollected?"
        )

    # --- Positive indicator: Immediate liquidity coverage ratio --------------
    obligations = liquidity_metrics["upcoming_obligations"]
    immediate_liquidity = liquidity_metrics["immediate_liquidity"]
    supporting_evidence["upcoming_obligations"] = obligations
    supporting_evidence["immediate_liquidity"] = immediate_liquidity

    if immediate_liquidity >= obligations:
        positive_indicators.append(
            f"Combined immediate liquidity (${immediate_liquidity:,}) covers "
            f"upcoming obligations (${obligations:,})."
        )

    return {
        "agent": "Financial Risk Agent",
        "status": "completed",
        "warning_signs": warning_signs,
        "positive_indicators": positive_indicators,
        "supporting_evidence": supporting_evidence,
        "unresolved_questions": unresolved_questions,
    }
