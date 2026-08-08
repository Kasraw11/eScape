"use client";

import { useEffect, useRef } from "react";

const FOCUSABLE = "a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex='-1'])";

export default function AccessibleMapModal({ open, title, onClose, returnFocusRef, children }) {
  const dialogRef = useRef(null);
  const closeRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();
    function keydown(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = [...dialogRef.current.querySelectorAll(FOCUSABLE)];
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable.at(-1);
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", keydown);
    return () => {
      document.removeEventListener("keydown", keydown);
      document.body.style.overflow = previousOverflow;
      returnFocusRef?.current?.focus();
    };
  }, [onClose, open, returnFocusRef]);

  if (!open) return null;
  return (
    <div className="map-modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="map-modal point-map-modal" role="dialog" aria-modal="true" aria-labelledby="point-map-modal-title" ref={dialogRef} tabIndex={-1}>
        <header className="map-modal__header">
          <div><p className="section-kicker">Expanded view</p><h2 id="point-map-modal-title">{title}</h2></div>
          <button type="button" className="map-modal__close" onClick={onClose} ref={closeRef} aria-label="Close expanded map">×</button>
        </header>
        <div className="map-modal__canvas-wrap">{children}</div>
      </section>
    </div>
  );
}
