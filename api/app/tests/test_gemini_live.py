import pytest
import asyncio
from app.database.session import engine, Base
from app.services.gemini_live import GeminiLiveService, LIVE_MODEL_NAME
from app.services.agent_tools import get_case_context, create_case, escalate_to_human

# Create DB tables before tests run
Base.metadata.create_all(bind=engine)

def test_gemini_live_service_init():
    async def _run():
        service = GeminiLiveService(session_id="test-live-1")
        assert service.session_id == "test-live-1"
        assert service.model_name == LIVE_MODEL_NAME
    asyncio.run(_run())

def test_gemini_live_connect_and_events():
    async def _run():
        service = GeminiLiveService(session_id="test-live-2")
        connected = await service.connect()
        assert connected is True

        await service.send_text_prompt("Hello")

        events = []
        try:
            async with asyncio.timeout(5.0):
                async for evt in service.receive_events():
                    events.append(evt)
                    break
        except asyncio.TimeoutError:
            pass

        await service.close()
    asyncio.run(_run())

def test_agent_tools_create_and_get():
    result = create_case(customer_name="Aarav Patel", issue_category="Account Access", language="Hindi + English")
    assert result["status"] == "SUCCESS"
    assert "case_number" in result

    case_num = result["case_number"]
    ctx = get_case_context(case_num)
    assert ctx["status"] == "SUCCESS"
    assert ctx["issue_category"] == "Account Access"

def test_agent_tools_escalate():
    create_res = create_case(customer_name="Meera Sharma", issue_category="Billing", language="Hindi")
    case_num = create_res["case_number"]

    esc_res = escalate_to_human(case_num, reason="Conflicting details")
    assert esc_res["status"] == "SUCCESS"

    ctx = get_case_context(case_num)
    assert ctx["status_name"] == "WAITING_FOR_HUMAN"
