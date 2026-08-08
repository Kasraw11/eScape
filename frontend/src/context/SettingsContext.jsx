"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

export const DEFAULT_SENSORY_PREFERENCES = {
  crowding: "high",
  noise: "medium",
  brightness: "high",
  odour: "medium",
};

export const DEFAULT_NOTIFICATION_PREFERENCES = {
  routeAlerts: true,
  sensoryAlerts: true,
};

const SETTINGS_STORAGE_KEY = "escape-settings";
const THEME_STORAGE_KEY = "escape-theme";
const LEVELS = new Set(["low", "medium", "high"]);
const SettingsContext = createContext(null);

function storedSettings() {
  try {
    const parsed = JSON.parse(globalThis.localStorage?.getItem(SETTINGS_STORAGE_KEY) || "null");
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function storedTheme() {
  try {
    return globalThis.localStorage?.getItem(THEME_STORAGE_KEY) === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

export function SettingsProvider({ children }) {
  const [sensoryPreferences, setSensoryPreferences] = useState(DEFAULT_SENSORY_PREFERENCES);
  const [notificationPreferences, setNotificationPreferences] = useState(DEFAULT_NOTIFICATION_PREFERENCES);
  const [theme, setThemeState] = useState("light");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const saved = storedSettings();
    setSensoryPreferences({
      ...DEFAULT_SENSORY_PREFERENCES,
      ...Object.fromEntries(Object.entries(saved.sensoryPreferences || {}).filter(([, value]) => LEVELS.has(value))),
    });
    setNotificationPreferences({
      ...DEFAULT_NOTIFICATION_PREFERENCES,
      ...Object.fromEntries(Object.entries(saved.notificationPreferences || {}).filter(([, value]) => typeof value === "boolean")),
    });
    const initialTheme = storedTheme();
    setThemeState(initialTheme);
    document.documentElement.dataset.theme = initialTheme;
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    try {
      globalThis.localStorage?.setItem(SETTINGS_STORAGE_KEY, JSON.stringify({ sensoryPreferences, notificationPreferences }));
    } catch {
      // Storage can be unavailable in privacy-restricted browser contexts.
    }
  }, [notificationPreferences, ready, sensoryPreferences]);

  function setTheme(value) {
    const next = value === "dark" ? "dark" : "light";
    setThemeState(next);
    document.documentElement.dataset.theme = next;
    try {
      globalThis.localStorage?.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // The selected theme still applies for the current session.
    }
  }

  const value = useMemo(() => ({
    sensoryPreferences,
    notificationPreferences,
    theme,
    setSensoryPreference(key, level) {
      if (Object.hasOwn(DEFAULT_SENSORY_PREFERENCES, key) && LEVELS.has(level)) {
        setSensoryPreferences((current) => ({ ...current, [key]: level }));
      }
    },
    resetSensoryPreferences() {
      setSensoryPreferences(DEFAULT_SENSORY_PREFERENCES);
    },
    setNotificationPreference(key, enabled) {
      if (Object.hasOwn(DEFAULT_NOTIFICATION_PREFERENCES, key)) {
        setNotificationPreferences((current) => ({ ...current, [key]: Boolean(enabled) }));
      }
    },
    setTheme,
  }), [notificationPreferences, sensoryPreferences, theme]);

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings() {
  const value = useContext(SettingsContext);
  if (!value) throw new Error("useSettings must be used within SettingsProvider");
  return value;
}

export function useOptionalSettings() {
  return useContext(SettingsContext);
}
