const MODES = [
  { value: "walking", label: "Walking", symbol: "W" },
  { value: "transit", label: "Public transport", symbol: "PT" },
];

export default function TravelModeSelector({ value, onChange, disabled, error }) {
  return (
    <fieldset className="travel-mode" id="travel-mode" aria-describedby={error ? "travel-mode-error" : undefined}>
      <legend>Travel mode</legend>
      <div className="travel-mode__options">
        {MODES.map((mode) => (
          <button
            type="button"
            key={mode.value}
            className={value === mode.value ? "travel-mode__option travel-mode__option--selected" : "travel-mode__option"}
            onClick={() => onChange(mode.value)}
            aria-pressed={value === mode.value}
            disabled={disabled}
          >
            <span className="travel-mode__symbol" aria-hidden="true">{mode.symbol}</span>
            {mode.label}
          </button>
        ))}
      </div>
      {error ? <strong className="field-error" id="travel-mode-error">{error}</strong> : null}
    </fieldset>
  );
}
