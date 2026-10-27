import { useEffect, useState } from "react";
import { api } from "../api/client";
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

const MAX_BACKOFF_MS = 15_000;

/** Keep whichever snapshot has more votes, so a slow REST response can
 *  never overwrite newer data that already arrived over the WebSocket. */
function newer(
  prev: ResultsPayload | undefined,
  next: ResultsPayload
): ResultsPayload {
  return !prev || next.totalVotes >= prev.totalVotes ? next : prev;
}

/**
 * Subscribes to a poll's room over WebSocket and keeps results in sync with
 * every broadcast the server sends. If the socket drops it reconnects with
 * backoff, and it re-fetches results on every (re)connect and whenever the
 * tab becomes visible again, so missed votes are never left stale.
 */
export function useRoomResults(
  code: string | undefined,
  initial?: ResultsPayload
) {
  const [results, setResults] = useState<ResultsPayload | undefined>(initial);
  const [connected, setConnected] = useState(false);

  // Sync results whenever the initial REST fetch resolves or changes.
  useEffect(() => {
    if (initial) {
      setResults((prev) => newer(prev, initial));
    }
  }, [initial]);

  useEffect(() => {
    if (!code) {
      setConnected(false);
      return;
    }

    let socket: WebSocket | null = null;
    let timer: number | undefined;
    let retry = 0;
    let disposed = false;

    // Pull the latest standings over REST (covers votes missed before the
    // socket opened, or while it was down).
    const resync = () => {
      api
        .getResults(code)
        .then((r) => {
          if (!disposed) setResults((prev) => newer(prev, r));
        })
        .catch(() => {
          // Ignore; the next broadcast or resync will catch up.
        });
    };

    const connect = () => {
      const ws = new WebSocket(`${WS_BASE}/ws/room/${code}`);
      socket = ws;

      ws.onopen = () => {
        retry = 0;
        setConnected(true);
        resync();
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as ResultsPayload;
          if (payload.type === "results") {
            setResults(payload);
          }
        } catch {
          // Ignore malformed WebSocket messages.
        }
      };

      ws.onerror = () => {
        // onclose always follows; it handles the reconnect.
        ws.close();
      };

      ws.onclose = () => {
        setConnected(false);
        if (disposed || socket !== ws) return;
        const delay = Math.min(1000 * 2 ** retry, MAX_BACKOFF_MS);
        retry += 1;
        timer = window.setTimeout(connect, delay);
      };
    };

    const onVisible = () => {
      if (document.visibilityState !== "visible") return;
      resync();
      // Browsers can silently kill sockets in background tabs.
      if (!socket || socket.readyState === WebSocket.CLOSED) {
        window.clearTimeout(timer);
        retry = 0;
        connect();
      }
    };

    connect();
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      disposed = true;
      window.clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisible);
      socket?.close();
      socket = null;
    };
  }, [code]);

  return { results, connected };
}
