import uuid
import logging
from typing import Dict, Any, Optional
from app.agents.poly_agent import poly_agent
from app.database.session import SessionLocal
from app.models.all_models import Case, Conversation, Message, ExtractedInformation, CaseStatus, Escalation, AuditEvent

logger = logging.getLogger(__name__)

class PolySession:
    def __init__(self, session_id: str, caller_name: str = "Aarav Patel"):
        self.session_id = session_id
        self.agora_channel = f"poly-{session_id}"
        self.state = poly_agent.create_initial_state(session_id, caller_name)
        self.transcript: list = [
            {
                "id": "t-0",
                "speaker": "poly",
                "speaker_name": "POLY Assistant",
                "timestamp_offset": "00:05",
                "originalText": "Namaste! Welcome to Poly Support. How can I help you with your account today?",
                "translatedText": "Namaste! Welcome to Poly Support. How can I help you with your account today?"
            }
        ]

    def interact(self, text: str) -> Dict[str, Any]:
        """Processes caller turn and updates session state and transcript."""
        # 0. Check AI Yield Controller Lock
        if self.state.get("controller") == "HUMAN":
            return {
                "session_id": self.session_id,
                "agora_channel": self.agora_channel,
                "response_text": None,
                "action": "YIELDED",
                "state": self.state,
                "transcript": self.transcript
            }

        turn_id = f"t-{len(self.transcript) + 1}"
        
        # Record caller turn
        self.transcript.append({
            "id": turn_id,
            "speaker": "caller",
            "speaker_name": self.state["customer_name"],
            "timestamp_offset": "00:15",
            "originalText": text,
            "translatedText": text,
            "language": self.state["active_language"]
        })

        # Poly Agent turn processing
        agent_result = poly_agent.process_turn(self.state, text, transcript=self.transcript)
        response_text = agent_result.get("response_text")

        # Record Poly response turn if not yielded
        if response_text:
            poly_turn_id = f"t-{len(self.transcript) + 1}"
            self.transcript.append({
                "id": poly_turn_id,
                "speaker": "poly",
                "speaker_name": "POLY Assistant",
                "timestamp_offset": "00:20",
                "originalText": response_text,
                "translatedText": response_text
            })

        # If escalation was triggered, persist case to database
        if self.state["escalation_required"]:
            self._persist_escalated_case()

        return {
            "session_id": self.session_id,
            "agora_channel": self.agora_channel,
            "turn_id": turn_id,
            "response_text": response_text,
            "action": agent_result.get("action"),
            "state": self.state,
            "transcript": self.transcript
        }

    def yield_control_to_human(self, agent_name: str = "Priya Sharma"):
        """Locks AI speech controller and yields conversation control to human specialist."""
        self.state["controller"] = "HUMAN"
        self.state["ai_yielded"] = True
        self.state["assigned_agent"] = agent_name

    def _persist_escalated_case(self):
        """Persists case, escalation, and audit events to database upon escalation."""
        db = SessionLocal()
        try:
            # Check if case already exists for this session to prevent duplicate creation
            if self.state.get("case_id"):
                existing = db.query(Case).filter(Case.id == self.state["case_id"]).first()
                if existing:
                    return existing

            count = db.query(Case).count()
            case_number = f"POLY-{1024 + count}"

            db_case = Case(
                case_number=case_number,
                language=self.state["active_language"],
                issue_category=self.state.get("issue") or "Account Access & Authentication",
                status=CaseStatus.WAITING_FOR_HUMAN,
                escalation_reason=self.state.get("escalation_reason") or "Information uncertainty threshold reached",
                summary=self.state.get("summary") or "Escalated assistance call",
                otp_verified=True
            )
            db.add(db_case)
            db.commit()
            db.refresh(db_case)
            self.state["case_id"] = db_case.id
            self.state["case_number"] = db_case.case_number

            # Create Escalation queue item
            db.add(Escalation(
                case_id=db_case.id,
                priority="PRIORITY",
                routing_node="APAC-Central (Mumbai Edge)",
                status="PENDING"
            ))

            # Audit events
            db.add(AuditEvent(case_id=db_case.id, event_type="CALL_STARTED", title="Caller Session Started", description="Connected via Agora RTC", timestamp_offset="00:00"))
            db.add(AuditEvent(case_id=db_case.id, event_type="ESCALATION_TRIGGERED", title="Confidence Engine Escalation", description=db_case.escalation_reason, timestamp_offset="00:45"))
            db.add(AuditEvent(case_id=db_case.id, event_type="CASE_CREATED", title=f"Case {case_number} Created", description="Status: WAITING_FOR_HUMAN", timestamp_offset="01:00"))

            # Persist extracted fields
            for item in self.state.get("confirmed_information", []):
                db.add(ExtractedInformation(
                    case_id=db_case.id,
                    field_key=item.get("key", "info"),
                    field_label=item.get("label", "Field"),
                    field_value=item.get("value", "Confirmed"),
                    status="confirmed"
                ))

            for item in self.state.get("uncertain_information", []):
                db.add(ExtractedInformation(
                    case_id=db_case.id,
                    field_key=item.get("key", "info"),
                    field_label=item.get("label", "Field"),
                    field_value=item.get("value", "Uncertain"),
                    status="uncertain",
                    notes=item.get("notes")
                ))

            db.commit()
            logger.info(f"Persisted escalated case {case_number} for session {self.session_id}")
            return db_case
        except Exception as e:
            db.rollback()
            logger.error(f"Error persisting escalated case: {e}")
        finally:
            db.close()

class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, PolySession] = {}

    def get_or_create(self, session_id: Optional[str] = None) -> PolySession:
        if not session_id or session_id not in self._sessions:
            sid = session_id or f"session-{uuid.uuid4().hex[:8]}"
            self._sessions[sid] = PolySession(sid)
            return self._sessions[sid]
        return self._sessions[session_id]

    def get(self, session_id: str) -> Optional[PolySession]:
        return self._sessions.get(session_id)

session_manager = SessionManager()
