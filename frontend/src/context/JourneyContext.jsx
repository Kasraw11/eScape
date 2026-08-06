"use client";

import { createContext, useContext, useMemo, useState } from "react";

const JourneyContext = createContext(null);

export function JourneyProvider({ children }) {
  const [activeJourney, setActiveJourney] = useState(null);
  const [journeyStatus, setJourneyStatus] = useState("idle");

  const value = useMemo(() => ({
    activeJourney,
    journeyStatus,
    startJourney(journey) {
      setActiveJourney(journey);
      setJourneyStatus("active");
    },
    endJourney() {
      setActiveJourney(null);
      setJourneyStatus("idle");
    },
  }), [activeJourney, journeyStatus]);

  return <JourneyContext.Provider value={value}>{children}</JourneyContext.Provider>;
}

export function useJourney() {
  const value = useContext(JourneyContext);
  const [fallbackJourney, setFallbackJourney] = useState(null);
  const fallback = useMemo(() => ({
    activeJourney: fallbackJourney,
    journeyStatus: fallbackJourney ? "active" : "idle",
    startJourney: setFallbackJourney,
    endJourney: () => setFallbackJourney(null),
  }), [fallbackJourney]);
  return value || fallback;
}
