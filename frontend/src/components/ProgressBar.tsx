interface ProgressBarProps {
  label: string;
  votes: number;
  percentage: number;
  colorIndex: number;
}

const COLORS = ["#ff5cad", "#5ce1ff", "#ffd23f", "#7bff8f"];

export function ProgressBar({ label, votes, percentage, colorIndex }: ProgressBarProps) {
  const color = COLORS[colorIndex % COLORS.length];
  return (
    <div className="progress-row">
      <div className="progress-row-top">
        <span className="progress-label">{label}</span>
        <span className="progress-stats">
          {percentage.toFixed(0)}% &middot; {votes} vote{votes === 1 ? "" : "s"}
        </span>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${percentage}%`, background: color }} />
      </div>
    </div>
  );
}
