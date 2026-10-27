import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";

const EXPIRY_CHOICES = [
  { label: "5 minutes", value: 5 },
  { label: "15 minutes", value: 15 },
  { label: "30 minutes", value: 30 },
];

export function CreatePoll() {
  const [question, setQuestion] = useState("");
  const [options, setOptions] = useState(["", ""]);
  const [expiresInMinutes, setExpiresInMinutes] = useState(15);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const updateOption = (i: number, value: string) => {
    setOptions((prev) => prev.map((o, idx) => (idx === i ? value : o)));
  };

  const addOption = () => {
    if (options.length < 4) setOptions((prev) => [...prev, ""]);
  };

  const removeOption = (i: number) => {
    if (options.length > 2) setOptions((prev) => prev.filter((_, idx) => idx !== i));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanOptions = options.map((o) => o.trim()).filter(Boolean);
    if (!question.trim()) {
      setError("Question cannot be empty");
      return;
    }
    if (cleanOptions.length < 2) {
      setError("Add at least 2 options");
      return;
    }

    setLoading(true);
    try {
      const poll = await api.createPoll(question.trim(), cleanOptions, expiresInMinutes);
      navigate(`/room/${poll.code}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create poll");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page page-center">
      <h1 className="page-title">Create a Poll</h1>
      <form className="create-form" onSubmit={handleSubmit}>
        <input
          className="text-input"
          placeholder="What's your question?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          maxLength={140}
        />

        <div className="options-list">
          {options.map((opt, i) => (
            <div key={i} className="option-row">
              <input
                className="text-input"
                placeholder={`Option ${i + 1}`}
                value={opt}
                onChange={(e) => updateOption(i, e.target.value)}
                maxLength={60}
              />
              {options.length > 2 && (
                <button
                  type="button"
                  className="btn-remove"
                  onClick={() => removeOption(i)}
                  aria-label="Remove option"
                >
                  ✕
                </button>
              )}
            </div>
          ))}
        </div>

        {options.length < 4 && (
          <button type="button" className="btn btn-ghost" onClick={addOption}>
            + Add option
          </button>
        )}

        <div className="expiry-choices">
          {EXPIRY_CHOICES.map((choice) => (
            <button
              key={choice.value}
              type="button"
              className={`chip ${expiresInMinutes === choice.value ? "chip-active" : ""}`}
              onClick={() => setExpiresInMinutes(choice.value)}
            >
              {choice.label}
            </button>
          ))}
        </div>

        {error && <div className="form-error">{error}</div>}

        <button className="btn btn-primary btn-large" type="submit" disabled={loading}>
          {loading ? "Creating..." : "Create Poll"}
        </button>
      </form>
    </div>
  );
}
