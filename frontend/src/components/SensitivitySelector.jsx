import AppIcon from "./app/AppIcon.jsx";

const LEVELS = ["low", "medium", "high"];

export default function SensitivitySelector({ id, icon, label, description, guidance, value, onChange, accent = "blue" }) {
  return (
    <section className={`sensitivity-row sensitivity-row--${accent}`} aria-labelledby={`${id}-label`}>
      <span className="sensitivity-row__icon"><AppIcon name={icon} size={25} /></span>
      <div className="sensitivity-row__copy">
        <h3 id={`${id}-label`}>{label}</h3>
        <p>{description}</p>
      </div>
      <fieldset className="sensitivity-control" aria-labelledby={`${id}-label`}>
        <legend className="sr-only">{label}</legend>
        {LEVELS.map((level) => (
          <button key={level} type="button" aria-pressed={value === level} onClick={() => onChange(level)}>
            {level[0].toUpperCase() + level.slice(1)}
          </button>
        ))}
      </fieldset>
      <p className="sensitivity-row__guidance">{guidance}</p>
    </section>
  );
}
