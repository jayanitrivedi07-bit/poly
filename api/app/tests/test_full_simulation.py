import pytest
from app.services.session_manager import PolySession, session_manager
from app.agents.poly_agent import PolyAgent
from app.services.confidence_engine import ConfidenceEngine, DecisionState
from app.services.escalation_service import EscalationService
from app.models.all_models import Case, CaseStatus, ExtractedInformation

def test_full_poly_end_to_end_simulation():
    # 1. Session Starts
    session = PolySession("sim-session-101", "Aarav Patel")
    assert session.state["customer_name"] == "Aarav Patel"
    assert session.state["controller"] == "AI"

    # 2. Caller speaks in Hindi
    res1 = session.interact("Namaste, mera account login nahi ho raha.")
    assert session.state["active_language"] in ["Hindi", "Hindi + English"]
    assert session.state["issue"] == "Account Access & Authentication"

    # 3. Caller switches to Hinglish and provides reference number
    res2 = session.interact("My reference number is 4281.")
    assert session.state["active_language"] == "Hindi + English"
    assert session.state["reference_number"] == "4281"
    # Action should be CONFIRM
    assert res2["action"] == DecisionState.CONFIRM

    # 4. Caller confirms initial reference number
    res3 = session.interact("Yes, that is correct.")
    confirmed_keys = [item["key"] for item in session.state["confirmed_information"]]
    assert "reference_number" in confirmed_keys

    # 5. Caller provides conflicting reference number
    res4 = session.interact("Actually ek second, reference number is 4289.")
    assert len(session.state["uncertain_information"]) > 0
    assert session.state["clarification_attempts"] >= 1

    # 6. Caller requests human or repeated clarification fails -> Escalation
    res5 = session.interact("Mujhe human agent se baat karni hai.")
    assert res5["action"] == DecisionState.ESCALATE
    assert session.state["escalation_required"] is True

    # 7. Escalation Service triggers case creation
    escalation_res = EscalationService.trigger_escalation(
        session_id=session.session_id,
        customer_name=session.state["customer_name"],
        language=session.state["active_language"],
        issue_category=session.state["issue"],
        reason=session.state["escalation_reason"],
        confirmed_info=session.state["confirmed_information"],
        uncertain_info=session.state["uncertain_information"],
        summary=session.state["summary"]
    )

    assert escalation_res["status"] == "SUCCESS"
    case_number = escalation_res["case_number"]

    # 8. Support Agent accepts handoff
    accept_res1 = EscalationService.accept_handoff(case_number, "Priya Sharma")
    assert accept_res1["status"] == "SUCCESS"
    assert accept_res1["status_name"] == CaseStatus.IN_PROGRESS

    # 9. AI Yield verification (Session controller set to HUMAN)
    session.yield_control_to_human("Priya Sharma")
    assert session.state["controller"] == "HUMAN"

    res_post_yield = session.interact("Hello?")
    assert res_post_yield["response_text"] is None
    assert res_post_yield["action"] == "YIELDED"

    # 10. Race Condition Check: Second agent trying to accept same case is blocked
    accept_res2 = EscalationService.accept_handoff(case_number, "Ananya Roy")
    assert accept_res2["status"] == "CONFLICT"

    # 11. Complete Case
    complete_res = EscalationService.complete_case(case_number, "Resolved reference conflict with caller.")
    assert complete_res["status"] == "SUCCESS"
    assert complete_res["status_name"] == CaseStatus.RESOLVED
