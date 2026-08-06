import "./globals.css";
import AppShell from "../components/app/AppShell.jsx";

export const metadata = {
  title: "eScape",
  description: "Sensory-aware urban navigation for Melbourne CBD",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body><AppShell>{children}</AppShell></body>
    </html>
  );
}
