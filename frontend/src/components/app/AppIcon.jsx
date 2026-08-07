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
    walk: <><circle cx="13" cy="4" r="2" /><path d="m10 22 1.5-7-2.5-2 2-5 4 2 3 3" /><path d="m11.5 15 4 2 2 5" /><path d="M7 13 4 18" /></>,
    transit: <><rect x="5" y="3" width="14" height="16" rx="3" /><path d="M8 7h8" /><path d="M8 12h8" /><path d="m8 21 2-2" /><path d="m16 19 2 2" /><circle cx="9" cy="15.5" r="1" /><circle cx="15" cy="15.5" r="1" /></>,
  };

  return <svg {...common}>{paths[name] || paths.home}</svg>;
}
