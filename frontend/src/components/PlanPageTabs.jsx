"use client";

import { useRef } from "react";
import AppIcon from "./app/AppIcon.jsx";

const TABS = [
  { id: "journey", label: "Plan your journey", icon: "route" },
  { id: "trip", label: "Current trip", icon: "transit" },
];

export default function PlanPageTabs({ activeTab, onChange }) {
  const refs = useRef([]);
  return <div className="plan-tabs" role="tablist" aria-label="Plan journey sections">{TABS.map((tab, index) => <button key={tab.id} id={`plan-tab-${tab.id}`} type="button" role="tab" aria-selected={activeTab === tab.id} aria-controls={`plan-panel-${tab.id}`} tabIndex={activeTab === tab.id ? 0 : -1} ref={(node) => { refs.current[index] = node; }} onClick={() => onChange(tab.id)} onKeyDown={(event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === "Home" ? 0 : event.key === "End" ? TABS.length - 1 : (index + (event.key === "ArrowRight" ? 1 : -1) + TABS.length) % TABS.length;
    onChange(TABS[next].id); refs.current[next]?.focus();
  }}><AppIcon name={tab.icon} size={19} />{tab.label}</button>)}</div>;
}
