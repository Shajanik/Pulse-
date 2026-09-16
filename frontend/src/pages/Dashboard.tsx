import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { PollSummary } from "../types";

export function Dashboard() {
  const [polls, setPolls] = useState<PollSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { email, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    api
      .myPolls()
      .then(setPolls)
      .catch(() => setError("Failed to load your polls"));
  }, []);

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const isActive = (expiresAt: string) => new Date(expiresAt).getTime() > Date.now();

  return (
    <div className="page">
      <div className="dashboard-header">
        <div>
          <h1 className="page-title">Your Polls</h1>
          <p className="dashboard-email">{email}</p>
        </div>
        <div className="dashboard-actions">
          <Link className="btn btn-primary" to="/create">
            + New Poll
          </Link>
          <button className="btn btn-ghost" onClick={handleLogout}>
            Log out
          </button>
        </div>
      </div>

      {error && <div className="form-error">{error}</div>}

      {!polls && !error && <p className="muted">Loading...</p>}

      {polls && polls.length === 0 && (
        <div className="empty-state">
          <p>You haven't created any polls yet.</p>
          <Link className="btn btn-primary" to="/create">
            Create your first poll
          </Link>
        </div>
      )}

      <div className="poll-list">
        {polls?.map((poll) => (
          <Link key={poll.id} to={`/room/${poll.code}`} className="poll-card">
            <div className="poll-card-top">
              <span className="poll-code">{poll.code}</span>
              <span className={`badge ${isActive(poll.expiresAt) ? "badge-live" : "badge-final"}`}>
                {isActive(poll.expiresAt) ? "LIVE" : "ENDED"}
              </span>
            </div>
            <p className="poll-question">{poll.question}</p>
            <p className="poll-options-count">{poll.options.length} options</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
