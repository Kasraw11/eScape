"use client";

import { useEffect, useRef, useState } from "react";

import { useSettings } from "../context/SettingsContext.jsx";
import AppIcon from "./app/AppIcon.jsx";
import SensitivitySelector from "./SensitivitySelector.jsx";

const NAV_ITEMS = [
  { id: "preferences", label: "Preferences", description: "Sensory preferences", icon: "sliders" },
  { id: "notifications", label: "Notifications", description: "Alerts & updates", icon: "bell" },
  { id: "account", label: "Account", description: "Profile & security", icon: "user" },
  { id: "about", label: "About", description: "About eScape", icon: "info" },
  { id: "support", label: "Support", description: "Help & feedback", icon: "help" },
];

const SENSORY_SETTINGS = [
  {
    id: "crowding",
    icon: "crowd",
    label: "Crowding sensitivity",
    description: "How much crowding affects you.",
    guidance: "We'll avoid busy areas when possible.",
    accent: "green",
  },
  {
    id: "noise",
    icon: "volume",
    label: "Noise sensitivity",
    description: "How much noise affects you.",
    guidance: "We'll prefer quieter routes and spaces.",
    accent: "purple",
  },
  {
    id: "brightness",
    icon: "brightness",
    label: "Brightness sensitivity",
    description: "How much bright light affects you.",
    guidance: "We'll prefer shaded or low-glare routes.",
    accent: "amber",
  },
  {
    id: "odour",
    icon: "scent",
    label: "Smells / strong odours",
    description: "How much smells affect you.",
    guidance: "We'll avoid areas with strong odours.",
    accent: "blue",
  },
];

function SettingsToggle({ label, description, checked, onChange }) {
  return (
    <label className="settings-toggle-row">
      <span><strong>{label}</strong><small>{description}</small></span>
      <span className="settings-toggle">
        <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
        <span aria-hidden="true" />
      </span>
    </label>
  );
}

function CardHeading({ title, description }) {
  return <header className="settings-card-heading"><h2>{title}</h2><p>{description}</p></header>;
}

export default function SettingsPage() {
  const {
    sensoryPreferences,
    notificationPreferences,
    theme,
    setSensoryPreference,
    resetSensoryPreferences,
    setNotificationPreference,
    setTheme,
  } = useSettings();
  const [saved, setSaved] = useState("");
  const savedTimer = useRef(null);

  useEffect(() => () => window.clearTimeout(savedTimer.current), []);

  function markSaved(message = "Changes saved") {
    setSaved(message);
    window.clearTimeout(savedTimer.current);
    savedTimer.current = window.setTimeout(() => setSaved(""), 1800);
  }

  function updateSensory(key, level) {
    setSensoryPreference(key, level);
    markSaved();
  }

  function updateNotification(key, enabled) {
    setNotificationPreference(key, enabled);
    markSaved();
  }

  function chooseTheme(nextTheme) {
    setTheme(nextTheme);
    markSaved(nextTheme === "dark" ? "Dark theme applied" : "Light theme applied");
  }

  function openSupport() {
    window.dispatchEvent(new globalThis.Event("escape:open-support"));
  }

  return (
    <div className="settings-approved-page">
      <aside className="settings-navigation glass-panel">
        <h1>Settings</h1>
        <nav aria-label="Settings sections">
          {NAV_ITEMS.map((item, index) => (
            <a key={item.id} href={"#settings-" + item.id} className={index === 0 ? "settings-navigation__active" : ""} aria-current={index === 0 ? "location" : undefined}>
              <AppIcon name={item.icon} size={24} />
              <span><strong>{item.label}</strong><small>{item.description}</small></span>
            </a>
          ))}
        </nav>
        <div className="settings-navigation__note">
          <span><AppIcon name="leaf" size={25} /></span>
          <p>Your preferences help us personalise calmer, more comfortable journeys.</p>
        </div>
      </aside>

      <main className="settings-primary" id="settings-preferences">
        <header className="settings-page-heading">
          <h2>Preferences</h2>
          <p>Customise your experience to match your sensory needs.</p>
          <span className="settings-saved" role="status" aria-live="polite">{saved}</span>
        </header>

        <section className="settings-sensory-card glass-panel" aria-labelledby="sensory-preferences-heading">
          <header className="settings-sensory-card__heading">
            <div><h2 id="sensory-preferences-heading">Sensory preferences</h2><p>Adjust what affects your comfort the most.</p></div>
            <button type="button" className="settings-reset" onClick={() => { resetSensoryPreferences(); markSaved("Sensory preferences reset"); }}>
              <AppIcon name="reset" size={18} /> Reset to default
            </button>
          </header>
          <div className="settings-sensory-list">
            {SENSORY_SETTINGS.map((setting) => (
              <SensitivitySelector
                key={setting.id}
                {...setting}
                value={sensoryPreferences[setting.id]}
                onChange={(level) => updateSensory(setting.id, level)}
              />
            ))}
          </div>
        </section>
      </main>

      <aside className="settings-secondary">
        <section className="settings-side-card glass-panel" id="settings-notifications">
          <CardHeading title="Notifications" description="Choose what updates you receive." />
          <div className="settings-toggle-list">
            <SettingsToggle label="Route alerts" description="Disruptions and changes" checked={notificationPreferences.routeAlerts} onChange={(enabled) => updateNotification("routeAlerts", enabled)} />
            <SettingsToggle label="Sensory alerts" description="High sensory conditions ahead" checked={notificationPreferences.sensoryAlerts} onChange={(enabled) => updateNotification("sensoryAlerts", enabled)} />
          </div>
          <p className="settings-availability-note">Only notification types currently supported by eScape are shown.</p>
        </section>

        <section className="settings-side-card glass-panel" aria-labelledby="appearance-heading">
          <CardHeading title="Appearance" description="Choose how eScape looks." />
          <fieldset className="theme-control" aria-labelledby="appearance-heading">
            <legend id="appearance-heading">Theme</legend>
            <button type="button" aria-pressed={theme === "light"} onClick={() => chooseTheme("light")}><AppIcon name="sun" size={18} /> Light</button>
            <button type="button" aria-pressed={theme === "dark"} onClick={() => chooseTheme("dark")}><AppIcon name="moon" size={18} /> Dark</button>
          </fieldset>
        </section>

        <section className="settings-side-card glass-panel" id="settings-account">
          <CardHeading title="Account" description="Profile & security." />
          <p className="settings-honest-state">Account sign-in is not configured in this version. Preferences are stored in this browser.</p>
        </section>

        <section className="settings-side-card glass-panel" id="settings-about">
          <CardHeading title="About" description="About eScape." />
          <p className="settings-about-brand"><strong>eScape</strong><span>Calmer journeys through Melbourne CBD.</span></p>
          <p className="settings-version">Version 0.1</p>
        </section>

        <section className="settings-side-card glass-panel" id="settings-support">
          <CardHeading title="Support" description="Help & feedback." />
          <button type="button" className="settings-support-action" onClick={openSupport}>Open support</button>
        </section>
      </aside>
    </div>
  );
}
