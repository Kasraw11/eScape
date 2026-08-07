const INDICATOR_LABELS = {
  low: "Low sensory impact",
  moderate: "Moderate sensory impact",
  high: "High sensory impact",
  unavailable: "Sensory information unavailable",
};

function normalizeIndicator(indicator) {
  const normalized = (indicator || "unavailable").toLowerCase();
  if (normalized === "low") return "low";
  if (normalized === "moderate" || normalized === "medium") return "moderate";
  if (normalized === "high") return "high";
  return "unavailable";
}

export default function SensoryIndicator({ indicator }) {
  const normalized = normalizeIndicator(indicator);
  const label = INDICATOR_LABELS[normalized];

  return (
    <span className={`sensory-indicator sensory-indicator--${normalized}`} aria-label={label}>
      <span className="sensory-indicator__mark" aria-hidden="true">{normalized === "low" ? "●" : normalized === "moderate" ? "◆" : normalized === "high" ? "!" : "?"}</span>
      {normalized === "unavailable" ? "Unavailable" : normalized.charAt(0).toUpperCase() + normalized.slice(1)}
    </span>
  );
}
