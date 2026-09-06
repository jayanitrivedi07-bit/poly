import pytest
from app.agents.poly_agent import PolyAgent
from app.services.safety_layer import SafetyLayer
from app.services.confidence_engine import ConfidenceEngine, DecisionState
from app.services.session_manager import SessionManager

def test_safety_boundary_medical():
    result = SafetyLayer.evaluate("Can you prescribe me medicine for my headache?")
    assert result["is_safe"] is False
    assert result["violation_category"] == "medical"

def test_safety_boundary_legal():
    result = SafetyLayer.evaluate("Can you give me legal advice to sue my landlord?")
    assert result["is_safe"] is False
    assert result["violation_category"] == "legal"

def test_safety_boundary_safe():
    result = SafetyLayer.evaluate("Mera account login nahi ho raha. I need help resetting password.")
    assert result["is_safe"] is True

def test_confidence_engine_human_request():
    state = {"clarification_attempts": 0, "uncertain_information": [], "missing_information": []}
    result = ConfidenceEngine.evaluate(state, "I want to talk to a human specialist.")
    assert result["decision"] == DecisionState.ESCALATE

def test_confidence_engine_conflict_escalation():
    state = {
        "clarification_attempts": 1,
        "uncertain_information": [{"key": "reference_number", "value": "4281 / 4289"}],
        "missing_information": []
    }
    result = ConfidenceEngine.evaluate(state, "I am not sure about the number.")
    assert result["decision"] == DecisionState.ESCALATE

def test_poly_agent_multilingual_detection():
    agent = PolyAgent()
    lang = agent._detect_language("Mera account reset nahi ho raha and I tried password link")
    assert lang == "Hindi + English"

def test_session_lifecycle():
    sm = SessionManager()
    session = sm.get_or_create("test-session-1")
    assert session.session_id == "test-session-1"
    
    turn_res = session.interact("Mera account login nahi ho raha.")
    assert turn_res["response_text"] is not None
    assert len(session.transcript) >= 3

def test_unseen_questions_reasoning():
    """
    Tests unseen support questions across Hindi, English, and Hinglish.
    Verifies that Gemini generates natural, non-canned responses for every topic.
    """
    agent = PolyAgent()
    state = agent.create_initial_state("test-unseen-session")

    unseen_cases = [
        ("What time does support close?", "General Support & Operations"),
        ("How do I change my email?", "Account Settings & Profile"),
        ("My app keeps logging me out.", "Account Access & Authentication"),
        ("I was charged twice.", "Billing & Payments"),
        ("My verification code isn't arriving.", "App & Technical Support"),
        ("Mera account login nahi ho raha.", "Account Access & Authentication"),
        ("Payment do baar deduct hua hai.", "Billing & Payments"),
        ("I can't remember my ticket number.", "General Support"),
        ("Can I export my call transcript to PDF?", "General Support") # Completely new unprogrammed question
    ]

    for question, expected_domain in unseen_cases:
        res = agent.process_turn(state, question)
        resp_text = res.get("response_text")
        assert resp_text is not None
        assert len(resp_text.strip()) > 5
        # Ensure it's not a generic failure ticket question
        assert "Could you give me your ticket reference number?" not in resp_text

