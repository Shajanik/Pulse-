import type { ResultsPayload } from "../types";
import { ProgressBar } from "./ProgressBar";
import { LiveBadge } from "./LiveBadge";
import { CrowdPulse } from "./CrowdPulse";

export function ResultsPanel({ results }: { results: ResultsPayload }) {
  return (
    <div className="results-panel">
      <div className="results-header">
        <h2 className="results-question">{results.question}</h2>
        <LiveBadge live={results.status === "active"} />
      </div>

      <div className="results-bars">
        {results.options.map((opt, i) => (
          <ProgressBar
            key={opt.id}
            label={opt.text}
            votes={opt.votes}
            percentage={opt.percentage}
            colorIndex={i}
          />
        ))}
      </div>

      <div className="results-total">{results.totalVotes} total votes</div>

      <CrowdPulse message={results.crowdPulse} />
    </div>
  );
}
