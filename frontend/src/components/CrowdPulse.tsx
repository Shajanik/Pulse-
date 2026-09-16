export function CrowdPulse({ message }: { message: string }) {
  return (
    <div className="crowd-pulse">
      <span className="crowd-pulse-icon">⚡</span>
      <span>{message}</span>
    </div>
  );
}
