import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { useRoomResults } from "../hooks/useRoomResults";
import { ResultsPanel } from "../components/ResultsPanel";
import type { ResultsPayload } from "../types";

export function Room() {
  const { code = "" } = useParams();
  const [initial, setInitial] = useState<ResultsPayload | undefined>(undefined);
  const [notFound, setNotFound] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api
      .getResults(code)
      .then(setInitial)
      .catch(() => setNotFound(true));
  }, [code]);

  const { results } = useRoomResults(code, initial);

  const joinUrl = `${window.location.origin}/join/${code}`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(joinUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard API unavailable, silently ignore
    }
  };

  if (notFound) {
    return (
      <div className="page page-center">
        <p className="form-error">This room doesn't exist.</p>
      </div>
    );
  }

  return (
    <div className="page page-center">
      <div className="room-code-block">
        <p className="muted">ROOM CODE</p>
        <div className="room-code">{code}</div>
        <button className="btn btn-ghost" onClick={handleCopy}>
          {copied ? "Copied!" : `Copy join link`}
        </button>
        <p className="join-url">{joinUrl}</p>
      </div>

      {results ? (
        <ResultsPanel results={results} />
      ) : (
        <p className="muted">Loading results...</p>
      )}
    </div>
  );
}
