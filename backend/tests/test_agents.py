"""
test_agents.py — pytest suite for the four Stage 3 specialist agents.

Covers:
  1.  Cash flow agent produces correct liquidity metrics for Greenfield Supplies.
  2.  Cash flow agent identifies the short-term funding gap.
  3.  Risk agent identifies elevated credit utilization.
  4.  Risk agent identifies a remaining funding gap.
  5.  Risk agent identifies positive indicators when appropriate.
  6.  Document agent correctly identifies missing documents.
  7.  Underwriting agent includes findings from all three specialist agents.
  8.  Underwriting agent preserves numerical evidence and human-review requirement.
  9.  Invalid / incomplete input is handled appropriately.
"""

import pytest
from decimal import Decimal

from app.agents.cash_flow_agent import run_cash_flow_agent
from app.agents.financial_risk_agent import run_financial_risk_agent
from app.agents.document_agent import run_document_agent
from app.agents.underwriting_agent import run_underwriting_preparation_agent


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

GREENFIELD_BUSINESS = {
    "business_name": "Greenfield Supplies",
    "credit_line": {"limit": 75_000, "currently_used": 68_000},
    "bank_balance": 19_000,
    "upcoming_obligations": {"payroll": 34_000, "vendor_payments": 22_000},
    "receivables": {"incoming_amount": 62_000, "expected_in_days": 30},
}

GREENFIELD_DOCUMENTS = {
    "business_name": "Greenfield Supplies",
    "required_documents": [
        {"name": "Recent Bank Statements", "key": "bank_statements", "status": "received"},
        {"name": "Business Tax Return", "key": "tax_return", "status": "received"},
        {"name": "Profit and Loss Statement", "key": "profit_loss_statement", "status": "missing"},
        {"name": "Balance Sheet", "key": "balance_sheet", "status": "received"},
    ],
}


@pytest.fixture
def cash_flow_result():
    return run_cash_flow_agent(GREENFIELD_BUSINESS)


@pytest.fixture
def risk_result(cash_flow_result):
    return run_financial_risk_agent(
        GREENFIELD_BUSINESS,
        cash_flow_result["liquidity_metrics"],
    )


@pytest.fixture
def document_result():
    return run_document_agent(GREENFIELD_DOCUMENTS)


@pytest.fixture
def underwriting_result(cash_flow_result, risk_result, document_result):
    return run_underwriting_preparation_agent(
        GREENFIELD_BUSINESS,
        cash_flow_result,
        risk_result,
        document_result,
    )


# ---------------------------------------------------------------------------
# 1 & 2. Cash Flow Agent — Greenfield Supplies
# ---------------------------------------------------------------------------
class TestCashFlowAgent:
    def test_agent_name_and_status(self, cash_flow_result):
        assert cash_flow_result["agent"] == "Cash Flow Agent"
        assert cash_flow_result["status"] == "completed"

    def test_liquidity_metrics_present(self, cash_flow_result):
        """The result must contain the full metrics dictionary."""
        assert "liquidity_metrics" in cash_flow_result

    def test_available_credit(self, cash_flow_result):
        assert cash_flow_result["liquidity_metrics"]["available_credit"] == Decimal("7000")

    def test_credit_utilization(self, cash_flow_result):
        assert cash_flow_result["liquidity_metrics"]["credit_utilization_pct"] == Decimal("90.67")

    def test_upcoming_obligations(self, cash_flow_result):
        assert cash_flow_result["liquidity_metrics"]["upcoming_obligations"] == Decimal("56000")

    def test_immediate_liquidity(self, cash_flow_result):
        assert cash_flow_result["liquidity_metrics"]["immediate_liquidity"] == Decimal("26000")

    def test_identifies_immediate_funding_gap(self, cash_flow_result):
        """Agent must flag the $37,000 immediate funding gap."""
        metrics = cash_flow_result["liquidity_metrics"]
        assert metrics["immediate_funding_gap"] == Decimal("37000")

    def test_identifies_remaining_funding_gap(self, cash_flow_result):
        """Agent must flag the $30,000 remaining gap."""
        metrics = cash_flow_result["liquidity_metrics"]
        assert metrics["remaining_funding_gap"] == Decimal("30000")

    def test_funding_gap_mentioned_in_findings(self, cash_flow_result):
        """At least one finding must mention the funding gap."""
        findings_text = " ".join(cash_flow_result["findings"])
        assert "gap" in findings_text.lower()

    def test_receivables_noted_as_future_funds(self, cash_flow_result):
        """Findings must explicitly state receivables are NOT immediately available."""
        findings_text = " ".join(cash_flow_result["findings"])
        assert "not" in findings_text.lower()
        assert "62000" in findings_text or "62,000" in findings_text

    def test_unresolved_questions_exist(self, cash_flow_result):
        assert len(cash_flow_result["unresolved_questions"]) > 0

    def test_supporting_evidence_has_bank_balance(self, cash_flow_result):
        assert "bank_balance" in cash_flow_result["supporting_evidence"]


