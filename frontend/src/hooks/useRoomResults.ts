import { useEffect, useRef, useState } from "react";
import type { ResultsPayload } from "../types";

const RAW_WS_BASE: string =
  import.meta.env.VITE_WS_BASE ??
  (import.meta.env.PROD
    ? "wss://pulse-stf8.onrender.com"
    : "ws://localhost:8080");

// Strip trailing slashes (fixes the double "//" in the URL)
let WS_BASE: string = RAW_WS_BASE;
while (WS_BASE.endsWith("/")) {
  WS_BASE = WS_BASE.slice(0, -1);
}

// Browsers block ws:// on HTTPS pages, so upgrade it to wss://
if (window.location.protocol === "https:" && WS_BASE.startsWith("ws://")) {
  WS_BASE = "wss://" + WS_BASE.slice("ws://".length);
}

/**
 * Subscribes to a poll's room over WebSocket and keeps results
 * in sync with every broadcast the server sends.
 */
export function useRoomResults(
  code: string | undefined,
  initial?: ResultsPayload
) {
  const [results, setResults] = useState<ResultsPayload | undefined>(initial);
  const [connected, setConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  // Sync results whenever the initial REST fetch resolves or changes.
  useEffect(() => {
    if (initial) {
      setResults(initial);
    }
  }, [initial]);

  useEffect(() => {
    if (!code) {
      setConnected(false);
      return;
    }

    const socket = new WebSocket(`${WS_BASE}/ws/room/${code}`);
    socketRef.current = socket;

    socket.onopen = () => {
      setConnected(true);
    };

    socket.onclose = () => {
      setConnected(false);
      if (socketRef.current === socket) {
        socketRef.current = null;
      }
    };

    socket.onerror = () => {
      setConnected(false);
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as ResultsPayload;

        if (payload.type === "results") {
          setResults(payload);
        }
      } catch {
        // Ignore malformed WebSocket messages.
      }
    };

    return () => {
      socket.close();

      if (socketRef.current === socket) {
        socketRef.current = null;
      }
    };
  }, [code]);

  return { results, connected };
}
