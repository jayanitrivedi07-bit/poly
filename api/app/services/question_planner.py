from typing import Dict, Any, List, Optional

class QuestionPlanner:
    @staticmethod
    def get_next_question_field(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Determines if there is a specific field needing clarification or confirmation.
        Returns None to allow natural open-ended conversational dialogue with Gemini.
        """
        uncertain_info = state.get("uncertain_information", [])
        confirmed_keys = [f.get("key") for f in state.get("confirmed_information", [])]

        # 1. Prioritize uncertain fields needing clarification (e.g. 4281 vs 4289)
        if uncertain_info:
            for item in uncertain_info:
                return {
                    "key": item.get("key", "reference_number"),
                    "label": item.get("label", "Reference Number"),
                    "priority": 1,
                    "critical": True
                }

        # 2. Only return missing reference field if caller explicitly mentioned having a ticket or reference
        if state.get("ticket_mentioned") and "reference_number" not in confirmed_keys:
            return {
                "key": "reference_number",
                "label": "Ticket / Reference Number",
                "priority": 1,
                "critical": True
            }

        # Return None so Gemini Flash handles open-ended support conversation naturally
        return None

