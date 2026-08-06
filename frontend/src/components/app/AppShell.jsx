"use client";

import { JourneyProvider } from "../../context/JourneyContext.jsx";
import AppHeader from "./AppHeader.jsx";
import MobileNavigation from "./MobileNavigation.jsx";
import SupportButton from "./SupportButton.jsx";

export default function AppShell({ children }) {
  return <JourneyProvider><div className="app-shell"><AppHeader /><main className="app-main" id="main-content">{children}</main><footer className="site-footer"><p><strong>eScape</strong> · Sensory-aware navigation for Melbourne CBD</p><p>Check current travel conditions before you leave.</p></footer><SupportButton /><MobileNavigation /></div></JourneyProvider>;
}
