import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Reading Room — Jared A. Ball Book Archive",
  description: "Follow the books. Find the source. A private reading archive from Jared A. Ball’s YouTube channel.",
  robots: { index: false, follow: false },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
