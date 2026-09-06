import time
import logging
try:
    from agora_token_builder import RtcTokenBuilder
except ImportError:
    RtcTokenBuilder = None

from app.core.config import settings

logger = logging.getLogger(__name__)

# Agora Role Enum: 1 = Publisher, 2 = Subscriber
ROLE_PUBLISHER = 1
ROLE_SUBSCRIBER = 2

def generate_agora_rtc_token(channel_name: str, uid: int = 0, role: int = ROLE_PUBLISHER, expire_seconds: int = 86400) -> dict:
    """
    Generates dynamic Agora RTC token based on official Agora SDK specifications.
    If AGORA_APP_ID or AGORA_APP_CERTIFICATE is not configured, returns a clear status.
    """
    app_id = settings.AGORA_APP_ID
    app_certificate = settings.AGORA_APP_CERTIFICATE

    if not app_id:
        return {
            "token": None,
            "channel_name": channel_name,
            "uid": uid,
            "app_id": None,
            "status": "MISSING_CREDENTIALS",
            "message": "AGORA_APP_ID environment variable is not configured. Please add AGORA_APP_ID to your .env file."
        }

    # Privilege expiration timestamp in seconds since epoch
    current_timestamp = int(time.time())
    privilege_expired_ts = current_timestamp + expire_seconds

    try:
        if app_certificate:
            token = RtcTokenBuilder.buildTokenWithUid(
                app_id,
                app_certificate,
                channel_name,
                uid,
                role,
                privilege_expired_ts
            )
        else:
            # Without certificate (Agora App ID in testing mode without certificate enabled)
            token = None

        return {
            "token": token,
            "channel_name": channel_name,
            "uid": uid,
            "app_id": app_id,
            "status": "SUCCESS" if token else "NO_CERTIFICATE_MODE",
            "message": "Agora RTC Token generated successfully" if token else "Agora App ID provided without Certificate (Testing Mode)"
        }
    except Exception as e:
        logger.error(f"Error generating Agora RTC Token: {e}")
        return {
            "token": None,
            "channel_name": channel_name,
            "uid": uid,
            "app_id": app_id,
            "status": "ERROR",
            "message": f"Failed to generate Agora RTC Token: {str(e)}"
        }
