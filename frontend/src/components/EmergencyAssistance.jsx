"use client";

import Link from "next/link";
import AccessibleDialog from "./AccessibleDialog.jsx";

export default function EmergencyAssistance({ open, onClose, returnFocusRef }) {
  const emergencyPhone = process.env.NEXT_PUBLIC_EMERGENCY_PHONE?.trim();
  const trustedContactPhone = process.env.NEXT_PUBLIC_TRUSTED_CONTACT_PHONE?.trim();

  return (
    <AccessibleDialog open={open} onClose={onClose} titleId="emergency-title" className="emergency-dialog" returnFocusRef={returnFocusRef}>
      <header className="dialog-heading">
        <div><p className="section-kicker">Immediate assistance</p><h2 id="emergency-title">Need immediate support?</h2></div>
        <button type="button" className="dialog-close" onClick={onClose} aria-label="Close emergency assistance">×</button>
      </header>
      <p>We can help you find a safe, quiet space or connect you with emergency services.</p>
      <div className="emergency-actions">
        <Link href="/refuges" onClick={onClose}>Nearest quiet space</Link>
        {emergencyPhone ? <a href={`tel:${emergencyPhone}`}>Call emergency services</a> : <button type="button" disabled title="No emergency contact is configured">Call emergency services</button>}
        {trustedContactPhone ? <a href={`tel:${trustedContactPhone}`}>Call trusted contact</a> : <button type="button" disabled title="No trusted contact is configured">Call trusted contact</button>}
        <Link href="/refuges" onClick={onClose}>Get directions</Link>
      </div>
      {(!emergencyPhone || !trustedContactPhone) ? <p className="configuration-note">Unavailable call actions have not been configured. eScape does not invent contact numbers.</p> : null}
      <p className="emergency-disclaimer">eScape provides access to support options but does not operate emergency services.</p>
    </AccessibleDialog>
  );
}
