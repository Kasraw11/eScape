import "./globals.css";
import AppShell from "../components/app/AppShell.jsx";
import { AlertCenterProvider } from "../context/AlertCenterContext.jsx";
import { SettingsProvider } from "../context/SettingsContext.jsx";

const themeScript = `(function(){try{var t=localStorage.getItem('escape-theme');document.documentElement.dataset.theme=t==='dark'?'dark':'light'}catch(e){document.documentElement.dataset.theme='light'}})();`;

export const metadata = {
  title: "eScape",
  description: "Sensory-aware urban navigation for Melbourne CBD",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" data-theme="light" suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: themeScript }} /></head>
      <body><SettingsProvider><AlertCenterProvider><AppShell>{children}</AppShell></AlertCenterProvider></SettingsProvider></body>
    </html>
  );
}
