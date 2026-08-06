const INDICATOR_LABELS = {
  low: "Low sensory impact",
  high: "High sensory impact",
  unavailable: "Sensory information unavailable",
};

function normalizeIndicator(indicator) {
  const normalized = (indicator || "unavailable").toLowerCase();
  if (normalized === "low") return "low";
  if (normalized === "high" || normalized === "medium") return "high";
  return "unavailable";
}

export default function SensoryIndicator({ indicator }) {
  const normalized = normalizeIndicator(indicator);
  const label = INDICATOR_LABELS[normalized];

  return (
    <span className={`sensory-indicator sensory-indicator--${normalized}`} aria-label={label}>
      <span className="sensory-indicator__mark" aria-hidden="true">{normalized === "low" ? "✓" : normalized === "high" ? "!" : "?"}</span>
      {label}
    </span>
  );
}