# ---------------------------------------------------------------------------
# 3 & 4 & 5. Financial Risk Agent
# ---------------------------------------------------------------------------
class TestFinancialRiskAgent:
    def test_agent_name_and_status(self, risk_result):
        assert risk_result["agent"] == "Financial Risk Agent"
        assert risk_result["status"] == "completed"

    def test_identifies_elevated_utilization(self, risk_result):
        """90.67% utilization must appear as a warning sign."""
        warnings_text = " ".join(risk_result["warning_signs"])
        assert "90.67" in warnings_text

    def test_warning_signs_list_non_empty(self, risk_result):
        assert len(risk_result["warning_signs"]) > 0

    def test_identifies_remaining_funding_gap_warning(self, risk_result):
        """A remaining gap of $30,000 must trigger a warning."""
        warnings_text = " ".join(risk_result["warning_signs"])
        assert "30000" in warnings_text or "30,000" in warnings_text

    def test_positive_indicators_non_empty_for_greenfield(self, risk_result):
        """Greenfield has incoming receivables — this should produce at least one positive indicator."""
        assert len(risk_result["positive_indicators"]) > 0

    def test_receivables_as_positive_indicator(self, risk_result):
        """Incoming receivables should be listed as a potentially positive indicator."""
        positives_text = " ".join(risk_result["positive_indicators"])
        assert "receivable" in positives_text.lower()

    def test_unresolved_questions_exist(self, risk_result):
        assert len(risk_result["unresolved_questions"]) > 0

    def test_supporting_evidence_has_utilization(self, risk_result):
        assert "credit_utilization_pct" in risk_result["supporting_evidence"]

    def test_no_credit_score_produced(self, risk_result):
        """Risk agent must not produce a credit score or eligibility decision."""
        assert "credit_score" not in risk_result
        assert "approved" not in risk_result
        assert "rejected" not in risk_result

    def test_zero_utilization_no_warning(self):
        """Below-threshold utilization must NOT trigger the elevated utilization warning."""
        from app.services.financial_calculations import calculate_liquidity_metrics

        low_metrics = calculate_liquidity_metrics(
            credit_limit=50_000,
            credit_used=10_000,   # 20% — well below 80% threshold
            bank_balance=30_000,
            payroll=5_000,
            vendor_payments=3_000,
            incoming_receivables=0,
            receivables_in_days=0,
        )
        result = run_financial_risk_agent(
            {
                "credit_line": {"limit": 50_000, "currently_used": 10_000},
                "receivables": {"incoming_amount": 0, "expected_in_days": 0},
            },
            low_metrics,
        )
        warnings_text = " ".join(result["warning_signs"])
        assert "20.00" not in warnings_text
        # 20% is below threshold so no utilization warning
        assert not any("utilization" in w.lower() for w in result["warning_signs"])

    def test_no_gap_produces_positive_indicator(self):
        """When obligations are fully covered, a positive indicator should appear."""
        from app.services.financial_calculations import calculate_liquidity_metrics

        covered_metrics = calculate_liquidity_metrics(
            credit_limit=100_000,
            credit_used=20_000,
            bank_balance=80_000,
            payroll=10_000,
            vendor_payments=5_000,
            incoming_receivables=0,
            receivables_in_days=0,
        )
        result = run_financial_risk_agent(
            {
                "credit_line": {"limit": 100_000, "currently_used": 20_000},
                "receivables": {"incoming_amount": 0, "expected_in_days": 0},
            },
            covered_metrics,
        )
        positives_text = " ".join(result["positive_indicators"])
        assert "gap" in positives_text.lower() or "covers" in positives_text.lower()


