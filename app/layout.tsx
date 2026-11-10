import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Reading Room — YouTube Book Archive",
  description: "Follow the books. Find the source. A private book archive for your favorite YouTube channels.",
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
