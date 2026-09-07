import type {
  IAgoraRTCClient,
  IMicrophoneAudioTrack,
  ILocalAudioTrack,
  IRemoteAudioTrack,
  ConnectionState
} from 'agora-rtc-sdk-ng';
import { pcmAudioBridge } from './pcmAudioBridge';
import { API_BASE_URL } from './apiConfig';

export interface AgoraTokenBackendResponse {
  token: string | null;
  channel_name: string;
  uid: number;
  app_id: string | null;
  status: string;
  message: string;
}

export interface AgoraSessionCallbacks {
  onStateChange?: (state: ConnectionState | 'connecting' | 'connected' | 'listening' | 'speaking' | 'interrupted' | 'ended' | 'error') => void;
  onRemoteAudioTrack?: (track: IRemoteAudioTrack) => void;
  onError?: (err: string) => void;
  onTranscriptTurn?: (turn: { speaker: string; text: string; language?: string }) => void;
}

class AgoraService {
  private client: IAgoraRTCClient | null = null;
  private localMicTrack: IMicrophoneAudioTrack | null = null;
  private localAiTrack: ILocalAudioTrack | null = null;
  private isJoined: boolean = false;
  private isInitializing: boolean = false;
  private currentChannel: string | null = null;
  private activeInitPromise: Promise<boolean> | null = null;

