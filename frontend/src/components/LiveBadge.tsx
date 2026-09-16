export function LiveBadge({ live }: { live: boolean }) {
  if (!live) {
    return <span className="badge badge-final">FINAL</span>;
  }
  return (
    <span className="badge badge-live">
      <span className="dot" /> LIVE
    </span>
  );
}
