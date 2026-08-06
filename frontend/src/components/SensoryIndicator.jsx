const INDICATOR_LABELS = {
  low: "Low sensory load",
  high: "High sensory load",
  unavailable: "Sensory data unavailable",
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
      <span aria-hidden="true">{normalized === "low" ? "OK" : normalized === "high" ? "!!" : "?"}</span>
      {label}
    </span>
  );
}
