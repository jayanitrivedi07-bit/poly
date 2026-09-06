import pytest
from app.database.session import engine, Base
from app.services.escalation_service import EscalationService
from app.models.all_models import Case, Escalation, AuditEvent, CaseStatus

# Initialize tables
Base.metadata.create_all(bind=engine)

def test_trigger_escalation():
    res = EscalationService.trigger_escalation(
        session_id="sess-101",
        customer_name="Aarav Patel",
        language="Hindi + English",
        issue_category="Account Access & Authentication",
        reason="Conflicting reference number (4281 vs 4289)",
        confirmed_info=[{"key": "customer_id", "label": "Customer ID", "value": "4281"}],
        uncertain_info=[{"key": "reference_number", "label": "Reference Number", "value": "4281 / 4289", "notes": "Conflict"}],
        summary="Caller stated 4281 then 4289."
    )
    assert res["status"] == "SUCCESS"
    assert "case_number" in res
    assert res["status_name"] == CaseStatus.WAITING_FOR_HUMAN

def test_accept_handoff():
    trig_res = EscalationService.trigger_escalation(
        session_id="sess-102",
        customer_name="Meera Sharma",
        language="Hindi",
        issue_category="Billing",
        reason="Explicit human agent request",
        confirmed_info=[],
        uncertain_info=[],
        summary="Customer requested human agent."
    )
    case_number = trig_res["case_number"]

    accept_res = EscalationService.accept_handoff(case_number, agent_name="Priya Sharma")
    assert accept_res["status"] == "SUCCESS"
    assert accept_res["assigned_agent"] == "Priya Sharma"
    assert accept_res["status_name"] == CaseStatus.IN_PROGRESS

def test_handoff_package_generation():
    state = {
        "case_number": "POLY-1024",
        "customer_name": "Aarav Patel",
        "active_language": "Hindi + English",
        "intent": "account_assistance",
        "issue": "Account Access & Authentication",
        "confirmed_information": [{"key": "customer_id", "value": "4281"}],
        "uncertain_information": [{"key": "reference_number", "value": "4281 / 4289"}],
        "missing_information": ["reference_number"],
        "summary": "Caller provided conflicting numbers."
    }
    transcript = [
        {"speaker": "caller", "originalText": "Mera account login nahi ho raha."},
        {"speaker": "poly", "originalText": "What is your reference number?"}
    ]

    pkg = EscalationService.create_handoff_package(state, transcript, "Conflicting numbers")
    assert pkg["case_number"] == "POLY-1024"
    assert pkg["language"] == "Hindi + English"
    assert pkg["escalation_reason"] == "Conflicting numbers"
    assert len(pkg["confirmed_information"]) == 1

def test_complete_case():
    trig = EscalationService.trigger_escalation(
        session_id="sess-103",
        customer_name="Vikram Malhotra",
        language="English",
        issue_category="Service",
        reason="Complex setup",
        confirmed_info=[],
        uncertain_info=[],
        summary="Setup help needed."
    )
    case_num = trig["case_number"]
    EscalationService.accept_handoff(case_num, "Priya Sharma")

    comp_res = EscalationService.complete_case(case_num, "Resolved configuration issue")
    assert comp_res["status"] == "SUCCESS"
    assert comp_res["status_name"] == CaseStatus.RESOLVED
