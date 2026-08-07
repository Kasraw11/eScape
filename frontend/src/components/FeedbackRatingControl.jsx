const RATINGS = [1, 2, 3, 4, 5];

export default function FeedbackRatingControl({ label, value, onChange, disabled = false }) {
  return (
    <fieldset className="feedback-rating" disabled={disabled}>
      <legend>{label}</legend>
      <div>
        {RATINGS.map((rating) => (
          <button
            key={rating}
            type="button"
            aria-pressed={value === rating}
            aria-label={`${label}: ${rating} of 5`}
            onClick={() => onChange(rating)}
          >
            {rating}
          </button>
        ))}
      </div>
    </fieldset>
  );
}
