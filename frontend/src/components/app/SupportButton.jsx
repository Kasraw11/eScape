"use client";

import { useEffect, useRef, useState } from "react";
import SupportPanel from "./SupportPanel.jsx";

export default function SupportButton({ onEmergency, returnFocusRef }) {
  const [open, setOpen] = useState(false);
  const internalButtonRef = useRef(null);
  const buttonRef = returnFocusRef || internalButtonRef;
  useEffect(() => {
    const openSupport = () => setOpen(true);
    window.addEventListener("escape:open-support", openSupport);
    return () => window.removeEventListener("escape:open-support", openSupport);
  }, []);
  return <><button className="support-button" type="button" aria-label="Open support" onClick={() => setOpen(true)} ref={buttonRef}><span aria-hidden="true">?</span><span>Support</span></button><SupportPanel open={open} onClose={() => setOpen(false)} returnFocusRef={buttonRef} onEmergency={() => { setOpen(false); onEmergency?.(); }} /></>;
}
