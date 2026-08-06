"use client";

import { useEffect, useRef } from "react";

const FOCUSABLE = "a[href],button:not([disabled]),[tabindex]:not([tabindex='-1'])";

export default function SupportPanel({ open, onClose, returnFocusRef }) {
  const panelRef = useRef(null);
  const closeRef = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    closeRef.current?.focus();
    const onKeyDown = (event) => {
      if (event.key === "Escape") { event.preventDefault(); onClose(); return; }
      if (event.key !== "Tab" || !panelRef.current) return;
      const items = [...panelRef.current.querySelectorAll(FOCUSABLE)];
      if (!items.length) return;
      if (event.shiftKey && document.activeElement === items[0]) { event.preventDefault(); items.at(-1).focus(); }
      if (!event.shiftKey && document.activeElement === items.at(-1)) { event.preventDefault(); items[0].focus(); }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => { document.removeEventListener("keydown", onKeyDown); returnFocusRef.current?.focus(); };
  }, [onClose, open, returnFocusRef]);
  if (!open) return null;
  return (
    <div className="support-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="support-panel" role="dialog" aria-modal="true" aria-labelledby="support-title" ref={panelRef}>
        <div className="support-panel__heading"><div><p className="section-kicker">Support</p><h2 id="support-title">How can we help?</h2></div><button ref={closeRef} type="button" onClick={onClose} aria-label="Close support">×</button></div>
        <div className="support-options"><a href="#help">View help</a><a href="mailto:support@example.invalid?subject=eScape%20problem">Report a problem</a><a href="mailto:support@example.invalid">Contact support</a></div>
        <div className="emergency-note"><strong>Need immediate assistance?</strong><p>Contact the appropriate local emergency service. eScape provides access to support options but does not operate emergency services.</p></div>
      </section>
    </div>
  );
}
