from typing import Dict, Any, List

class DecisionState:
    CONTINUE = "CONTINUE"
    CLARIFY = "CLARIFY"
    CONFIRM = "CONFIRM"
    ESCALATE = "ESCALATE"

class ConfidenceEngine:
    @staticmethod
    def evaluate(state: Dict[str, Any], caller_input: str) -> Dict[str, Any]:
        """
        Evaluates observable signals to determine Poly Agent decision state:
        - CONTINUE: Normal dialogue flow
        - CLARIFY: Information is missing or ambiguous
        - CONFIRM: Critical detail captured (e.g. reference number) requiring verification
        - ESCALATE: Unresolved conflict, multiple failed clarifications, explicit human request, or safety policy trigger
        """
        text_lower = caller_input.lower()
        
        # 1. Explicit Human Request
        human_request_keywords = ["human", "agent", "representative", "specialist", "real person", "talk to human", "connect agent", "speak to someone"]
        if any(kw in text_lower for kw in human_request_keywords):
            return {
                "decision": DecisionState.ESCALATE,
                "reason": "Caller explicitly requested a human support specialist.",
                "confidence_score": 1.0
            }

        # 2. Repeated Clarification Attempts (> 2 attempts)
        clarification_attempts = state.get("clarification_attempts", 0)
        if clarification_attempts >= 2:
            return {
                "decision": DecisionState.ESCALATE,
                "reason": f"Multiple clarification attempts ({clarification_attempts}) failed to resolve information conflict.",
                "confidence_score": 0.4
            }

        # 3. Conflicting / Uncertain Information present
        uncertain_info = state.get("uncertain_information", [])
        if len(uncertain_info) > 0 and clarification_attempts >= 1:
            return {
                "decision": DecisionState.ESCALATE,
                "reason": "Conflicting reference details provided by caller could not be confidently verified.",
                "confidence_score": 0.5
            }

        # 4. Critical Detail Needing Confirmation
        # Check if reference_number or customer_id was just provided but not yet confirmed
        recent_reference = state.get("reference_number")
        confirmed_keys = [item.get("key") for item in state.get("confirmed_information", [])]
        
        if recent_reference and "reference_number" not in confirmed_keys and "reference_number" not in [u.get("key") for u in uncertain_info]:
            return {
                "decision": DecisionState.CONFIRM,
                "reason": f"Critical detail 'reference_number' ({recent_reference}) requires confirmation.",
                "confidence_score": 0.85
            }

        # 5. Missing Required Information
        missing_info = state.get("missing_information", [])
        if len(missing_info) > 0 and not state.get("intent") and state.get("clarification_attempts", 0) > 1:
            return {
                "decision": DecisionState.CLARIFY,
                "reason": "Caller issue/intent remains ambiguous after multiple turns.",
                "confidence_score": 0.7
            }

        # 6. Default Continue — Natural dialogue flow
        return {
            "decision": DecisionState.CONTINUE,
            "reason": "High-confidence conversational progress.",
            "confidence_score": 0.95
        }
