import { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";

export function Home() {
  const [code, setCode] = useState("");
  const navigate = useNavigate();

  const handleJoin = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = code.trim();
    if (trimmed.length === 6) {
      navigate(`/join/${trimmed}`);
    }
  };

  return (
    <div className="page page-center">
      <div className="brand-block">
        <h1 className="brand-title">PULSE <span className="bolt">⚡</span></h1>
        <p className="brand-tagline">Ask. Vote. Watch.</p>
      </div>

      <form className="join-form" onSubmit={handleJoin}>
        <input
          className="code-input"
          placeholder="Enter room code"
          maxLength={6}
          inputMode="numeric"
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
        />
        <button className="btn btn-primary" type="submit" disabled={code.length !== 6}>
          Join Poll
        </button>
      </form>

      <div className="home-host-link">
        Hosting a poll? <Link to="/login">Log in</Link> or{" "}
        <Link to="/signup">create an account</Link>
      </div>
    </div>
  );
}
