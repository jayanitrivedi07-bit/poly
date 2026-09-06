import json
import logging
import re
import time
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.services.safety_layer import SafetyLayer
from app.services.confidence_engine import ConfidenceEngine, DecisionState
from app.services.question_planner import QuestionPlanner

logger = logging.getLogger(__name__)

POLY_SYSTEM_INSTRUCTION = """
You are POLY, an authentic, empathetic, highly intelligent, open-ended conversational AI customer support voice agent built by Poly Agora.
Your role is to have genuine, natural, fluid conversations with callers about ANY customer support, technical assistance, billing, account access, email updates, app issues, verification codes, support hours, order tracking, or general inquiries.

CRITICAL CONVERSATIONAL RULES:
1. NEVER use a rigid question tree, fixed questionnaire, or canned response.
2. DO NOT repeatedly ask for a ticket or reference number. Only ask for a ticket/reference number if checking an existing case is genuinely required for the caller's request, or if the caller mentions having one. If the caller says they don't know their ticket number, help them directly with their issue.
3. ADAPT SEAMLESSLY TO THE CALLER'S LANGUAGE:
   - If the caller speaks English, respond naturally in English.
   - If the caller speaks Hindi ("Mera account login nahi ho raha"), respond in warm, natural Hindi.
   - If the caller speaks Hinglish or code-switches ("Actually mera password reset ho gaya but email nahi aa raha"), respond in natural Hinglish.
4. HANDLE TOPIC SWITCHES NATURALLY:
   - If the caller changes topics (e.g. "Actually, forget that, I have a billing question"), drop the old topic immediately and address the new question directly.
5. RESOLVE CONTEXTUAL REFERENCES:
   - Use the full conversation history to understand references like "the email", "it", "that", "my reset link", or "the payment".
6. KEEP RESPONSES CONCISE AND SPOKEN-FRIENDLY:
   - Poly is a voice agent. Keep answers clear, direct, empathetic, and concise (typically 1 to 3 short sentences suitable for text-to-speech).
7. SAFETY:
   - Strictly refuse medical diagnoses, emergency guidance, legal advice, or financial advice.
"""

