import logging
from typing import Dict, Any
from app.database.session import SessionLocal
from app.models.all_models import Case, ExtractedInformation, CaseStatus

logger = logging.getLogger(__name__)

def get_case_context(case_number: str) -> Dict[str, Any]:
    """Retrieves full case context, summary, and confirmed fields from database."""
    db = SessionLocal()
    try:
        case = db.query(Case).filter(Case.case_number == case_number).first()
        if not case:
            return {"status": "NOT_FOUND", "message": f"Case {case_number} not found."}
        
        fields = db.query(ExtractedInformation).filter(ExtractedInformation.case_id == case.id).all()
        confirmed = [{"key": f.field_key, "value": f.field_value} for f in fields if f.status == "confirmed"]
        uncertain = [{"key": f.field_key, "value": f.field_value, "notes": f.notes} for f in fields if f.status == "uncertain"]

        return {
            "status": "SUCCESS",
            "case_number": case.case_number,
            "issue_category": case.issue_category,
            "language": case.language,
            "status_name": case.status,
            "summary": case.summary,
            "confirmed_info": confirmed,
            "uncertain_info": uncertain
        }
    finally:
        db.close()

def create_case(customer_name: str, issue_category: str, language: str = "Hindi + English") -> Dict[str, Any]:
    """Creates a new customer support ticket case in PostgreSQL/SQLite database."""
    db = SessionLocal()
    try:
        count = db.query(Case).count()
        case_number = f"POLY-{1024 + count}"
        new_case = Case(
            case_number=case_number,
            issue_category=issue_category,
            language=language,
            status=CaseStatus.WAITING_FOR_HUMAN,
            summary=f"Case created for {customer_name} regarding {issue_category}."
        )
        db.add(new_case)
        db.commit()
        db.refresh(new_case)

        return {
            "status": "SUCCESS",
            "case_number": new_case.case_number,
            "message": f"Case {new_case.case_number} created successfully."
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating case: {e}")
        return {"status": "ERROR", "message": str(e)}
    finally:
        db.close()

def escalate_to_human(case_number: str, reason: str) -> Dict[str, Any]:
    """Triggers human escalation for a case."""
    db = SessionLocal()
    try:
        case = db.query(Case).filter(Case.case_number == case_number).first()
        if case:
            case.status = CaseStatus.WAITING_FOR_HUMAN
            case.escalation_reason = reason
            db.commit()
            return {"status": "SUCCESS", "case_number": case_number, "message": f"Escalated case {case_number} to human specialist."}
        return {"status": "NOT_FOUND", "message": f"Case {case_number} not found."}
    finally:
        db.close()

AGENT_TOOLS_SCHEMA = [
    {
        "name": "get_case_context",
        "description": "Get complete context and confirmed details for a case number.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"case_number": {"type": "STRING", "description": "The case identifier e.g. POLY-1024"}},
            "required": ["case_number"]
        }
    },
    {
        "name": "create_case",
        "description": "Create a new support ticket case.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "customer_name": {"type": "STRING"},
                "issue_category": {"type": "STRING"},
                "language": {"type": "STRING"}
            },
            "required": ["customer_name", "issue_category"]
        }
    },
    {
        "name": "escalate_to_human",
        "description": "Escalate conversation to a human support specialist.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "case_number": {"type": "STRING"},
                "reason": {"type": "STRING"}
            },
            "required": ["case_number", "reason"]
        }
    }
]
