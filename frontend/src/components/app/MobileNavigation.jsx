"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PRIMARY_LINKS } from "./AppHeader.jsx";
import AppIcon from "./AppIcon.jsx";

export default function MobileNavigation() {
  const pathname = usePathname();
  return (
    <nav className="mobile-bottom-nav" aria-label="Mobile primary navigation">
      {PRIMARY_LINKS.map((link) => {
        const active = link.href === "/" ? pathname === "/" : pathname === link.href || pathname.startsWith(`${link.href}/`);
        return <Link key={link.href} href={link.href} aria-current={active ? "page" : undefined}><span aria-hidden="true"><AppIcon name={link.icon} size={20} /></span>{link.mobile}</Link>;
      })}
    </nav>
  );
}
