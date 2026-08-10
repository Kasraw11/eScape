const LEVELS = [
  {
    value: 1,
    label: "Quietest available (very low crowd tolerance)",
  },
  {
    value: 2,
    label: "Extra calm (low crowd tolerance)",
  },
  {
    value: 3,
    label: "Calmer route (moderate crowd tolerance)",
  },
  {
    value: 4,
    label: "Flexible route (higher crowd tolerance)",
  },
  {
    value: 5,
    label: "Most direct options (highest crowd tolerance)",
  },
];


export default function CrowdToleranceSelector({
  value,
  onChange,
  disabled,
  error,
}) {
  return (
    <label
      className="route-preference"
      htmlFor="route-preference"
      aria-describedby={
        error ? "crowd-tolerance-error" : undefined
      }
    >
      <span>Route preference</span>

      <select
        id="route-preference"
        value={value ?? ""}
        disabled={disabled}
        onChange={(event) => {
          const selectedValue = event.target.value;

          onChange(
            selectedValue
              ? Number(selectedValue)
              : null
          );
        }}
      >
        <option value="" disabled>
          Select your crowd tolerance
        </option>

        {LEVELS.map((level) => (
          <option
            key={level.value}
            value={level.value}
          >
            {level.label}
          </option>
        ))}
      </select>

      {error ? (
        <strong
          className="field-error"
          id="crowd-tolerance-error"
        >
          {error}
        </strong>
      ) : null}
    </label>
  );
}