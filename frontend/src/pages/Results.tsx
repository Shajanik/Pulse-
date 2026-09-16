import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { useRoomResults } from "../hooks/useRoomResults";
import { ResultsPanel } from "../components/ResultsPanel";
import type { ResultsPayload } from "../types";

export function Results() {
  const { code = "" } = useParams();
  const [initial, setInitial] = useState<ResultsPayload | undefined>(undefined);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    api
      .getResults(code)
      .then(setInitial)
      .catch(() => setNotFound(true));
  }, [code]);

  const { results } = useRoomResults(code, initial);

  if (notFound) {
    return (
      <div className="page page-center">
        <p className="form-error">This room doesn't exist.</p>
      </div>
    );
  }

  return (
    <div className="page page-center">
      {results ? (
        <ResultsPanel results={results} />
      ) : (
        <p className="muted">Loading results...</p>
      )}
    </div>
  );
}