  public async fetchToken(channelName: string): Promise<AgoraTokenBackendResponse> {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/agora/rtc-token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel_name: channelName, role: 1 })
      });
      if (!res.ok) {
        throw new Error(`Backend returned status ${res.status}`);
      }
      return await res.json();
    } catch (err: any) {
      console.warn('Failed to fetch Agora RTC token from backend:', err?.message || err);
      return {
        token: null,
        channel_name: channelName,
        uid: 0,
        app_id: (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_AGORA_APP_ID as string) || null,
        status: 'BACKEND_OFFLINE',
        message: 'Could not reach backend token endpoint.'
      };
    }
  }

  public async startSession(
    channelName: string,
    callbacks?: AgoraSessionCallbacks
  ): Promise<boolean> {
    if (this.isJoined && this.currentChannel === channelName && this.client) {
      console.log(`Agora session already connected to channel '${channelName}'. Skipping redundant init.`);
      callbacks?.onStateChange?.('connected');
      return true;
    }

    if (this.isInitializing && this.activeInitPromise) {
      console.debug('Agora session initialization in progress. Awaiting current initialization task...');
      return this.activeInitPromise;
    }

    this.isInitializing = true;
    this.activeInitPromise = this.internalStartSession(channelName, callbacks)
      .finally(() => {
        this.isInitializing = false;
        this.activeInitPromise = null;
      });

    return this.activeInitPromise;
  }

  private async internalStartSession(
    channelName: string,
    callbacks?: AgoraSessionCallbacks
  ): Promise<boolean> {
    try {
      callbacks?.onStateChange?.('connecting');

      // Stop any existing dirty session before initializing new client
      if (this.client || this.isJoined) {
        await this.stopSession();
      }

      const AgoraRTC = (await import('agora-rtc-sdk-ng')).default;

      // Disable excessive Agora internal verbose logs
      try {
        AgoraRTC.setLogLevel(3);
      } catch (e) {}

      // 1. Fetch token from FastAPI backend
      const tokenResult = await this.fetchToken(channelName);
      const appId = tokenResult.app_id || (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_AGORA_APP_ID as string) || '';

      if (!appId) {
        console.warn('AGORA_APP_ID is not configured. Running voice agent in local simulation mode.');
        callbacks?.onStateChange?.('listening');
        return true;
      }

      // 2. Initialize RTC client
      this.client = AgoraRTC.createClient({ mode: 'rtc', codec: 'vp8' });
      this.currentChannel = channelName;

      this.client.on('connection-state-change', (curState) => {
        console.log('Agora Connection State:', curState);
        if (curState === 'CONNECTED') {
          callbacks?.onStateChange?.('connected');
        } else if (curState === 'DISCONNECTED') {
          callbacks?.onStateChange?.('ended');
        }
      });

      this.client.on('user-published', async (user, mediaType) => {
        try {
          await this.client?.subscribe(user, mediaType);
          if (mediaType === 'audio') {
            const remoteTrack = user.audioTrack;
            remoteTrack?.play();
            if (remoteTrack) {
              callbacks?.onRemoteAudioTrack?.(remoteTrack);
            }
          }
        } catch (subErr) {
          console.warn('Agora subscribe error:', subErr);
        }
      });

      // 3. Join Channel
      try {
        const uid = await this.client.join(appId, channelName, tokenResult.token || null, null);
        this.isJoined = true;
        console.log(`Successfully joined Agora Channel '${channelName}' with UID: ${uid}`);

        // 4. Create local microphone track safely
        try {
          this.localMicTrack = await AgoraRTC.createMicrophoneAudioTrack({
            encoderConfig: 'speech_standard',
            AEC: true,
            ANS: true,
            AGC: true
          });
        } catch (micErr: any) {
          console.warn('Could not create microphone track (Permission or Device issue):', micErr?.message || micErr);
        }

        // Start PCM Audio Bridge capture for local voice pipeline
        try {
          await pcmAudioBridge.startMicCapture((_chunk) => {
            // PCM 16kHz audio chunk ready
          });
        } catch (pcmErr) {
          console.warn('PCM capture initialization error:', pcmErr);
        }

        // 5. Publish tracks if available
        const tracksToPublish = [];
        if (this.localMicTrack) tracksToPublish.push(this.localMicTrack);

        const mediaTrack = pcmAudioBridge.getMediaStreamTrack();
        if (mediaTrack) {
          try {
            this.localAiTrack = AgoraRTC.createCustomAudioTrack({ mediaStreamTrack: mediaTrack });
            tracksToPublish.push(this.localAiTrack);
          } catch (aiTrackErr) {
            console.warn('Could not create custom AI track:', aiTrackErr);
          }
        }

        if (tracksToPublish.length > 0 && this.isJoined && this.client) {
          await this.client.publish(tracksToPublish);
        }
      } catch (joinErr: any) {
        console.warn('Agora WebRTC channel join running in local fallback mode:', joinErr?.message || joinErr);
      }

      callbacks?.onStateChange?.('listening');
      return true;

    } catch (err: any) {
      const errMsg = typeof err === 'string' ? err : err?.message || 'Failed to start Agora session';
      console.error('Error in Agora startSession:', err);
      callbacks?.onError?.(errMsg);
      callbacks?.onStateChange?.('listening');
      return false;
    }
  }

  public async stopSession(): Promise<void> {
    try {
      if (this.localMicTrack) {
        try {
          this.localMicTrack.stop();
          this.localMicTrack.close();
        } catch (e) {}
        this.localMicTrack = null;
      }

      if (this.localAiTrack) {
        try {
          this.localAiTrack.stop();
          this.localAiTrack.close();
        } catch (e) {}
        this.localAiTrack = null;
      }

      if (this.client) {
        try {
          if (this.isJoined) {
            await this.client.leave();
          }
          this.client.removeAllListeners();
        } catch (e) {}
        this.client = null;
      }

      this.isJoined = false;
      this.currentChannel = null;
      pcmAudioBridge.stopAll();
      console.log('Agora WebRTC session stopped cleanly.');
    } catch (err) {
      console.error('Error stopping Agora session:', err);
    }
  }

  public setMicrophoneMuted(muted: boolean): void {
    if (this.localMicTrack) {
      try {
        this.localMicTrack.setEnabled(!muted);
        console.log(`Agora Microphone track setEnabled(${!muted})`);
      } catch (e) {
        console.warn('Could not set microphone track state:', e);
      }
    }
  }
}

export const agoraService = new AgoraService();

