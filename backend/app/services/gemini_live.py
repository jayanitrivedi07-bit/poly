import asyncio
import base64
import json
import logging
from typing import Dict, Any, AsyncGenerator, Optional, Callable
from app.core.config import settings
from app.agents.poly_agent import POLY_SYSTEM_INSTRUCTION

logger = logging.getLogger(__name__)

# Target Model for Gemini Live Preview
LIVE_MODEL_NAME = "gemini-2.0-flash-live-001"

class GeminiLiveService:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = LIVE_MODEL_NAME
        self.client = None
        self.live_session = None
        self.is_connected = False
        self.is_speaking = False
        self.current_transcript_input = ""
        self.current_transcript_output = ""

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize GenAI Live client: {e}")

    async def connect(self, tool_declarations: Optional[list] = None) -> bool:
        """
        Establishes real-time Live WebSocket connection with Gemini Live API.
        """
        if not self.client:
            logger.info(f"Gemini Live Service for session '{self.session_id}' running in simulated audio mode (No API Key).")
            self.is_connected = True
            return True

        try:
            from google.genai import types
            
            # Configure Live Session
            config = types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")
                    )
                ),
                system_instruction=types.Content(
                    parts=[types.Part.from_text(text=POLY_SYSTEM_INSTRUCTION)]
                )
            )

            # Connect via async Live SDK context manager
            self.live_context = self.client.aio.live.connect(
                model=self.model_name,
                config=config
            )
            self.live_session = await self.live_context.__aenter__()
            self.is_connected = True
            logger.info(f"Connected to Gemini Live ({self.model_name}) for session {self.session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Gemini Live model {self.model_name}: {e}")
            self.is_connected = False
            return False

    async def send_pcm_audio(self, pcm_data: bytes, sample_rate: int = 16000):
        """
        Sends raw PCM 16-bit 16kHz audio input chunk to Gemini Live Session.
        """
        if self.live_session and self.is_connected:
            try:
                from google.genai import types
                logger.info(f"[OBSERVABILITY - VOICE] MIC AUDIO (16kHz PCM, {len(pcm_data)} bytes) -> GEMINI LIVE ({self.model_name})")
                await self.live_session.send(
                    input=types.LiveClientRealtimeInput(
                        media_chunks=[
                            types.Blob(
                                data=pcm_data,
                                mime_type=f"audio/pcm;rate={sample_rate}"
                            )
                        ]
                    )
                )
            except Exception as e:
                logger.error(f"Error sending audio chunk to Gemini Live: {e}")

    async def send_text_prompt(self, text: str):
        """
        Sends real-time text turn to Gemini Live Session.
        """
        if self.live_session and self.is_connected:
            try:
                from google.genai import types
                logger.info(f"[OBSERVABILITY - VOICE] TEXT PROMPT -> GEMINI LIVE ({self.model_name}): \"{text}\"")
                await self.live_session.send(
                    input=types.LiveClientContent(
                        turns=[
                            types.Content(
                                role="user",
                                parts=[types.Part.from_text(text=text)]
                            )
                        ],
                        turn_complete=True
                    )
                )
            except Exception as e:
                logger.error(f"Error sending text turn to Gemini Live: {e}")

    async def receive_events(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Yields real-time events from Gemini Live session:
        - audio_output (24kHz PCM)
        - text_transcript_input (Caller speech transcription)
        - text_transcript_output (Poly speech transcription)
        - turn_complete
        - interrupted
        - tool_call
        """
        if not self.live_session or not self.is_connected:
            # Yield simulated event for local testing mode
            yield {
                "event": "simulated_audio",
                "text": "Gemini Live initialized in local session mode."
            }
            return

        try:
            async for response in self.live_session.receive():
                server_content = response.server_content
                if server_content is None:
                    continue

                model_turn = server_content.model_turn
                if model_turn:
                    for part in model_turn.parts:
                        has_text = bool(part.text)
                        has_audio = bool(part.inline_data)
                        audio_len = len(part.inline_data.data) if part.inline_data else 0
                        text_len = len(part.text or "")
                        
                        logger.info(
                            f"[GEMINI_RAW_STREAM] session={self.session_id} "
                            f"event_type='model_turn' has_text={has_text} text_len={text_len} "
                            f"has_audio={has_audio} audio_bytes={audio_len} "
                            f"turn_complete={bool(server_content.turn_complete)} "
                            f"interrupted={bool(server_content.interrupted)}"
                        )

                        # 1. Real Audio Output (PCM 24kHz)
                        if part.inline_data:
                            self.is_speaking = True
                            logger.info(f"[OBSERVABILITY - VOICE] GEMINI LIVE -> AI AUDIO ({audio_len} bytes 24kHz PCM) -> PLAYBACK")
                            yield {
                                "event": "audio_output",
                                "pcm_bytes": part.inline_data.data,
                                "mime_type": part.inline_data.mime_type
                            }

                        # 2. Output Transcription Text
                        if part.text:
                            self.current_transcript_output += part.text
                            yield {
                                "event": "output_transcript_chunk",
                                "text": part.text,
                                "accumulated_text": self.current_transcript_output
                            }

                # 3. Interruption Event (Caller spoke while Poly was speaking)
                if server_content.interrupted:
                    self.is_speaking = False
                    logger.info("[OBSERVABILITY - VOICE] INTERRUPT DETECTED -> GEMINI LIVE BARGE-IN")
                    yield {
                        "event": "interrupted",
                        "reason": "Caller barge-in detected"
                    }

                # 4. Turn Complete Event
                if server_content.turn_complete:
                    self.is_speaking = False
                    completed_output = self.current_transcript_output
                    self.current_transcript_output = ""
                    logger.info(f"[OBSERVABILITY - VOICE] TURN COMPLETE -> GEMINI_ASSEMBLED_TEXT: \"{completed_output}\"")
                    yield {
                        "event": "turn_complete",
                        "output_text": completed_output
                    }

        except Exception as e:
            logger.error(f"Error in Gemini Live receive loop: {e}")
            yield {
                "event": "error",
                "message": str(e)
            }

    async def close(self):
        """Cleanly closes Gemini Live session."""
        if hasattr(self, 'live_context') and self.live_context:
            try:
                await self.live_context.__aexit__(None, None, None)
                logger.info(f"Gemini Live session {self.session_id} closed cleanly.")
            except Exception as e:
                logger.error(f"Error closing Gemini Live session: {e}")
        elif self.live_session:
            try:
                await self.live_session.close()
                logger.info(f"Gemini Live session {self.session_id} closed cleanly.")
            except Exception as e:
                logger.error(f"Error closing Gemini Live session: {e}")
        self.is_connected = False
