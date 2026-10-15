import { useEffect, useRef, useState } from "react"; import type { ResultsPayload } from "../types";

const RAWWSBASE = import.meta.env.VITEWSBASE ?? (import.meta.env.PROD ? "wss://pulse-stf8.onrender.com" : "ws://localhost:8080");

const WSBASE = RAWWS_BASE.replace(//+$/, "");

/

Subscribes to a poll's room over WebSocket and keeps results
in sync with every broadcast the server sends.

*/ export function useRoomResults( code: string | undefined, initial?: ResultsPayload ) { const [results, setResults] = useState<ResultsPayload | undefined>(initial); const [connected, setConnected] = useState(false); const socketRef = useRef<WebSocket | null>(null);

// Sync results whenever the initial REST fetch resolves or changes. useEffect(() => { if (initial) { setResults(initial); } }, [initial]);

useEffect(() => { if (!code) { setConnected(false); return; }

const socket = new WebSocket(${WS_BASE}/ws/room/${code}); socketRef.current = socket;

socket.onopen = () => { setConnected(true); };

socket.onclose = () => { setConnected(false); if (socketRef.current === socket) { socketRef.current = null; } };

socket.onerror = () => { setConnected(false); };

socket.onmessage = (event) => { try { const payload = JSON.parse(event.data) as ResultsPayload;

if (payload.type === "results") { setResults(payload); } } catch { // Ignore malformed WebSocket messages. } };

return () => { socket.close();

if (socketRef.current === socket) { socketRef.current = null; } }; }, [code]);

return { results, connected }; }