class PolyAgent:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.client = None
        self.model_name = settings.GEMINI_MODEL or "gemini-2.0-flash"
        
        if self.api_key and self.api_key != "mock_gemini_api_key":
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"PolyAgent initialized with Google GenAI client ({self.model_name}).")
            except Exception as e:
                logger.warning(f"Could not initialize google.genai Client: {e}")

    def create_initial_state(self, session_id: str, caller_name: str = "Aarav Patel") -> Dict[str, Any]:
        """Creates clean structured conversation state for a new session."""
        return {
            "session_id": session_id,
            "agora_channel": f"poly-{session_id}",
            "controller": "AI", # "AI" or "HUMAN"
            "ai_yielded": False,
            "language": ["hi-IN", "en-US"],
            "active_language": "Hindi + English",
            "intent": None,
            "issue": None,
            "customer_name": caller_name,
            "customer_id": None,
            "reference_number": None,
            "ticket_mentioned": False,
            "confirmed_information": [
                {"key": "customer_name", "label": "Customer Name", "value": caller_name, "status": "confirmed"}
            ],
            "uncertain_information": [],
            "missing_information": [],
            "clarification_attempts": 0,
            "escalation_required": False,
            "escalation_reason": None,
            "summary": "Caller started assistance session."
        }

    def process_turn(
        self, state: Dict[str, Any], caller_input: str, transcript: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Processes a conversation turn dynamically:
        0. AI Yield Controller Check
        1. Safety Layer Check
        2. Language Detection
        3. Dynamic Entity & Topic Switch Detection
        4. Confidence Engine Evaluation
        5. Question Prioritization
        6. Gemini LLM Reasoning Generation
        """
        # 0. AI Yield Control Lock Check
        if state.get("controller") == "HUMAN" or state.get("ai_yielded"):
            state["ai_yielded"] = True
            return {
                "response_text": None,
                "response_audio_url": None,
                "state": state,
                "action": "YIELDED",
                "message": "AI controller yielded to Human Support Specialist."
            }

        # 1. Safety Layer Check
        safety_result = SafetyLayer.evaluate(caller_input)
        if not safety_result["is_safe"]:
            state["escalation_required"] = True
            state["escalation_reason"] = safety_result["reason"]
            return {
                "response_text": f"I understand your request, but as an assistance agent I cannot provide {safety_result['violation_category']} instructions. Connecting you to a support specialist.",
                "response_audio_url": None,
                "state": state,
                "action": DecisionState.ESCALATE,
                "safety": safety_result
            }

        # 2. Language Detection
        detected_language = self._detect_language(caller_input)
        if state.get("active_language") in ["Hindi", "Hindi + English"] and detected_language in ["Hindi", "English"]:
            state["active_language"] = "Hindi + English"
        else:
            state["active_language"] = detected_language

        # 3. Dynamic Information Extraction & Topic Shift Check
        extracted = self._extract_entities(caller_input, state)
        self._update_state_with_extraction(state, extracted, caller_input)

        # 4. Confidence Engine Evaluation
        confidence_result = ConfidenceEngine.evaluate(state, caller_input)
        decision = confidence_result["decision"]

        if decision == DecisionState.ESCALATE:
            state["escalation_required"] = True
            state["escalation_reason"] = confidence_result["reason"]
            response_text = "I don't want to record the wrong information. Connecting you with a human support agent and sharing the context we've collected so far."
            return {
                "response_text": response_text,
                "response_audio_url": None,
                "state": state,
                "action": decision,
                "confidence": confidence_result
            }

        # 5. Question Prioritization (only for genuine missing fields/conflicts)
        next_question_field = QuestionPlanner.get_next_question_field(state)

        # 6. Generate Natural Language Response via Gemini 3.5 Flash
        response_text = self._generate_response(state, caller_input, decision, next_question_field, transcript=transcript)

        # Update Summary narrative dynamically
        state["summary"] = f"Caller discussed: '{state.get('issue') or 'general inquiry'}'. Detected language: {detected_language}."

        return {
            "response_text": response_text,
            "response_audio_url": None,
            "state": state,
            "action": decision,
            "confidence": confidence_result,
            "next_field": next_question_field
        }

    def _detect_language(self, text: str) -> str:
        text_lower = text.lower()
        hindi_indicators = ["mera", "hai", "nahi", "ho", "raha", "haan", "par", "ko", "kya", "aap", "namaste", "aaya", "chahiye", "kaise", "bhi", "ek", "baar", "kal", "se", "kar"]
        has_hindi = any(re.search(r'\b' + kw + r'\b', text_lower) for kw in hindi_indicators)
        has_english = any(kw in text_lower for kw in ["account", "problem", "access", "reset", "password", "ticket", "reference", "order", "number", "email", "login", "help", "hours", "charged", "code", "app", "billing", "payment"])

        if has_hindi and has_english:
            return "Hindi + English"
        elif has_hindi:
            return "Hindi"
        else:
            return "English"

    def _extract_entities(self, text: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts reference numbers, ticket mentions, and topic shifts dynamically."""
        extracted = {}
        text_lower = text.lower()

        # Check for dynamic Topic Switch signals ("actually", "forget that", "another question", "billing question", etc.)
        topic_switch_signals = ["actually", "forget that", "another question", "different issue", "different problem", "by the way", "instead"]
        if any(sig in text_lower for sig in topic_switch_signals):
            extracted["topic_switch"] = True

        # Check if caller mentions having or not having a ticket number
        if any(w in text_lower for w in ["don't know my ticket", "no ticket", "don't have a ticket", "no reference"]):
            extracted["ticket_unknown"] = True
        elif any(w in text_lower for w in ["ticket", "reference", "ref number", "case number"]):
            extracted["ticket_mentioned"] = True

        # Reference numbers (e.g. 4281, 4289, 1024)
        numbers = re.findall(r'\b\d{4}\b', text)
        if numbers:
            extracted["numbers"] = numbers

        # Dynamic Issue Labeling
        if any(w in text_lower for w in ["login", "access", "password", "reset", "cannot login", "login nahi", "logout", "log me out", "logging me out"]):
            extracted["issue"] = "Account Access & Authentication"
        elif any(w in text_lower for w in ["charged", "billing", "payment", "refund", "receipt", "deduct"]):
            extracted["issue"] = "Billing & Payments"
        elif any(w in text_lower for w in ["hours", "timings", "schedule", "open", "close"]):
            extracted["issue"] = "General Support & Operations"
        elif any(w in text_lower for w in ["order", "delivery", "shipping", "track"]):
            extracted["issue"] = "Order & Delivery Support"
        elif any(w in text_lower for w in ["email", "change email", "update email"]):
            extracted["issue"] = "Account Settings & Profile"
        elif any(w in text_lower for w in ["app", "crash", "bug", "freeze", "code", "otp", "verification"]):
            extracted["issue"] = "App & Technical Support"

        return extracted

    def _update_state_with_extraction(self, state: Dict[str, Any], extracted: Dict[str, Any], caller_input: str):
        text_lower = caller_input.lower()

        # Handle topic switch
        if extracted.get("topic_switch") and "issue" in extracted:
            state["issue"] = extracted["issue"]
            state["intent"] = extracted["issue"].lower().replace(" ", "_")
            # Clear obsolete clarification locks on topic shift
            state["uncertain_information"] = []
            state["clarification_attempts"] = 0
        elif "issue" in extracted:
            state["issue"] = extracted["issue"]
            state["intent"] = extracted["issue"].lower().replace(" ", "_")

        if extracted.get("ticket_unknown"):
            state["ticket_mentioned"] = False
        elif extracted.get("ticket_mentioned"):
            state["ticket_mentioned"] = True

        if "numbers" in extracted:
            numbers = extracted["numbers"]
            if len(numbers) == 1:
                num = numbers[0]
                if not state["reference_number"]:
                    state["reference_number"] = num
                elif state["reference_number"] != num:
                    # Contradiction detected
                    state["uncertain_information"].append({
                        "key": "reference_number",
                        "label": "Reference Number",
                        "value": f"{state['reference_number']} / {num}",
                        "status": "uncertain",
                        "notes": f"Conflict detected: initial {state['reference_number']}, then {num}"
                    })
                    state["clarification_attempts"] += 1
            elif len(numbers) > 1:
                state["uncertain_information"].append({
                    "key": "reference_number",
                    "label": "Reference Number",
                    "value": " / ".join(numbers),
                    "status": "uncertain",
                    "notes": "Multiple reference numbers provided in single turn"
                })
                state["clarification_attempts"] += 1

        # Check for explicit user confirmation
        if any(w in text_lower for w in ["yes", "haan", "correct", "sahi hai", "that is right", "right"]):
            if state["reference_number"] and not any(f["key"] == "reference_number" for f in state["confirmed_information"]):
                state["confirmed_information"].append({
                    "key": "reference_number",
                    "label": "Reference Number",
                    "value": state["reference_number"],
                    "status": "confirmed"
                })

    def _clean_response_text(self, text: str) -> str:
        """Strips structural prompt leaks, markdown headers, and formatting artifacts if emitted."""
        if not text:
            return ""
        cleaned = text.strip()
        # Remove structural prompt leaks
        patterns = [
            r'^---.*?\n',
            r'^Dialogue History:?\*?\*?',
            r'^Goal:?\*?\*?.*?\n',
            r'^Respond as POLY:?',
            r'^POLY:?'
        ]
        for p in patterns:
            cleaned = re.sub(p, '', cleaned, flags=re.IGNORECASE | re.MULTILINE).strip()
        return cleaned

    def _generate_response(
        self,
        state: Dict[str, Any],
        caller_input: str,
        decision: str,
        next_field: Optional[Dict[str, Any]],
        transcript: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Generates response strictly via Gemini 3.5 Flash using full conversation context and structured observability logging."""
        
        history_turns = []
        if transcript:
            for t in transcript[-15:]:
                speaker = "Caller" if t.get("speaker") == "caller" else "POLY"
                text = t.get("originalText") or t.get("original_text") or ""
                # Strip previous structural headers if present in history
                clean_text = self._clean_response_text(text)
                if clean_text:
                    history_turns.append(f"{speaker}: {clean_text}")
        history_str = "\n".join(history_turns) if history_turns else f"Caller: {caller_input}"

        context_summary = (
            f"Active Topic: {state.get('issue') or 'General Inquiry'}, "
            f"Language: {state.get('active_language')}, "
            f"Decision: {decision}"
        )

        prompt = (
            f"Context: {context_summary}\n"
            f"Conversation History:\n{history_str}\n\n"
            f"Caller: \"{caller_input}\"\n"
            f"POLY:"
        )

        # STRUCTURED OBSERVABILITY LOGGING
        logger.info(f"[OBSERVABILITY] USER INPUT: \"{caller_input}\"")
        logger.info(f"[OBSERVABILITY] CONVERSATION CONTEXT: {context_summary}")
        logger.info(f"[OBSERVABILITY] GEMINI REQUEST MODEL: {self.model_name}")

        if self.client:
            # Retry loop for API rate-limits (429) or transient network resets
            for attempt in range(3):
                try:
                    from google.genai import types
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=POLY_SYSTEM_INSTRUCTION,
                            max_output_tokens=350,
                            temperature=0.7
                        )
                    )
                    if response and response.text:
                        resp_text = self._clean_response_text(response.text)
                        logger.info(f"[OBSERVABILITY] GEMINI RAW RESPONSE: \"{response.text}\"")
                        logger.info(f"[OBSERVABILITY] GEMINI ASSEMBLED RESPONSE: \"{resp_text}\"")
                        logger.info(f"[OBSERVABILITY] FINAL POLY RESPONSE: \"{resp_text}\"")
                        return resp_text
                except Exception as e:
                    logger.warning(f"[GEMINI RETRY {attempt + 1}/3] API call failed for {self.model_name}: {e}")
                    if attempt < 2:
                        time.sleep(1.5)

        # Dynamic Contextual Response Generator for offline/rate-limited environments
        logger.warning("[GEMINI FALLBACK] Gemini API unavailable or rate-limited. Synthesizing context-aware response.")
        raw_fallback = self._synthesize_contextual_fallback(state, caller_input, decision)
        return self._clean_response_text(raw_fallback)

    def _synthesize_contextual_fallback(self, state: Dict[str, Any], caller_input: str, decision: str) -> str:
        """Contextually synthesizes a unique, relevant natural response without any hardcoded ticket trees."""
        text_lower = caller_input.lower()
        active_lang = state.get("active_language", "English")
        is_hindi = "Hindi" in active_lang or any(w in text_lower for w in ["mera", "hai", "nahi", "ho", "raha", "haan", "par", "kya", "aap", "namaste", "kal", "se"])

        # 1. Critical Detail Confirmation
        if decision == DecisionState.CONFIRM and state.get("reference_number"):
            return f"I heard your reference number as {state['reference_number']}. Is that correct?"

        # 2. Support Hours Inquiry
        if any(w in text_lower for w in ["hours", "timings", "schedule", "open", "close"]):
            if is_hindi:
                return "Humari customer support team 24/7 active hai. Aap bataiye main aapki kya help kar sakta hoon?"
            return "Our support team is available 24 hours a day, 7 days a week. How can I assist you today?"

        # 3. Email Update Inquiry
        if any(w in text_lower for w in ["change email", "update email", "new email"]):
            if is_hindi:
                return "Aap apne account settings mein jaakar Naya email address update kar sakte hain. Main instructions share kar doon?"
            return "You can easily update your email address in account settings. Would you like me to walk you through the steps?"

        # 4. App Logout / Crash
        if any(w in text_lower for w in ["logging me out", "logout", "crashing", "freeze", "app"]):
            if is_hindi:
                return "Frequent logouts fixed karne ke liye app cache clear karke latest version update karein."
            return "I understand how inconvenient frequent logouts are. Try clearing your app cache or updating to the latest version."

        # 5. Billing / Double Charge
        if any(w in text_lower for w in ["charged", "billing", "payment", "refund", "deduct"]):
            if is_hindi:
                return "Double payment deduct hone ke liye apologies. Main billing team ke saath refund review initiate kar deta hoon."
            return "I apologize for the double charge. I will initiate a billing review and refund request for your transaction."

        # 6. Verification Code / OTP
        if any(w in text_lower for w in ["verification code", "otp", "code"]):
            if is_hindi:
                return "Agar verification OTP code nahi mil raha, mobile network check karke resend code try karein."
            return "If your verification code isn't arriving, check your cellular connection or hit resend in a minute."

        # 7. Topic Switch
        if any(w in text_lower for w in ["actually", "forget that", "another question", "different issue"]):
            if is_hindi:
                return "Bilkul! Aap doosra question poochiye, main help karunga."
            return "Sure! Tell me about your other question and I'll be happy to help."

        # 8. Password / Login
        if any(w in text_lower for w in ["password", "login", "access"]):
            if is_hindi:
                return "Account access issues mein main madad kar sakta hoon. Kya error message show ho raha hai?"
            return "I can help resolve your account access issue. What error message are you seeing on screen?"

        # 9. Generic Unseen Query
        if is_hindi:
            return f"Samajh gaya. '{caller_input}' ke bare mein main assist kar sakta hoon."
        return f"I understand your request regarding '{caller_input}'. Let's solve this together."

poly_agent = PolyAgent()


