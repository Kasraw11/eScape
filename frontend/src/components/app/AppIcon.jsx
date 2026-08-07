export default function AppIcon({ name, size = 22, className = "" }) {
  const common = {
    className,
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.9,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    "aria-hidden": true,
  };

  const paths = {
    home: <><path d="m3 11 9-8 9 8" /><path d="M5.5 9.5V21h13V9.5" /><path d="M9.5 21v-6h5v6" /></>,
    route: <><circle cx="6" cy="4" r="2" /><circle cx="18" cy="20" r="2" /><path d="M6 6v5c0 1.7 1.3 3 3 3h6c1.7 0 3 1.3 3 3v1" /><path d="M18 3v7" /><path d="m15.5 7.5 2.5 2.5 2.5-2.5" /></>,
    leaf: <><path d="M20.5 3.5C11 3.8 5.7 7.2 5.2 13.1c-.4 4.2 3.2 7.4 7.2 6.1 5.4-1.7 7.5-7.5 8.1-15.7Z" /><path d="M3 21c2.3-5 6.5-8.7 12.5-11" /></>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /><path d="M10 21h4" /><path d="M10 3.3V2h4v1.3" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.6v-.2h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z" /></>,
    sliders: <><path d="M4 6h5" /><path d="M15 6h5" /><circle cx="12" cy="6" r="3" /><path d="M4 18h5" /><path d="M15 18h5" /><circle cx="12" cy="18" r="3" /></>,
    user: <><circle cx="12" cy="7" r="4" /><path d="M4.5 21a7.5 7.5 0 0 1 15 0" /></>,
    info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v6" /><path d="M12 7h.01" /></>,
    help: <><circle cx="12" cy="12" r="9" /><path d="M9.6 9a2.6 2.6 0 1 1 3.2 2.5c-.8.3-.8 1-.8 1.5" /><path d="M12 17h.01" /></>,
    sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2" /><path d="M12 20v2" /><path d="m4.9 4.9 1.4 1.4" /><path d="m17.7 17.7 1.4 1.4" /><path d="M2 12h2" /><path d="M20 12h2" /><path d="m4.9 19.1 1.4-1.4" /><path d="m17.7 6.3 1.4-1.4" /></>,
    moon: <path d="M20 15.2A8.5 8.5 0 0 1 8.8 4 8.5 8.5 0 1 0 20 15.2Z" />,
    crowd: <><circle cx="9" cy="8" r="3" /><circle cx="17" cy="9" r="2.5" /><path d="M3 20a6 6 0 0 1 12 0" /><path d="M14 15.2A5 5 0 0 1 21 20" /></>,
    volume: <><path d="M5 10v4h3l4 4V6l-4 4H5Z" /><path d="M16 9a4 4 0 0 1 0 6" /><path d="M18.5 6.5a7.5 7.5 0 0 1 0 11" /></>,
    brightness: <><circle cx="12" cy="12" r="3.5" /><path d="M12 2v2" /><path d="M12 20v2" /><path d="M2 12h2" /><path d="M20 12h2" /><path d="m5 5 1.5 1.5" /><path d="m17.5 17.5 1.5 1.5" /><path d="m19 5-1.5 1.5" /><path d="m6.5 17.5-1.5 1.5" /></>,
    scent: <><path d="M4 8h10c2 0 2-3 0-3-1 0-1.5.5-1.7 1" /><path d="M4 12h15c2.5 0 2.5 4 0 4-1.2 0-1.8-.6-2-1.2" /><path d="M4 16h7" /></>,
    reset: <><path d="M4 7v5h5" /><path d="M5.5 11a7 7 0 1 1 1.3 6.5" /></>,
    walk: <><circle cx="13" cy="4" r="2" /><path d="m10 22 1.5-7-2.5-2 2-5 4 2 3 3" /><path d="m11.5 15 4 2 2 5" /><path d="M7 13 4 18" /></>,
    transit: <><rect x="5" y="3" width="14" height="16" rx="3" /><path d="M8 7h8" /><path d="M8 12h8" /><path d="m8 21 2-2" /><path d="m16 19 2 2" /><circle cx="9" cy="15.5" r="1" /><circle cx="15" cy="15.5" r="1" /></>,
  };

  return <svg {...common}>{paths[name] || paths.home}</svg>;
}
