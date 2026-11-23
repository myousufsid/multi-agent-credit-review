"""
financial_calculations.py — Pure financial calculation engine (Stage 2).

This module provides deterministic, Decimal-precision calculations used to
prepare liquidity indicators for human underwriter review.

IMPORTANT: These calculations identify financial indicators only.
They must never be used to automatically approve or reject credit.
All outputs are advisory and require qualified human review.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


# ---------------------------------------------------------------------------
# Public type alias — the dict shape returned by calculate_liquidity_metrics.
# ---------------------------------------------------------------------------
LiquidityMetrics = dict[str, Any]


def _to_decimal(value: Any, field_name: str) -> Decimal:
    """
    Convert a numeric value to Decimal and enforce non-negative constraint.

    We reject negative amounts early so that every downstream calculation
    operates on mathematically valid inputs.
    """
    try:
        d = Decimal(str(value))
    except Exception as exc:
        raise ValueError(
            f"Field '{field_name}' could not be converted to Decimal: {exc}"
        ) from exc

    if d < Decimal("0"):
        raise ValueError(
            f"Field '{field_name}' must be non-negative; got {value}."
        )
    return d


def calculate_liquidity_metrics(
    credit_limit: Any,
    credit_used: Any,
    bank_balance: Any,
    payroll: Any,
    vendor_payments: Any,
    incoming_receivables: Any,
    receivables_in_days: int,
) -> LiquidityMetrics:
    """
    Calculate key short-term liquidity indicators for a business credit review.

    Parameters
    ----------
    credit_limit : numeric
        Total approved credit line (must be > 0).
    credit_used : numeric
        Amount of the credit line currently drawn.
    bank_balance : numeric
        Current bank account balance.
    payroll : numeric
        Upcoming payroll obligation (due before receivables arrive).
    vendor_payments : numeric
        Upcoming vendor payment obligation (due before receivables arrive).
    incoming_receivables : numeric
        Expected inbound payments (informational — not counted as cash on hand).
    receivables_in_days : int
        How many days until the receivables are expected to arrive.

    Returns
    -------
    LiquidityMetrics
        A dictionary of calculated metrics with Decimal monetary values and a
        Decimal percentage.  Receivables are carried as informational fields.

    Raises
    ------
    ValueError
        If any monetary amount is negative, or if credit_limit is zero.
    """

    # --- Input validation ---------------------------------------------------

    limit = _to_decimal(credit_limit, "credit_limit")
    used = _to_decimal(credit_used, "credit_used")
    balance = _to_decimal(bank_balance, "bank_balance")
    pay = _to_decimal(payroll, "payroll")
    vendors = _to_decimal(vendor_payments, "vendor_payments")
    receivables = _to_decimal(incoming_receivables, "incoming_receivables")

    if limit == Decimal("0"):
        raise ValueError("credit_limit must be greater than zero.")

    # --- Core calculations --------------------------------------------------

    # 1. Available credit — clamped to zero when credit is over-limit.
    #    A negative value here would be misleading; we surface the over-limit
    #    amount separately.
    available_credit = max(limit - used, Decimal("0"))

    # 2. Credit utilisation as a percentage.
    #    Can legitimately exceed 100 % when the line has been over-drawn.
    credit_utilization_pct = (used / limit * Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # 3. Amount by which the credit line has been exceeded (zero when within
    #    limits).  Useful for the underwriter to flag immediately.
    credit_over_limit = max(used - limit, Decimal("0"))

    # 4. Total cash obligations the business must cover in the near term.
    upcoming_obligations = pay + vendors

    # 5. Gap between obligations and current bank balance alone.
    #    Zero when the bank balance already covers everything.
    immediate_funding_gap = max(upcoming_obligations - balance, Decimal("0"))

    # 6. Combined liquid resources available right now: cash + unused credit.
    #    Receivables are intentionally excluded; they are not yet in hand.
    immediate_liquidity = balance + available_credit

    # 7. Gap that remains after exhausting both cash and available credit.
    #    Zero when total liquidity covers all obligations.
    remaining_funding_gap = max(
        upcoming_obligations - immediate_liquidity, Decimal("0")
    )

    # --- Result dictionary --------------------------------------------------
    return {
        # Calculated monetary metrics
        "available_credit": available_credit,
        "credit_utilization_pct": credit_utilization_pct,
        "credit_over_limit_amount": credit_over_limit,
        "upcoming_obligations": upcoming_obligations,
        "immediate_funding_gap": immediate_funding_gap,
        "immediate_liquidity": immediate_liquidity,
        "remaining_funding_gap": remaining_funding_gap,
        # Informational — receivables are future cash, not available today.
        "incoming_receivables": receivables,
        "receivables_in_days": receivables_in_days,
    }
