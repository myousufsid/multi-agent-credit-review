"""
test_supervisor.py — pytest suite for the Stage 4 Supervisor Agent.

Covers:
  1.  Supervisor successfully executes the complete workflow.
  2.  All four agent functions are actually invoked.
  3.  Risk Agent receives the Cash Flow Agent's liquidity_metrics.
  4.  Underwriting Agent receives all three specialist outputs.
  5.  Final report contains the expected Greenfield Supplies figures.
  6.  Missing Profit and Loss Statement is identified.
  7.  Workflow metadata correctly identifies agents and their statuses.
  8.  Invalid input is handled appropriately.
  9.  An agent failure does not result in a falsely successful report.
"""

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock

from app.agents.supervisor_agent import run_supervisor_review


# ---------------------------------------------------------------------------
# Fixtures — real sample data matching the JSON fixture files
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
        {"name": "Recent Bank Statements",    "key": "bank_statements",       "status": "received"},
        {"name": "Business Tax Return",       "key": "tax_return",            "status": "received"},
        {"name": "Profit and Loss Statement", "key": "profit_loss_statement", "status": "missing"},
        {"name": "Balance Sheet",             "key": "balance_sheet",         "status": "received"},
    ],
}


@pytest.fixture
def result():
    """Run the full supervisor workflow once and cache for the test class."""
    return run_supervisor_review(GREENFIELD_BUSINESS, GREENFIELD_DOCUMENTS)


# ---------------------------------------------------------------------------
# 1. Successful workflow completion
# ---------------------------------------------------------------------------
class TestWorkflowCompletion:
    def test_workflow_status_is_completed(self, result):
        assert result["workflow_status"] == "completed"

    def test_business_name_in_result(self, result):
        assert result["business_name"] == "Greenfield Supplies"

    def test_final_report_is_present(self, result):
        assert result["final_report"] is not None

    def test_human_review_requirement_at_top_level(self, result):
        requirement = result["human_review_requirement"]
        assert isinstance(requirement, str) and len(requirement) > 0
        assert "human" in requirement.lower() or "review" in requirement.lower()


# ---------------------------------------------------------------------------
# 2. All four agent functions are actually invoked
# ---------------------------------------------------------------------------
class TestAgentInvocation:
    def test_agents_executed_contains_all_four(self, result):
        executed = result["agents_executed"]
        assert "Cash Flow Agent"             in executed
        assert "Financial Risk Agent"        in executed
        assert "Document Agent"              in executed
        assert "Underwriting Preparation Agent" in executed

    def test_agents_executed_in_correct_order(self, result):
        executed = result["agents_executed"]
        # Cash Flow must come before Risk (dependency order)
        assert executed.index("Cash Flow Agent") < executed.index("Financial Risk Agent")
        # All specialists before Underwriting
        for specialist in ("Cash Flow Agent", "Financial Risk Agent", "Document Agent"):
            assert executed.index(specialist) < executed.index("Underwriting Preparation Agent")

    def test_all_agents_called_via_mock(self):
        """Confirm the supervisor actually calls all four agent functions."""
        with (
            patch("app.agents.supervisor_agent.run_cash_flow_agent") as mock_cf,
            patch("app.agents.supervisor_agent.run_financial_risk_agent") as mock_risk,
            patch("app.agents.supervisor_agent.run_document_agent") as mock_doc,
            patch("app.agents.supervisor_agent.run_underwriting_preparation_agent") as mock_uw,
        ):
            # Provide minimal valid return shapes so the supervisor can proceed.
            mock_cf.return_value = {
                "agent": "Cash Flow Agent",
                "status": "completed",
                "liquidity_metrics": {"available_credit": Decimal("0")},
                "findings": [],
                "supporting_evidence": {},
                "unresolved_questions": [],
            }
            mock_risk.return_value = {
                "agent": "Financial Risk Agent",
                "status": "completed",
                "warning_signs": [],
                "positive_indicators": [],
                "supporting_evidence": {},
                "unresolved_questions": [],
            }
            mock_doc.return_value = {
                "agent": "Document Agent",
                "status": "completed",
                "is_complete": True,
                "received_documents": [],
                "missing_documents": [],
                "findings": [],
                "unresolved_questions": [],
            }
            mock_uw.return_value = {
                "agent": "Underwriting Preparation Agent",
                "status": "completed",
                "business_overview": {},
                "liquidity_analysis": {},
                "financial_indicators": {},
                "document_completeness": {},
                "all_unresolved_questions": [],
                "supporting_evidence": {},
                "source_findings": {},
                "human_review_requirement": "HUMAN REVIEW REQUIRED.",
            }

            run_supervisor_review(GREENFIELD_BUSINESS, GREENFIELD_DOCUMENTS)

            mock_cf.assert_called_once()
            mock_risk.assert_called_once()
            mock_doc.assert_called_once()
            mock_uw.assert_called_once()


