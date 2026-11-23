"""
test_financial_calculations.py — pytest suite for the financial calculation engine.

Covers:
  1. Sample business scenario (Greenfield Supplies) with exact expected values.
  2. Zero credit utilization.
  3. Fully utilized credit line.
  4. Exceeded credit line (over-limit).
  5. No upcoming payment obligations.
  6. Invalid negative financial values.
  7. Zero credit line limit.
"""

import pytest
from decimal import Decimal

from app.services.financial_calculations import calculate_liquidity_metrics


# ---------------------------------------------------------------------------
# Helper — call the function with the Greenfield Supplies sample data.
# ---------------------------------------------------------------------------
def _greenfield() -> dict:
    return calculate_liquidity_metrics(
        credit_limit=75_000,
        credit_used=68_000,
        bank_balance=19_000,
        payroll=34_000,
        vendor_payments=22_000,
        incoming_receivables=62_000,
        receivables_in_days=30,
    )


# ---------------------------------------------------------------------------
# 1. Sample business scenario — Greenfield Supplies
# ---------------------------------------------------------------------------
class TestGreenfieldSample:
    def test_available_credit(self):
        assert _greenfield()["available_credit"] == Decimal("7000")

    def test_credit_utilization(self):
        # 68000 / 75000 * 100 = 90.666... → rounds to 90.67
        assert _greenfield()["credit_utilization_pct"] == Decimal("90.67")

    def test_upcoming_obligations(self):
        # 34000 payroll + 22000 vendors = 56000
        assert _greenfield()["upcoming_obligations"] == Decimal("56000")

    def test_immediate_funding_gap(self):
        # 56000 obligations − 19000 bank balance = 37000
        assert _greenfield()["immediate_funding_gap"] == Decimal("37000")

    def test_immediate_liquidity(self):
        # 19000 bank balance + 7000 available credit = 26000
        assert _greenfield()["immediate_liquidity"] == Decimal("26000")

    def test_remaining_funding_gap(self):
        # 56000 obligations − 26000 immediate liquidity = 30000
        assert _greenfield()["remaining_funding_gap"] == Decimal("30000")

    def test_receivables_are_informational(self):
        """Receivables must NOT be included in any liquidity calculation."""
        result = _greenfield()
        assert result["incoming_receivables"] == Decimal("62000")
        assert result["receivables_in_days"] == 30
        # Confirm receivables did not leak into immediate_liquidity
        assert result["immediate_liquidity"] == Decimal("26000")

    def test_no_over_limit(self):
        assert _greenfield()["credit_over_limit_amount"] == Decimal("0")


# ---------------------------------------------------------------------------
# 2. Zero credit utilization
# ---------------------------------------------------------------------------
class TestZeroCreditUtilization:
    def setup_method(self):
        self.result = calculate_liquidity_metrics(
            credit_limit=50_000,
            credit_used=0,
            bank_balance=10_000,
            payroll=5_000,
            vendor_payments=3_000,
            incoming_receivables=0,
            receivables_in_days=0,
        )

    def test_available_credit_equals_limit(self):
        assert self.result["available_credit"] == Decimal("50000")

    def test_utilization_is_zero(self):
        assert self.result["credit_utilization_pct"] == Decimal("0.00")

    def test_no_over_limit(self):
        assert self.result["credit_over_limit_amount"] == Decimal("0")

    def test_immediate_liquidity(self):
        # 10000 + 50000 = 60000
        assert self.result["immediate_liquidity"] == Decimal("60000")

    def test_no_remaining_gap(self):
        # obligations (8000) < liquidity (60000)
        assert self.result["remaining_funding_gap"] == Decimal("0")


# ---------------------------------------------------------------------------
# 3. Fully utilized credit line (used == limit)
# ---------------------------------------------------------------------------
class TestFullyUtilizedCreditLine:
    def setup_method(self):
        self.result = calculate_liquidity_metrics(
            credit_limit=40_000,
            credit_used=40_000,
            bank_balance=5_000,
            payroll=10_000,
            vendor_payments=0,
            incoming_receivables=0,
            receivables_in_days=0,
        )

    def test_available_credit_is_zero(self):
        assert self.result["available_credit"] == Decimal("0")

    def test_utilization_is_100(self):
        assert self.result["credit_utilization_pct"] == Decimal("100.00")

    def test_no_over_limit(self):
        assert self.result["credit_over_limit_amount"] == Decimal("0")

    def test_immediate_liquidity_equals_bank_balance(self):
        # No available credit → liquidity = bank balance only
        assert self.result["immediate_liquidity"] == Decimal("5000")

    def test_remaining_gap(self):
        # obligations (10000) − liquidity (5000) = 5000
        assert self.result["remaining_funding_gap"] == Decimal("5000")


