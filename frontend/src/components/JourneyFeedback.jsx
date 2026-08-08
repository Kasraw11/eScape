"use client";

import { useState } from "react";
import { submitJourneyFeedback } from "../services/api.js";
import AccessibleDialog from "./AccessibleDialog.jsx";
import FeedbackRatingControl from "./FeedbackRatingControl.jsx";

export default function JourneyFeedback({ open, journey, onClose, returnFocusRef }) {
  const [sensoryRating, setSensoryRating] = useState(3);
  const [crowdRating, setCrowdRating] = useState(3);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState("");

  async function submit(event) {
    event.preventDefault();
    setSubmitting(true);
    setResult("");
    try {
      await submitJourneyFeedback({ route_id: journey?.route?.route_id, sensory_rating: sensoryRating, crowd_rating: crowdRating, comments: comment.trim() || null });
      setResult("Thank you. Your feedback was submitted.");
      window.setTimeout(onClose, 600);
    } catch {
      setResult("Feedback could not be sent. You can skip and continue.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AccessibleDialog open={open} onClose={onClose} titleId="feedback-title" className="feedback-dialog" returnFocusRef={returnFocusRef}>
      <header className="dialog-heading"><div><p className="section-kicker">Journey complete</p><h2 id="feedback-title">How was your journey?</h2></div><button type="button" className="dialog-close" onClick={onClose} aria-label="Close journey feedback">×</button></header>
      <form onSubmit={submit}>
        <FeedbackRatingControl label="Sensory comfort" value={sensoryRating} onChange={setSensoryRating} />
        <FeedbackRatingControl label="Crowd comfort" value={crowdRating} onChange={setCrowdRating} />
        <label className="feedback-comment">Optional comment<textarea value={comment} onChange={(event) => setComment(event.target.value)} maxLength={500} rows={3} /></label>
        <p className="feedback-result" aria-live="polite">{result}</p>
        <div className="dialog-actions"><button type="button" className="secondary-button" onClick={onClose}>Skip</button><button type="submit" className="primary-button" disabled={submitting}>{submitting ? "Submitting…" : "Submit feedback"}</button></div>
      </form>
    </AccessibleDialog>
  );
}