# ---------------------------------------------------------------------------
# 3. Risk Agent receives the Cash Flow Agent's liquidity_metrics
# ---------------------------------------------------------------------------
class TestMetricsPropagation:
    def test_risk_agent_receives_cash_flow_metrics(self):
        """
        Intercept the call to run_financial_risk_agent and verify that the
        second argument is the liquidity_metrics dict produced by the
        Cash Flow Agent, not a separately constructed dict.
        """
        with (
            patch("app.agents.supervisor_agent.run_cash_flow_agent") as mock_cf,
            patch("app.agents.supervisor_agent.run_financial_risk_agent") as mock_risk,
            patch("app.agents.supervisor_agent.run_document_agent") as mock_doc,
            patch("app.agents.supervisor_agent.run_underwriting_preparation_agent") as mock_uw,
        ):
            sentinel_metrics = {"sentinel": True, "available_credit": Decimal("7000")}
            mock_cf.return_value = {
                "agent": "Cash Flow Agent",
                "status": "completed",
                "liquidity_metrics": sentinel_metrics,
                "findings": [],
                "supporting_evidence": {},
                "unresolved_questions": [],
            }
            mock_risk.return_value = {
                "agent": "Financial Risk Agent", "status": "completed",
                "warning_signs": [], "positive_indicators": [],
                "supporting_evidence": {}, "unresolved_questions": [],
            }
            mock_doc.return_value = {
                "agent": "Document Agent", "status": "completed",
                "is_complete": True, "received_documents": [],
                "missing_documents": [], "findings": [], "unresolved_questions": [],
            }
            mock_uw.return_value = {
                "agent": "Underwriting Preparation Agent", "status": "completed",
                "business_overview": {}, "liquidity_analysis": {},
                "financial_indicators": {}, "document_completeness": {},
                "all_unresolved_questions": [], "supporting_evidence": {},
                "source_findings": {},
                "human_review_requirement": "HUMAN REVIEW REQUIRED.",
            }

            run_supervisor_review(GREENFIELD_BUSINESS, GREENFIELD_DOCUMENTS)

            # Second positional arg to run_financial_risk_agent must be the
            # exact same metrics object returned by run_cash_flow_agent.
            _, call_kwargs = mock_risk.call_args
            call_args_positional = mock_risk.call_args[0]
            # Support both positional and keyword passing
            if len(call_args_positional) >= 2:
                passed_metrics = call_args_positional[1]
            else:
                passed_metrics = mock_risk.call_args[1].get("liquidity_metrics")
            assert passed_metrics is sentinel_metrics