# ---------------------------------------------------------------------------
# 6. Document Agent
# ---------------------------------------------------------------------------
class TestDocumentAgent:
    def test_agent_name_and_status(self, document_result):
        assert document_result["agent"] == "Document Agent"
        assert document_result["status"] == "completed"

    def test_identifies_missing_document(self, document_result):
        assert "Profit and Loss Statement" in document_result["missing_documents"]

    def test_identifies_received_documents(self, document_result):
        received = document_result["received_documents"]
        assert "Recent Bank Statements" in received
        assert "Business Tax Return" in received
        assert "Balance Sheet" in received

    def test_is_not_complete(self, document_result):
        """One document is missing, so is_complete must be False."""
        assert document_result["is_complete"] is False

    def test_complete_set_is_flagged_complete(self):
        """When all documents are received, is_complete must be True."""
        all_received = {
            "required_documents": [
                {"name": "Bank Statements", "key": "bank_statements", "status": "received"},
                {"name": "Tax Return", "key": "tax_return", "status": "received"},
            ]
        }
        result = run_document_agent(all_received)
        assert result["is_complete"] is True
        assert result["missing_documents"] == []

    def test_findings_mention_missing_document(self, document_result):
        findings_text = " ".join(document_result["findings"])
        assert "Profit and Loss Statement" in findings_text

    def test_unresolved_question_for_each_missing(self, document_result):
        """There should be one unresolved question per missing document."""
        assert len(document_result["unresolved_questions"]) == len(
            document_result["missing_documents"]
        )


# ---------------------------------------------------------------------------
# 7 & 8. Underwriting Preparation Agent
# ---------------------------------------------------------------------------
class TestUnderwritingAgent:
    def test_agent_name_and_status(self, underwriting_result):
        assert underwriting_result["agent"] == "Underwriting Preparation Agent"
        assert underwriting_result["status"] == "completed"

    def test_includes_cash_flow_findings(self, underwriting_result):
        """Source findings must preserve the original cash flow output."""
        assert "cash_flow" in underwriting_result["source_findings"]
        assert underwriting_result["source_findings"]["cash_flow"]["agent"] == "Cash Flow Agent"

    def test_includes_risk_findings(self, underwriting_result):
        assert "risk" in underwriting_result["source_findings"]
        assert underwriting_result["source_findings"]["risk"]["agent"] == "Financial Risk Agent"

    def test_includes_document_findings(self, underwriting_result):
        assert "documents" in underwriting_result["source_findings"]
        assert underwriting_result["source_findings"]["documents"]["agent"] == "Document Agent"

    def test_business_name_in_overview(self, underwriting_result):
        assert underwriting_result["business_overview"]["business_name"] == "Greenfield Supplies"

    def test_liquidity_metrics_carried_through(self, underwriting_result):
        metrics = underwriting_result["liquidity_analysis"]["metrics"]
        assert metrics["available_credit"] == Decimal("7000")
        assert metrics["remaining_funding_gap"] == Decimal("30000")
        assert metrics["credit_utilization_pct"] == Decimal("90.67")

    def test_warning_signs_carried_through(self, underwriting_result):
        warnings = underwriting_result["financial_indicators"]["warning_signs"]
        assert len(warnings) > 0

    def test_document_completeness_carried_through(self, underwriting_result):
        doc = underwriting_result["document_completeness"]
        assert doc["is_complete"] is False
        assert "Profit and Loss Statement" in doc["missing_documents"]

    def test_all_unresolved_questions_aggregated(self, underwriting_result):
        """Questions from all three agents must be present and labelled."""
        questions = underwriting_result["all_unresolved_questions"]
        assert len(questions) > 0
        # Every entry must carry a source label
        for q in questions:
            assert "source" in q
            assert "question" in q

    def test_human_review_requirement_present(self, underwriting_result):
        """The mandatory advisory statement must always be present."""
        requirement = underwriting_result["human_review_requirement"]
        assert isinstance(requirement, str)
        assert len(requirement) > 0
        assert "human" in requirement.lower() or "review" in requirement.lower()

    def test_supporting_evidence_has_numerical_values(self, underwriting_result):
        evidence = underwriting_result["supporting_evidence"]
        assert len(evidence) > 0
        # At least credit utilization must be present
        assert "credit_utilization_pct" in evidence

    def test_no_approval_or_rejection(self, underwriting_result):
        """Report must not contain any autonomous credit decision language."""
        report_str = str(underwriting_result).lower()
        assert "approved" not in report_str
        assert "rejected" not in report_str
        assert "credit score" not in report_str


