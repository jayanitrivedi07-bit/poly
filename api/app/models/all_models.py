import enum
import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum, Float
from sqlalchemy.orm import relationship
from app.database.session import Base

class CaseStatus(str, enum.Enum):
    WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"
    ASSIGNED = "ASSIGNED"
    CONNECTING_HUMAN = "CONNECTING_HUMAN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

class PriorityLevel(str, enum.Enum):
    PRIORITY = "PRIORITY"
    URGENT = "URGENT"
    HIGH = "HIGH"
    NORMAL = "NORMAL"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    phone_number = Column(String(50), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    location = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    cases = relationship("Case", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")

class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(100), default="Support Specialist")
    is_online = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    cases = relationship("Case", back_populates="assigned_agent")
    escalations = relationship("Escalation", back_populates="assigned_agent")

class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    case_number = Column(String(50), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    language = Column(String(100), default="Hindi + English")
    issue_category = Column(String(255), nullable=False)
    status = Column(String(50), default="WAITING_FOR_HUMAN")
    priority = Column(String(50), default="PRIORITY")
    escalation_reason = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    otp_verified = Column(Boolean, default=True)
    call_duration_seconds = Column(Integer, default=165)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))

    user = relationship("User", back_populates="cases")
    assigned_agent = relationship("Agent", back_populates="cases")
    conversations = relationship("Conversation", back_populates="case")
    extracted_fields = relationship("ExtractedInformation", back_populates="case")
    escalations = relationship("Escalation", back_populates="case")
    audit_events = relationship("AuditEvent", back_populates="case")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True, nullable=False)
    agora_channel_name = Column(String(100), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    call_duration_seconds = Column(Integer, default=0)
    language_mode = Column(String(100), default="Hindi + English")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    user = relationship("User", back_populates="conversations")
    case = relationship("Case", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    speaker = Column(String(50), nullable=False) # 'poly', 'caller', 'agent', 'system'
    speaker_name = Column(String(100), nullable=False)
    timestamp_offset = Column(String(20), nullable=False)
    original_text = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=True)
    language_detected = Column(String(50), nullable=True)
    confidence_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    conversation = relationship("Conversation", back_populates="messages")

class ExtractedInformation(Base):
    __tablename__ = "extracted_information"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    field_key = Column(String(100), nullable=False)
    field_label = Column(String(255), nullable=False)
    field_value = Column(String(255), nullable=False)
    status = Column(String(50), default="confirmed") # 'confirmed', 'needs_confirmation', 'uncertain'
    notes = Column(Text, nullable=True)

    case = relationship("Case", back_populates="extracted_fields")

class Escalation(Base):
    __tablename__ = "escalations"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    priority = Column(String(50), default="PRIORITY")
    waiting_time_seconds = Column(Integer, default=0)
    routing_node = Column(String(100), default="APAC-Central (Mumbai Edge)")
    status = Column(String(50), default="PENDING") # 'PENDING', 'ACCEPTED', 'COMPLETED'
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    case = relationship("Case", back_populates="escalations")
    assigned_agent = relationship("Agent", back_populates="escalations")

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    event_type = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    timestamp_offset = Column(String(20), default="00:00")
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    case = relationship("Case", back_populates="audit_events")
