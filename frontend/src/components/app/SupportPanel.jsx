"use client";

import { useState } from "react";
import AccessibleDialog from "../AccessibleDialog.jsx";

export default function SupportPanel({ open, onClose, returnFocusRef, onEmergency }) {
  const [section, setSection] = useState("");
  const contactUrl = process.env.NEXT_PUBLIC_SUPPORT_URL?.trim();

  return (
    <AccessibleDialog open={open} onClose={onClose} titleId="support-title" className="support-panel" returnFocusRef={returnFocusRef}>
      <header className="dialog-heading"><div><p className="section-kicker">Support</p><h2 id="support-title">How can we help?</h2></div><button type="button" className="dialog-close" onClick={onClose} aria-label="Close support">×</button></header>
      <div className="support-options">
        <button type="button" onClick={() => setSection("help")}>View help</button>
        <button type="button" onClick={() => setSection("report")}>Report a problem</button>
        {contactUrl ? <a href={contactUrl}>Contact support</a> : <button type="button" onClick={() => setSection("contact")}>Contact support</button>}
      </div>
      <div className="support-detail" aria-live="polite">
        {section === "help" ? <p>Plan a route, select it, then choose Start Trip. Maps and crowd information show an unavailable label when live services cannot be reached.</p> : null}
        {section === "report" ? <p>A report service is not configured. Note what happened and use the configured support link when available.</p> : null}
        {section === "contact" ? <p>No support contact link is configured for this environment.</p> : null}
      </div>
      <div className="emergency-note"><strong>Need immediate assistance?</strong><p>Emergency support is separate from general help.</p><button type="button" onClick={onEmergency}>Open emergency assistance</button></div>
    </AccessibleDialog>
  );
}
