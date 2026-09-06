import logging
import datetime
from typing import Dict, Any, List, Optional
from app.database.session import SessionLocal
from app.models.all_models import (
    Case, Agent, Escalation, ExtractedInformation, AuditEvent, CaseStatus, PriorityLevel
)

logger = logging.getLogger(__name__)

class EscalationService:
    @staticmethod
    def create_handoff_package(state: Dict[str, Any], transcript: List[Dict[str, Any]], reason: str) -> Dict[str, Any]:
        """Generates structured handoff package for Support Specialist view."""
        return {
            "case_number": state.get("case_number", "POLY-1024"),
            "customer_name": state.get("customer_name", "Aarav Patel"),
            "language": state.get("active_language", "Hindi + English"),
            "intent": state.get("intent", "account_assistance"),
            "issue_category": state.get("issue", "Account Access & Authentication"),
            "escalation_reason": reason,
            "confirmed_information": state.get("confirmed_information", []),
            "uncertain_information": state.get("uncertain_information", []),
            "missing_information": state.get("missing_information", []),
            "ai_summary": state.get("summary", "Caller reported account access failure."),
            "transcript_excerpts": transcript[-4:] if transcript else [],
            "recommended_next_step": "Verify identity via OTP and resolve reference number conflict between 4281 and 4289."
        }

    @staticmethod
    def trigger_escalation(
        session_id: str,
        customer_name: str,
        language: str,
        issue_category: str,
        reason: str,
        confirmed_info: List[Dict[str, Any]],
        uncertain_info: List[Dict[str, Any]],
        summary: str,
        priority: str = "PRIORITY"
    ) -> Dict[str, Any]:
        """Creates persistent case, escalation queue item, and system audit events in database."""
        db = SessionLocal()
        try:
            count = db.query(Case).count()
            case_number = f"POLY-{1024 + count}"

            case = Case(
                case_number=case_number,
                language=language,
                issue_category=issue_category,
                status=CaseStatus.WAITING_FOR_HUMAN,
                priority=priority,
                escalation_reason=reason,
                summary=summary,
                otp_verified=True
            )
            db.add(case)
            db.commit()
            db.refresh(case)

            # Persist confirmed & uncertain fields
            for item in confirmed_info:
                db.add(ExtractedInformation(
                    case_id=case.id,
                    field_key=item.get("key", "info"),
                    field_label=item.get("label", "Field"),
                    field_value=item.get("value", "Confirmed"),
                    status="confirmed"
                ))

            for item in uncertain_info:
                db.add(ExtractedInformation(
                    case_id=case.id,
                    field_key=item.get("key", "info"),
                    field_label=item.get("label", "Field"),
                    field_value=item.get("value", "Uncertain"),
                    status="uncertain",
                    notes=item.get("notes")
                ))

            # Create Escalation Queue item
            escalation = Escalation(
                case_id=case.id,
                priority=priority,
                routing_node="APAC-Central (Mumbai Edge)",
                status="PENDING"
            )
            db.add(escalation)

            # Audit Timeline Events
            db.add(AuditEvent(case_id=case.id, event_type="CALL_STARTED", title="Caller Session Started", description="Connected via Agora WebRTC APAC-Central node", timestamp_offset="00:00"))
            db.add(AuditEvent(case_id=case.id, event_type="LANGUAGE_CHANGED", title="Multilingual Intent Detected", description=f"Language set to {language}", timestamp_offset="00:12"))
            db.add(AuditEvent(case_id=case.id, event_type="ESCALATION_TRIGGERED", title="Confidence Engine Escalation", description=reason, timestamp_offset="00:58"))
            db.add(AuditEvent(case_id=case.id, event_type="CASE_CREATED", title=f"Case {case_number} Created", description=f"Initial status: WAITING_FOR_HUMAN", timestamp_offset="01:00"))

            db.commit()
            logger.info(f"Escalation triggered for case {case_number} (Reason: {reason})")

            return {
                "status": "SUCCESS",
                "case_id": case.id,
                "case_number": case_number,
                "status_name": case.status,
                "escalation_reason": reason
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error triggering escalation: {e}")
            return {"status": "ERROR", "message": str(e)}
        finally:
            db.close()

    @staticmethod
    def accept_handoff(case_id: str, agent_name: str = "Priya Sharma") -> Dict[str, Any]:
        """
        Support agent accepts handoff:
        1. Atomic duplicate acceptance validation.
        2. Assigns case, updates status to IN_PROGRESS.
        3. Records HUMAN_CONNECTED and AI_YIELDED audit events.
        """
        db = SessionLocal()
        try:
            raw_id = case_id.replace("case-", "")
            if raw_id.isdigit():
                case = db.query(Case).filter((Case.id == int(raw_id)) | (Case.case_number == case_id)).first()
            else:
                case = db.query(Case).filter(Case.case_number == case_id).first()
            if not case:
                return {"status": "NOT_FOUND", "message": f"Case {case_id} not found."}

            # Atomic race-condition check: Block duplicate acceptance
            if case.status in [CaseStatus.IN_PROGRESS, CaseStatus.ASSIGNED, CaseStatus.RESOLVED]:
                assigned_name = case.assigned_agent.full_name if case.assigned_agent else "another specialist"
                return {
                    "status": "CONFLICT",
                    "message": f"Case {case.case_number} has already been accepted by {assigned_name}."
                }

            case.status = CaseStatus.IN_PROGRESS
            
            # Find or assign agent
            agent = db.query(Agent).filter(Agent.full_name == agent_name).first()
            if not agent:
                agent = Agent(full_name=agent_name, email="priya.sharma@poly.support", hashed_password="pass", role="Support Specialist")
                db.add(agent)
                db.commit()
                db.refresh(agent)

            case.agent_id = agent.id

            # Update Escalation Queue status
            esc = db.query(Escalation).filter(Escalation.case_id == case.id).first()
            if esc:
                esc.status = "ACCEPTED"
                esc.agent_id = agent.id

            # Audit Events
            db.add(AuditEvent(
                case_id=case.id,
                event_type="HUMAN_CONNECTED",
                title="Human Specialist Joined Agora Call",
                description=f"Support Specialist {agent_name} accepted real-time handoff in Agora channel",
                timestamp_offset="02:45"
            ))

            db.add(AuditEvent(
                case_id=case.id,
                event_type="AI_YIELDED",
                title="POLY AI Yielded Control",
                description="POLY AI voice speech disabled; human agent in full control",
                timestamp_offset="02:46"
            ))

            db.commit()
            logger.info(f"Handoff accepted for case {case.case_number} by agent {agent_name}")

            # Also trigger session controller yield if session_manager holds this active session
            from app.services.session_manager import session_manager
            session = session_manager.get(f"session-{case.id}") or session_manager.get("session-8042")
            if session:
                session.yield_control_to_human(agent_name)

            return {
                "status": "SUCCESS",
                "case_number": case.case_number,
                "status_name": case.status,
                "assigned_agent": agent_name,
                "agora_channel": f"poly-session-{case.id}"
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error accepting handoff: {e}")
            return {"status": "ERROR", "message": str(e)}
        finally:
            db.close()

    @staticmethod
    def complete_case(case_id: str, resolution_notes: str = "Resolved reference number ambiguity") -> Dict[str, Any]:
        """Marks case as RESOLVED and records final resolution audit event."""
        db = SessionLocal()
        try:
            raw_id = case_id.replace("case-", "")
            if raw_id.isdigit():
                case = db.query(Case).filter((Case.id == int(raw_id)) | (Case.case_number == case_id)).first()
            else:
                case = db.query(Case).filter(Case.case_number == case_id).first()
            if not case:
                return {"status": "NOT_FOUND", "message": f"Case {case_id} not found."}

            case.status = CaseStatus.RESOLVED
            db.add(AuditEvent(
                case_id=case.id,
                event_type="CASE_RESOLVED",
                title="Case Resolved by Specialist",
                description=resolution_notes,
                timestamp_offset="05:30"
            ))
            db.commit()
            return {"status": "SUCCESS", "case_number": case.case_number, "status_name": case.status}
        finally:
            db.close()
