"use client";

import { useRef, useState } from "react";
import { JourneyProvider } from "../../context/JourneyContext.jsx";
import EmergencyAssistance from "../EmergencyAssistance.jsx";
import AppHeader from "./AppHeader.jsx";
import MobileNavigation from "./MobileNavigation.jsx";
import SupportButton from "./SupportButton.jsx";

export default function AppShell({ children }) {
  const [emergencyOpen, setEmergencyOpen] = useState(false);
  const emergencyButtonRef = useRef(null);
  const openEmergency = () => setEmergencyOpen(true);
  return <JourneyProvider><div className="app-shell"><a className="skip-link" href="#main-content">Skip to content</a><AppHeader onEmergency={openEmergency} emergencyButtonRef={emergencyButtonRef} /><main className="app-main" id="main-content">{children}</main><footer className="site-footer"><p><strong>eScape</strong> · Sensory-aware navigation for Melbourne CBD</p><p>Check current travel conditions before you leave.</p></footer><SupportButton onEmergency={openEmergency} /><MobileNavigation /><EmergencyAssistance open={emergencyOpen} onClose={() => setEmergencyOpen(false)} returnFocusRef={emergencyButtonRef} /></div></JourneyProvider>;
}
