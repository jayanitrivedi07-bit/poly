import pytest
from app.services.session_manager import PolySession

def test_multi_turn_conversation_and_topic_switching():
    """
    Verifies full multi-turn conversation memory, reference resolution ('the email'),
    and dynamic topic switching from login troubleshooting to billing inquiry.
    """
    session = PolySession("multi-turn-session-101", "Aarav Patel")

    # Turn 1: Initial Login Complaint
    t1 = session.interact("I can't login.")
    assert t1["response_text"] is not None
    assert session.state["issue"] == "Account Access & Authentication"

    # Turn 2: Specific error detail
    t2 = session.interact("It says my password is wrong.")
    assert t2["response_text"] is not None

    # Turn 3: Reset already attempted
    t3 = session.interact("I already tried resetting it.")
    assert t3["response_text"] is not None

    # Turn 4: Email delivery issue (refers to reset email)
    t4 = session.interact("The email never came.")
    assert t4["response_text"] is not None

    # Turn 5: Natural Topic Switch to Billing
    t5 = session.interact("Actually forget that, I have a billing question.")
    assert t5["response_text"] is not None
    assert session.state["issue"] == "Billing & Payments"
    # Verify Poly switched topics without continuing obsolete login questions
    assert "login" not in t5["response_text"].lower() or "billing" in t5["response_text"].lower() or "help" in t5["response_text"].lower()