# ---------------------------------------------------------------------------
# 4. Underwriting Agent receives all three specialist outputs
# ---------------------------------------------------------------------------
class TestUnderwritingInputs:
    def test_underwriting_receives_all_three_specialist_outputs(self):
        """Verify the underwriting agent is called with the exact dicts
        returned by the three specialist agents."""
        with (
            patch("app.agents.supervisor_agent.run_cash_flow_agent") as mock_cf,
            patch("app.agents.supervisor_agent.run_financial_risk_agent") as mock_risk,
            patch("app.agents.supervisor_agent.run_document_agent") as mock_doc,
            patch("app.agents.supervisor_agent.run_underwriting_preparation_agent") as mock_uw,
        ):
            cf_out = {
                "agent": "Cash Flow Agent", "status": "completed",
                "liquidity_metrics": {}, "findings": [],
                "supporting_evidence": {}, "unresolved_questions": [],
            }
            risk_out = {
                "agent": "Financial Risk Agent", "status": "completed",
                "warning_signs": [], "positive_indicators": [],
                "supporting_evidence": {}, "unresolved_questions": [],
            }
            doc_out = {
                "agent": "Document Agent", "status": "completed",
                "is_complete": True, "received_documents": [],
                "missing_documents": [], "findings": [], "unresolved_questions": [],
            }
            mock_cf.return_value = cf_out
            mock_risk.return_value = risk_out
            mock_doc.return_value = doc_out
            mock_uw.return_value = {
                "agent": "Underwriting Preparation Agent", "status": "completed",
                "business_overview": {}, "liquidity_analysis": {},
                "financial_indicators": {}, "document_completeness": {},
                "all_unresolved_questions": [], "supporting_evidence": {},
                "source_findings": {},
                "human_review_requirement": "HUMAN REVIEW REQUIRED.",
            }

            run_supervisor_review(GREENFIELD_BUSINESS, GREENFIELD_DOCUMENTS)

            args = mock_uw.call_args[0]
            # args: (business_data, cash_flow_findings, risk_findings, doc_findings)
            assert args[1] is cf_out
            assert args[2] is risk_out
            assert args[3] is doc_out


# ---------------------------------------------------------------------------
# 5. Final report contains the expected Greenfield Supplies figures
# ---------------------------------------------------------------------------
class TestGreenfieldFigures:
    def test_available_credit(self, result):
        metrics = result["final_report"]["liquidity_analysis"]["metrics"]
        assert metrics["available_credit"] == Decimal("7000")

    def test_credit_utilization(self, result):
        metrics = result["final_report"]["liquidity_analysis"]["metrics"]
        assert metrics["credit_utilization_pct"] == Decimal("90.67")

    def test_upcoming_obligations(self, result):
        metrics = result["final_report"]["liquidity_analysis"]["metrics"]
        assert metrics["upcoming_obligations"] == Decimal("56000")

    def test_remaining_funding_gap(self, result):
        metrics = result["final_report"]["liquidity_analysis"]["metrics"]
        assert metrics["remaining_funding_gap"] == Decimal("30000")

    def test_immediate_liquidity(self, result):
        metrics = result["final_report"]["liquidity_analysis"]["metrics"]
        assert metrics["immediate_liquidity"] == Decimal("26000")

    def test_business_name_in_report(self, result):
        assert (
            result["final_report"]["business_overview"]["business_name"]
            == "Greenfield Supplies"
        )


# ---------------------------------------------------------------------------
# 6. Missing Profit and Loss Statement is identified
# ---------------------------------------------------------------------------
class TestMissingDocument:
    def test_profit_loss_in_missing_list(self, result):
        missing = result["final_report"]["document_completeness"]["missing_documents"]
        assert "Profit and Loss Statement" in missing

    def test_document_completeness_is_false(self, result):
        assert result["final_report"]["document_completeness"]["is_complete"] is False

    def test_missing_document_in_unresolved_questions(self, result):
        questions_text = " ".join(
            q["question"] for q in result["final_report"]["all_unresolved_questions"]
        )
        assert "Profit and Loss Statement" in questions_text


# ---------------------------------------------------------------------------
# 7. Workflow metadata correctly identifies agents and statuses
# ---------------------------------------------------------------------------
class TestWorkflowMetadata:
    def test_agent_statuses_all_completed(self, result):
        for agent_name, status in result["agent_statuses"].items():
            assert status == "completed", (
                f"Expected 'completed' for {agent_name}, got '{status}'"
            )

    def test_agent_statuses_has_all_four_agents(self, result):
        statuses = result["agent_statuses"]
        assert "Cash Flow Agent"                in statuses
        assert "Financial Risk Agent"           in statuses
        assert "Document Agent"                 in statuses
        assert "Underwriting Preparation Agent" in statuses

    def test_no_error_key_on_success(self, result):
        assert "error" not in result
        assert "failed_agent" not in result


