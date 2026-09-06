// Centralized API and WebSocket Base URL Configuration for Production & Development

export const API_BASE_URL: string =
  (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL)
    ? (import.meta.env.VITE_API_BASE_URL as string)
    : '';

export const WS_BASE_URL: string =
  (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_WS_BASE_URL)
    ? (import.meta.env.VITE_WS_BASE_URL as string)
    : (typeof window !== 'undefined' ? window.location.origin.replace(/^http/, 'ws') : 'ws://localhost:8000');

