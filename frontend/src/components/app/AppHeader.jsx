"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import AppIcon from "./AppIcon.jsx";

export const PRIMARY_LINKS = [
  { href: "/", desktop: "Home", mobile: "Home", icon: "home" },
  { href: "/plan", desktop: "Plan", mobile: "Plan", icon: "route" },
  { href: "/refuges", desktop: "Find Refuges", mobile: "Refuges", icon: "leaf" },
  { href: "/alerts", desktop: "Alerts", mobile: "Alerts", icon: "bell" },
  { href: "/settings", desktop: "Settings", mobile: "Settings", icon: "settings" },
];

export default function AppHeader({ onEmergency, emergencyButtonRef }) {
  const pathname = usePathname();
  return (
    <header className="site-header">
      <Link className="brand" href="/" aria-label="eScape Home">
        <span className="brand__mark" aria-hidden="true">e</span>
        <span className="brand__copy"><strong>eScape</strong><small>Calmer journeys through Melbourne CBD</small></span>
      </Link>
      <nav className="desktop-nav" aria-label="Primary navigation">
        {PRIMARY_LINKS.map((link) => {
          const active = link.href === "/" ? pathname === "/" : pathname === link.href || pathname.startsWith(`${link.href}/`);
          return <Link key={link.href} href={link.href} className={active ? "desktop-nav__active" : ""} aria-current={active ? "page" : undefined}><AppIcon name={link.icon} />{link.desktop}</Link>;
        })}
      </nav>
      <button className="emergency-button" type="button" onClick={onEmergency} ref={emergencyButtonRef}><span aria-hidden="true">+</span><span>Emergency</span></button>
    </header>
  );
}
