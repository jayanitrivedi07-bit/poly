import re
from typing import Dict, Any

RESTRICTED_KEYWORDS = {
    "medical": [
        "diagnose", "diagnosis", "prescription", "symptoms", "medical advice",
        "doctor", "heart attack", "stroke", "cancer", "treatment", "medicine"
    ],
    "emergency": [
        "ambulance", "fire department", "911", "112", "police emergency",
        "active fire", "suicide", "bleeding profusely"
    ],
    "legal": [
        "legal advice", "sue", "lawsuit", "court representation", "legal opinion",
        "criminal defense"
    ],
    "financial": [
        "stock advice", "investment guarantee", "crypto tip", "financial planning advice"
    ]
}

class SafetyLayer:
    @staticmethod
    def evaluate(text: str) -> Dict[str, Any]:
        """
        Evaluates input text against Poly's strict safety boundary policies:
        - No medical diagnosis
        - No emergency responder replacement
        - No legal advice
        - No financial investment advice
        """
        lower_text = text.lower()
        
        for category, keywords in RESTRICTED_KEYWORDS.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', lower_text):
                    return {
                        "is_safe": False,
                        "violation_category": category,
                        "reason": f"Request contains restricted {category} topics: '{kw}'",
                        "explanation": f"Poly is an assistance-line agent and cannot provide {category} advice or replace emergency services. Connecting to a human support specialist."
                    }
                    
        return {
            "is_safe": True,
            "violation_category": None,
            "reason": None,
            "explanation": None
        }
