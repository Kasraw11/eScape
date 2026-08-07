"use client";

import { useRef, useState } from "react";
import SupportPanel from "./SupportPanel.jsx";

export default function SupportButton({ onEmergency }) {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef(null);
  return <><button className="support-button" type="button" aria-label="Open support" onClick={() => setOpen(true)} ref={buttonRef}><span aria-hidden="true">?</span><span>Support</span></button><SupportPanel open={open} onClose={() => setOpen(false)} returnFocusRef={buttonRef} onEmergency={() => { setOpen(false); onEmergency?.(); }} /></>;
}
