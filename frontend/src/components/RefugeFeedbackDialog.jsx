"use client";

import { useEffect, useState } from "react";

import { submitRefugeFeedback } from "../services/api.js";
import AccessibleDialog from "./AccessibleDialog.jsx";
import FeedbackRatingControl from "./FeedbackRatingControl.jsx";

const CROWDING = [
  ["low", "Low"],
  ["moderate", "Moderate"],
  ["high", "High"],
];
const COMFORT = [
  ["yes", "Yes"],
  ["somewhat", "Somewhat"],
  ["no", "No"],
];

function ChoiceGroup({ legend, options, value, onChange, disabled }) {
  return (
    <fieldset className="refuge-feedback-choices" disabled={disabled}>
      <legend>{legend}</legend>
      <div>
        {options.map(([optionValue, label]) => (
          <button key={optionValue} type="button" aria-pressed={value === optionValue} onClick={() => onChange(optionValue)}>
            {label}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

export default function RefugeFeedbackDialog({ open, refuge, onClose, onSubmitted, returnFocusRef }) {
  const [quietness, setQuietness] = useState(null);
  const [crowding, setCrowding] = useState("");
  const [comfort, setComfort] = useState("");
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setQuietness(null);
    setCrowding("");
    setComfort("");
    setComment("");
    setSubmitting(false);
    setError("");
  }, [open, refuge?.refuge_id]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!quietness || !crowding || !comfort) {
      setError("Choose a quietness rating, crowding level, and comfort level.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await submitRefugeFeedback(refuge.refuge_id, {
        quietness_score: quietness,
        crowding_level: crowding,
        comfort_level: comfort,
        comment: comment.trim() || null,
      });
      await onSubmitted?.();
    } catch (requestError) {
      setError(requestError.message || "Feedback could not be submitted. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AccessibleDialog open={open} onClose={onClose} titleId="refuge-feedback-title" className="refuge-feedback-dialog" returnFocusRef={returnFocusRef}>
      <header className="dialog-heading">
        <div><p className="section-kicker">Community feedback</p><h2 id="refuge-feedback-title">How was this refuge?</h2></div>
        <button type="button" className="dialog-close" onClick={onClose} aria-label="Close refuge feedback">×</button>
      </header>
      <p className="refuge-feedback-name">{refuge?.name}</p>
      <form onSubmit={handleSubmit} noValidate>
        <FeedbackRatingControl label="How quiet was it?" value={quietness} onChange={setQuietness} disabled={submitting} />
        <ChoiceGroup legend="Crowding" options={CROWDING} value={crowding} onChange={setCrowding} disabled={submitting} />
        <ChoiceGroup legend="Did you feel comfortable?" options={COMFORT} value={comfort} onChange={setComfort} disabled={submitting} />
        <label className="feedback-comment">
          Optional comment
          <textarea value={comment} onChange={(event) => setComment(event.target.value)} maxLength={300} rows={3} disabled={submitting} />
          <span>{300 - comment.length} characters remaining</span>
        </label>
        <p className="feedback-result error-state" role={error ? "alert" : undefined} aria-live="polite">{error}</p>
        <div className="dialog-actions">
          <button type="button" className="secondary-button" onClick={onClose} disabled={submitting}>Cancel</button>
          <button type="submit" className="primary-button" disabled={submitting}>{submitting ? "Submitting…" : "Submit feedback"}</button>
        </div>
      </form>
    </AccessibleDialog>
  );
}
