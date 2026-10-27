import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Option } from "../types";

type Stage = "loading" | "nickname" | "voting" | "submitting" | "error";

function votedKey(code: string) {
  return `pulse_voted_${code}`;
}

export function Join() {
  const { code = "" } = useParams();
  const navigate = useNavigate();

  const [stage, setStage] = useState<Stage>("loading");
  const [nickname, setNickname] = useState("");
  const [question, setQuestion] = useState("");
  const [options, setOptions] = useState<Option[]>([]);
  const [voterId, setVoterId] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Already voted in this room on this device? Skip straight to results.
    if (localStorage.getItem(votedKey(code))) {
      navigate(`/results/${code}`, { replace: true });
      return;
    }
    setStage("nickname");
  }, [code, navigate]);

  const handleNicknameSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!nickname.trim()) return;

    setStage("loading");
    setError(null);
    try {
      const res = await api.joinRoom(code, nickname.trim());
      setQuestion(res.question);
      setOptions(res.options);
      setVoterId(res.voterId);
      setStage("voting");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not join this room");
      setStage("error");
    }
  };

  const handleVote = async (optionId: string) => {
    setStage("submitting");
    setError(null);
    try {
      await api.castVote(code, optionId, voterId, nickname.trim());
      localStorage.setItem(votedKey(code), "true");
      navigate(`/results/${code}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to submit vote");
      setStage("voting");
    }
  };

  if (stage === "loading") {
    return (
      <div className="page page-center">
        <p className="muted">Loading...</p>
      </div>
    );
  }

  if (stage === "error") {
    return (
      <div className="page page-center">
        <p className="form-error">{error ?? "Something went wrong"}</p>
      </div>
    );
  }

  if (stage === "nickname") {
    return (
      <div className="page page-center">
        <h1 className="page-title">Joining room {code}</h1>
        <form className="auth-form" onSubmit={handleNicknameSubmit}>
          <input
            className="text-input"
            placeholder="Pick a nickname"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            maxLength={24}
            autoFocus
            required
          />
          <button className="btn btn-primary" type="submit">
            Join
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="page page-center">
      <h1 className="page-title vote-question">{question}</h1>
      <div className="vote-options">
        {options.map((opt) => (
          <button
            key={opt.id}
            className="btn btn-vote"
            disabled={stage === "submitting"}
            onClick={() => handleVote(opt.id)}
          >
            {opt.text}
          </button>
        ))}
      </div>
      {error && <div className="form-error">{error}</div>}
      {stage === "submitting" && <p className="muted">Submitting your vote...</p>}
    </div>
  );
}
