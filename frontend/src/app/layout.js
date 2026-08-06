import "./globals.css";

export const metadata = {
  title: "eScape",
  description: "Sensory-aware urban navigation for Melbourne CBD",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
