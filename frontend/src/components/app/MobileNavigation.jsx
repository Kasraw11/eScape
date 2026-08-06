"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PRIMARY_LINKS } from "./AppHeader.jsx";

export default function MobileNavigation() {
  const pathname = usePathname();
  return (
    <nav className="mobile-bottom-nav" aria-label="Mobile primary navigation">
      {PRIMARY_LINKS.map((link) => {
        const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
        return <Link key={link.href} href={link.href} aria-current={active ? "page" : undefined}><span aria-hidden="true">{link.mobile.slice(0, 1)}</span>{link.mobile}</Link>;
      })}
    </nav>
  );
}