# ---------------------------------------------------------------------------
# 4. Exceeded credit line (used > limit)
# ---------------------------------------------------------------------------
class TestExceededCreditLine:
    def setup_method(self):
        self.result = calculate_liquidity_metrics(
            credit_limit=30_000,
            credit_used=35_000,  # 5000 over limit
            bank_balance=8_000,
            payroll=12_000,
            vendor_payments=4_000,
            incoming_receivables=0,
            receivables_in_days=0,
        )

    def test_available_credit_clamped_to_zero(self):
        # Must never be negative
        assert self.result["available_credit"] == Decimal("0")

    def test_utilization_exceeds_100(self):
        # 35000 / 30000 * 100 = 116.67 %
        assert self.result["credit_utilization_pct"] == Decimal("116.67")

    def test_over_limit_amount(self):
        assert self.result["credit_over_limit_amount"] == Decimal("5000")

    def test_immediate_liquidity_equals_bank_balance(self):
        assert self.result["immediate_liquidity"] == Decimal("8000")

    def test_remaining_gap(self):
        # obligations (16000) − liquidity (8000) = 8000
        assert self.result["remaining_funding_gap"] == Decimal("8000")


# ---------------------------------------------------------------------------
# 5. No upcoming payment obligations
# ---------------------------------------------------------------------------
class TestNoUpcomingObligations:
    def setup_method(self):
        self.result = calculate_liquidity_metrics(
            credit_limit=20_000,
            credit_used=5_000,
            bank_balance=15_000,
            payroll=0,
            vendor_payments=0,
            incoming_receivables=10_000,
            receivables_in_days=15,
        )

    def test_upcoming_obligations_is_zero(self):
        assert self.result["upcoming_obligations"] == Decimal("0")

    def test_no_funding_gaps(self):
        assert self.result["immediate_funding_gap"] == Decimal("0")
        assert self.result["remaining_funding_gap"] == Decimal("0")

    def test_immediate_liquidity(self):
        # 15000 + 15000 available = 30000
        assert self.result["immediate_liquidity"] == Decimal("30000")


# ---------------------------------------------------------------------------
# 6. Invalid negative financial values
# ---------------------------------------------------------------------------
class TestNegativeValueValidation:
    @pytest.mark.parametrize(
        "field,kwargs",
        [
            (
                "credit_limit",
                dict(
                    credit_limit=-1,
                    credit_used=0,
                    bank_balance=0,
                    payroll=0,
                    vendor_payments=0,
                    incoming_receivables=0,
                    receivables_in_days=0,
                ),
            ),
            (
                "credit_used",
                dict(
                    credit_limit=10_000,
                    credit_used=-500,
                    bank_balance=0,
                    payroll=0,
                    vendor_payments=0,
                    incoming_receivables=0,
                    receivables_in_days=0,
                ),
            ),
            (
                "bank_balance",
                dict(
                    credit_limit=10_000,
                    credit_used=0,
                    bank_balance=-100,
                    payroll=0,
                    vendor_payments=0,
                    incoming_receivables=0,
                    receivables_in_days=0,
                ),
            ),
            (
                "payroll",
                dict(
                    credit_limit=10_000,
                    credit_used=0,
                    bank_balance=1_000,
                    payroll=-200,
                    vendor_payments=0,
                    incoming_receivables=0,
                    receivables_in_days=0,
                ),
            ),
            (
                "vendor_payments",
                dict(
                    credit_limit=10_000,
                    credit_used=0,
                    bank_balance=1_000,
                    payroll=0,
                    vendor_payments=-50,
                    incoming_receivables=0,
                    receivables_in_days=0,
                ),
            ),
            (
                "incoming_receivables",
                dict(
                    credit_limit=10_000,
                    credit_used=0,
                    bank_balance=1_000,
                    payroll=0,
                    vendor_payments=0,
                    incoming_receivables=-300,
                    receivables_in_days=0,
                ),
            ),
        ],
    )
    def test_negative_raises_value_error(self, field: str, kwargs: dict):
        with pytest.raises(ValueError, match=field):
            calculate_liquidity_metrics(**kwargs)


# ---------------------------------------------------------------------------
# 7. Zero credit line limit
# ---------------------------------------------------------------------------
class TestZeroCreditLimit:
    def test_zero_limit_raises_value_error(self):
        with pytest.raises(ValueError, match="credit_limit"):
            calculate_liquidity_metrics(
                credit_limit=0,
                credit_used=0,
                bank_balance=5_000,
                payroll=1_000,
                vendor_payments=500,
                incoming_receivables=0,
                receivables_in_days=0,
            )
