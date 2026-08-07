"use client";

import { useEffect, useRef, useState } from "react";
import { useJourney } from "../context/JourneyContext.jsx";

const accessibilityDefaults = { reducedMotion: false, contrast: false, largerText: false, simplifiedMap: false, soundAlerts: false };
const SECTIONS = ["Sensory preferences", "Journey preferences", "Accessibility", "Notifications", "Privacy", "About"];

export default function SettingsPage() {
  const { endJourney } = useJourney();
  const [accessibility, setAccessibility] = useState(accessibilityDefaults);
  const [saved, setSaved] = useState("");
  const savedTimer = useRef(null);
  const markSaved = () => { setSaved("Changes saved"); window.clearTimeout(savedTimer.current); savedTimer.current = window.setTimeout(() => setSaved(""), 1800); };

  useEffect(() => () => window.clearTimeout(savedTimer.current), []);

  useEffect(() => {
    document.documentElement.classList.toggle("increased-contrast", accessibility.contrast);
    document.documentElement.classList.toggle("larger-text", accessibility.largerText);
    document.documentElement.classList.toggle("reduce-motion", accessibility.reducedMotion);
    return () => document.documentElement.classList.remove("increased-contrast", "larger-text", "reduce-motion");
  }, [accessibility]);

  function toggle(key) {
    setAccessibility((current) => ({ ...current, [key]: !current[key] }));
    markSaved();
  }

  return <div className="settings-page page-stack"><header className="page-heading"><p className="section-kicker">Your experience</p><h1>Settings</h1><p>Adjust how eScape presents routes and alerts. Changes are not permanently saved.</p><span className="settings-saved" role="status" aria-live="polite">{saved}</span></header>
    <div className="settings-layout">
      <nav className="settings-sidebar" aria-label="Settings sections">{SECTIONS.map((section) => <a key={section} href={`#settings-${section.toLowerCase().replaceAll(" ", "-")}`}>{section}</a>)}</nav>
      <div className="settings-content">
        <section className="settings-card" id="settings-sensory-preferences"><h2>Sensory preferences</h2><label>Crowd tolerance<select defaultValue="3" onChange={markSaved}><option value="1">Very low</option><option value="2">Low</option><option value="3">Moderate</option><option value="4">Higher</option><option value="5">Highest</option></select></label><label>Notification sensitivity<select defaultValue="important" onChange={markSaved}><option value="all">All changes</option><option value="important">Important changes</option><option value="high">High crowding only</option></select></label><label>Data freshness preference<select defaultValue="recent" onChange={markSaved}><option value="live">Live only</option><option value="recent">Live or recent</option><option value="any">Include historical estimates</option></select></label></section>
        <details className="settings-card settings-disclosure" id="settings-journey-preferences"><summary><h2>Journey preferences</h2><span>Optional</span></summary><label>Preferred travel mode<select defaultValue="walking" onChange={markSaved}><option value="walking">Walking</option><option value="transit">Public transport</option></select></label><label>Maximum additional travel time<select defaultValue="10" onChange={markSaved}><option value="5">5 minutes</option><option value="10">10 minutes</option><option value="20">20 minutes</option></select></label></details>
        <section className="settings-card" id="settings-accessibility"><h2>Accessibility</h2>{Object.entries({ reducedMotion: "Reduced motion", contrast: "Increased contrast", largerText: "Larger text", simplifiedMap: "Simplified map", soundAlerts: "Sound alerts" }).map(([key, label]) => <label className="checkbox-control" key={key}><input type="checkbox" checked={accessibility[key]} onChange={() => toggle(key)} />{label}</label>)}</section>
        <section className="settings-card" id="settings-notifications"><h2>Notifications</h2><label className="checkbox-control"><input type="checkbox" defaultChecked onChange={markSaved} />Enable predictive alerts</label><label>Minimum alert severity<select defaultValue="high" onChange={markSaved}><option>Low</option><option>Moderate</option><option>High</option></select></label><label className="checkbox-control"><input type="checkbox" defaultChecked onChange={markSaved} />Route change warnings</label></section>
        <section className="settings-card" id="settings-privacy"><h2>Privacy</h2><p>Trip and preference information stays in temporary browser state.</p><button type="button" onClick={() => { endJourney(); markSaved(); }}>Clear trip history</button><button type="button" onClick={() => { setAccessibility(accessibilityDefaults); markSaved(); }}>Clear saved preferences</button></section>
        <section className="settings-card" id="settings-about"><h2>About</h2><p>eScape compares sensory-aware routes using FastAPI, Google Maps and validated Melbourne data when available.</p><p>Version 0.1</p></section>
      </div>
    </div>
  </div>;
}
