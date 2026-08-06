"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export const PRIMARY_LINKS = [
  { href: "/plan", desktop: "Plan", mobile: "Plan" },
  { href: "/refuges", desktop: "Find Refuges", mobile: "Refuges" },
  { href: "/alerts", desktop: "Alerts", mobile: "Alerts" },
  { href: "/settings", desktop: "Settings", mobile: "Settings" },
];

export default function AppHeader() {
  const pathname = usePathname();
  return (
    <header className="site-header">
      <Link className="brand" href="/plan" aria-label="eScape Plan">
        <span className="brand__mark" aria-hidden="true">e</span>
        <span className="brand__copy"><strong>eScape</strong><small>Calmer journeys through Melbourne CBD</small></span>
      </Link>
      <nav className="desktop-nav" aria-label="Primary navigation">
        {PRIMARY_LINKS.map((link) => {
          const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
          return <Link key={link.href} href={link.href} className={active ? "desktop-nav__active" : ""} aria-current={active ? "page" : undefined}>{link.desktop}</Link>;
        })}
      </nav>
    </header>
  );
}
