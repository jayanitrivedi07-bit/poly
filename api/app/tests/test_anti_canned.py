import pytest
from app.agents.poly_agent import PolyAgent

def test_anti_canned_responses():
    """
    Verifies that unrelated questions produce contextually distinct responses
    and NEVER output the old canned fallback 'Could you give me your ticket reference number?'.
    """
    agent = PolyAgent()
    state = agent.create_initial_state("test-anti-canned-session")

    unrelated_questions = [
        "How do I change my email?",
        "What are your support hours?",
        "I was charged twice.",
        "My app keeps logging me out.",
        "Why isn't my verification code coming?",
        "Can I export my account data to a file?" # Completely independent unseen question
    ]

    responses = []
    for q in unrelated_questions:
        res = agent.process_turn(state, q)
        resp_text = res.get("response_text")
        
        assert resp_text is not None, f"Response text for '{q}' should not be None"
        
        # EXPLICIT ANTI-CANNED CHECK:
        # Must NOT generate the old universal fallback ticket request for unrelated questions
        assert "Could you give me your ticket reference number?" not in resp_text, \
            f"Universal ticket fallback detected for question '{q}': {resp_text}"
        
        responses.append(resp_text)

    # Ensure responses are contextually different (not repetitive canned strings)
    unique_responses = set(responses)
    assert len(unique_responses) == len(responses), \
        f"Responses were repeated instead of contextually generated! Unique: {len(unique_responses)} / {len(responses)}"
