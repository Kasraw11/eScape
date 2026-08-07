export default function RefugeFeedbackSummary({ summary, loading, error, onLeaveFeedback, leaveFeedbackRef }) {
  const count = summary?.response_count || 0;

  return (
    <section className="refuge-feedback-summary" aria-labelledby="community-feedback-heading">
      <div className="refuge-feedback-summary__heading">
        <div>
          <p className="section-kicker">Shared anonymously</p>
          <h3 id="community-feedback-heading">Community feedback</h3>
        </div>
        {count > 0 ? (
          <div className="refuge-feedback-score" aria-label={`${summary.average_quietness} out of 5 from ${count} responses`}>
            <strong><span aria-hidden="true">★</span> {summary.average_quietness}</strong>
            <span>{count} {count === 1 ? "response" : "responses"}</span>
          </div>
        ) : null}
      </div>

      {loading ? <p role="status">Loading community feedback…</p> : null}
      {!loading && error ? <p className="refuge-feedback-unavailable">Community feedback is temporarily unavailable.</p> : null}
      {!loading && !error && count === 0 ? (
        <div className="refuge-feedback-empty">
          <p><strong>No community feedback yet.</strong></p>
          <p>Be the first to share how this space felt.</p>
        </div>
      ) : null}
      {!loading && !error && count > 0 ? (
        <dl className="refuge-feedback-metrics">
          <div><dt>Quiet environment</dt><dd>{summary.quiet_percentage}%</dd></div>
          <div><dt>Comfortable</dt><dd>{summary.comfortable_percentage}%</dd></div>
          <div><dt>Low crowding</dt><dd>{summary.low_crowding_percentage}%</dd></div>
        </dl>
      ) : null}

      <button type="button" className="secondary-button refuge-feedback-trigger" onClick={onLeaveFeedback} ref={leaveFeedbackRef}>
        Leave feedback
      </button>
    </section>
  );
}