# ---------------------------------------------------------------------------
# 8. Invalid input is handled appropriately
# ---------------------------------------------------------------------------
class TestInvalidInput:
    def test_empty_business_data_raises(self):
        with pytest.raises(ValueError, match="business_data"):
            run_supervisor_review({}, GREENFIELD_DOCUMENTS)

    def test_none_business_data_raises(self):
        with pytest.raises(ValueError, match="business_data"):
            run_supervisor_review(None, GREENFIELD_DOCUMENTS)

    def test_empty_document_data_raises(self):
        with pytest.raises(ValueError, match="document_data"):
            run_supervisor_review(GREENFIELD_BUSINESS, {})

    def test_none_document_data_raises(self):
        with pytest.raises(ValueError, match="document_data"):
            run_supervisor_review(GREENFIELD_BUSINESS, None)


# ---------------------------------------------------------------------------
# 9. Agent failure does not produce a falsely successful report
# ---------------------------------------------------------------------------
class TestAgentFailurePropagation:
    def _make_failing_cf(self):
        """Return a mock that raises when run_cash_flow_agent is called."""
        m = MagicMock(side_effect=ValueError("Simulated cash flow agent failure"))
        return m

    def test_cash_flow_failure_returns_failed_status(self):
        with patch(
            "app.agents.supervisor_agent.run_cash_flow_agent",
            side_effect=ValueError("bad business data"),
        ):
            result = run_supervisor_review(GREENFIELD_BUSINESS, GREENFIELD_DOCUMENTS)
        assert result["workflow_status"] == "failed"
        assert result["final_report"] is None

    def test_cash_flow_failure_identifies_failed_agent(self):
        with patch(
            "app.agents.supervisor_agent.run_cash_flow_agent",
            side_effect=ValueError("bad business data"),
        ):
            result = run_supervisor_review(GREENFIELD_BUSINESS, GREENFIELD_DOCUMENTS)
        assert result["failed_agent"] == "Cash Flow Agent"
        assert result["agent_statuses"]["Cash Flow Agent"] == "failed"

    def test_risk_failure_returns_failed_status(self):
        with patch(
            "app.agents.supervisor_agent.run_financial_risk_agent",
            side_effect=RuntimeError("Simulated risk agent crash"),
        ):
            result = run_supervisor_review(GREENFIELD_BUSINESS, GREENFIELD_DOCUMENTS)
        assert result["workflow_status"] == "failed"
        assert result["failed_agent"] == "Financial Risk Agent"
        assert result["final_report"] is None

    def test_document_failure_returns_failed_status(self):
        with patch(
            "app.agents.supervisor_agent.run_document_agent",
            side_effect=ValueError("bad document data"),
        ):
            result = run_supervisor_review(GREENFIELD_BUSINESS, GREENFIELD_DOCUMENTS)
        assert result["workflow_status"] == "failed"
        assert result["failed_agent"] == "Document Agent"

    def test_underwriting_failure_returns_failed_status(self):
        with patch(
            "app.agents.supervisor_agent.run_underwriting_preparation_agent",
            side_effect=ValueError("bad underwriting input"),
        ):
            result = run_supervisor_review(GREENFIELD_BUSINESS, GREENFIELD_DOCUMENTS)
        assert result["workflow_status"] == "failed"
        assert result["failed_agent"] == "Underwriting Preparation Agent"

    def test_failure_always_has_human_review_requirement(self):
        with patch(
            "app.agents.supervisor_agent.run_cash_flow_agent",
            side_effect=ValueError("fail"),
        ):
            result = run_supervisor_review(GREENFIELD_BUSINESS, GREENFIELD_DOCUMENTS)
        assert "human_review_requirement" in result
        assert len(result["human_review_requirement"]) > 0

    def test_error_message_contains_exception_info(self):
        with patch(
            "app.agents.supervisor_agent.run_cash_flow_agent",
            side_effect=ValueError("specifically this error message"),
        ):
            result = run_supervisor_review(GREENFIELD_BUSINESS, GREENFIELD_DOCUMENTS)
        assert "specifically this error message" in result["error"]