# ---------------------------------------------------------------------------
# 9. Invalid / incomplete input handling
# ---------------------------------------------------------------------------
class TestInvalidInputHandling:
    def test_cash_flow_agent_missing_credit_line(self):
        bad_data = {
            "business_name": "X",
            # credit_line key intentionally omitted
            "bank_balance": 1000,
            "upcoming_obligations": {"payroll": 500, "vendor_payments": 200},
            "receivables": {"incoming_amount": 0, "expected_in_days": 0},
        }
        with pytest.raises(ValueError, match="credit_line"):
            run_cash_flow_agent(bad_data)

    def test_cash_flow_agent_missing_receivables(self):
        bad_data = {
            "business_name": "X",
            "credit_line": {"limit": 10_000, "currently_used": 1_000},
            "bank_balance": 5_000,
            "upcoming_obligations": {"payroll": 500, "vendor_payments": 200},
            # receivables key intentionally omitted
        }
        with pytest.raises(ValueError, match="receivables"):
            run_cash_flow_agent(bad_data)

    def test_risk_agent_missing_metrics_key(self):
        incomplete_metrics = {"credit_utilization_pct": Decimal("50.00")}
        with pytest.raises(ValueError, match="missing required keys"):
            run_financial_risk_agent(
                {"credit_line": {}, "receivables": {}},
                incomplete_metrics,
            )

    def test_document_agent_missing_required_documents_key(self):
        with pytest.raises(ValueError, match="required_documents"):
            run_document_agent({"business_name": "X"})

    def test_document_agent_unrecognised_status(self):
        bad_docs = {
            "required_documents": [
                {"name": "Some Doc", "key": "some_doc", "status": "unknown_status"}
            ]
        }
        with pytest.raises(ValueError, match="unrecognised status"):
            run_document_agent(bad_docs)

    def test_underwriting_agent_missing_cash_flow_key(self, risk_result, document_result):
        incomplete_cf = {"agent": "Cash Flow Agent"}  # missing required keys
        with pytest.raises(ValueError, match="cash_flow_findings"):
            run_underwriting_preparation_agent(
                GREENFIELD_BUSINESS,
                incomplete_cf,
                risk_result,
                document_result,
            )

    def test_underwriting_agent_missing_business_name(
        self, cash_flow_result, risk_result, document_result
    ):
        with pytest.raises(ValueError, match="business_name"):
            run_underwriting_preparation_agent(
                {},  # no business_name
                cash_flow_result,
                risk_result,
                document_result,
            )
