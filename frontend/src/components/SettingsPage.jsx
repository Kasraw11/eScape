"use client";

import { useEffect, useState } from "react";

const defaults = { reducedMotion: false, contrast: false, largerText: false, simplifiedMap: false, soundAlerts: false };

export default function SettingsPage() {
  const [accessibility, setAccessibility] = useState(defaults);
  useEffect(() => {
    document.documentElement.classList.toggle("increased-contrast", accessibility.contrast);
    document.documentElement.classList.toggle("larger-text", accessibility.largerText);
    document.documentElement.classList.toggle("reduce-motion", accessibility.reducedMotion);
    return () => document.documentElement.classList.remove("increased-contrast", "larger-text", "reduce-motion");
  }, [accessibility]);
  const toggle = (key) => setAccessibility((current) => ({ ...current, [key]: !current[key] }));
  return <div className="settings-page page-stack"><header className="page-heading"><p className="section-kicker">Your experience</p><h1>Settings</h1><p>These preferences are stored only for this browser session and are not permanently saved.</p></header>
    <section className="settings-card"><h2>Sensory preferences</h2><label>Crowd tolerance<select defaultValue="3"><option value="1">Very low</option><option value="2">Low</option><option value="3">Moderate</option><option value="4">Higher</option><option value="5">Highest</option></select></label><label>Refuge search radius<select defaultValue="1000"><option value="500">500 m</option><option value="1000">1 km</option><option value="2000">2 km</option></select></label><label>Route preference<select defaultValue="calmer"><option value="calmer">Calmer routes</option><option value="balanced">Balanced</option><option value="fastest">Fastest</option></select></label></section>
    <section className="settings-card"><h2>Journey preferences</h2><label>Preferred travel mode<select defaultValue="walking"><option value="walking">Walking</option><option value="transit">Public transport</option></select></label><label>Maximum additional travel time<select defaultValue="10"><option value="5">5 minutes</option><option value="10">10 minutes</option><option value="20">20 minutes</option></select></label></section>
    <section className="settings-card"><h2>Notifications</h2><label className="checkbox-control"><input type="checkbox" defaultChecked />Enable predictive alerts</label><label>Minimum alert severity<select defaultValue="high"><option>Low</option><option>Moderate</option><option>High</option></select></label><label className="checkbox-control"><input type="checkbox" defaultChecked />Route change warnings</label></section>
    <section className="settings-card"><h2>Accessibility</h2>{Object.entries({ reducedMotion: "Reduced motion", contrast: "Increased contrast", largerText: "Larger text", simplifiedMap: "Simplified map", soundAlerts: "Sound alerts" }).map(([key, label]) => <label className="checkbox-control" key={key}><input type="checkbox" checked={accessibility[key]} onChange={() => toggle(key)} />{label}</label>)}</section>
    <section className="settings-card settings-card--danger"><h2>Privacy</h2><p>Trip and preference information stays in temporary browser state unless a future backend persistence feature is added.</p><button type="button">Clear trip history</button><button type="button">Clear saved preferences</button></section>
  </div>;
}
