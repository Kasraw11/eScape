export default function DataAvailabilityNotice({ availability, warning }) {
  const normalized = availability || "unavailable";
  const label =
    normalized === "available"
      ? "Pedestrian data available"
      : normalized === "partial"
        ? "Pedestrian data partially available"
        : "Pedestrian data unavailable";

  return (
    <div className={`availability availability--${normalized}`} role={warning ? "note" : undefined}>
      <strong>{label}</strong>
      {warning ? <p>{warning}</p> : null}
      {normalized === "unavailable" && !warning ? (
        <p>Congestion and sensory information cannot be fully confirmed for this route.</p>
      ) : null}
    </div>
  );
}
