import { useEffect, useRef, useState } from "react";
import type { ResultsPayload } from "../types";

const WS_BASE = import.meta.env.VITE_WS_BASE ?? "ws://localhost:8080";

/**
 * Subscribes to a poll's room over WebSocket and keeps `results` in sync
 * with every broadcast the server sends.
 */
export function useRoomResults(code: string | undefined, initial?: ResultsPayload) {
  const [results, setResults] = useState<ResultsPayload | undefined>(initial);
  const [connected, setConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  // Sync results whenever the initial REST fetch resolves/changes
  useEffect(() => {
    if (initial) {
      setResults(initial);
    }
  }, [initial]);

  useEffect(() => {
    if (!code) return;

    const socket = new WebSocket(`${WS_BASE}/ws/room/${code}`);
    socketRef.current = socket;

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onerror = () => setConnected(false);

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as ResultsPayload;
        if (payload.type === "results") {
          setResults(payload);
        }
      } catch {
        // ignore malformed frames
      }
    };

    return () => {
      socket.close();
      socketRef.current = null;
    };
  }, [code]);

  return { results, connected };
}
