import type { Metadata } from "next";
import { Fraunces, Geist, Geist_Mono } from "next/font/google";

import { ThemeCorner } from "@/components/theme-corner";
import { themeScript } from "@/lib/theme";

import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  axes: ["SOFT", "WONK", "opsz"],
});

export const metadata: Metadata = {
  title: "CreatorRetain",
  description: "Where creators, brands and agencies work together.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      // The script below writes data-theme onto this element
      // before React gets here, so the attribute the browser has
      // is deliberately not the one the server sent. Without this
      // React reports that difference as a hydration error.
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} ${fraunces.variable} h-full antialiased`}
    >
      <head>
        {/* Blocking, and first. Anything above it would paint in
            the wrong theme and be corrected a frame later, which
            is the flash this exists to avoid. */}
        <script
          dangerouslySetInnerHTML={{ __html: themeScript() }}
        />
      </head>
      <body className="min-h-full flex flex-col">
        {children}
        <ThemeCorner />
      </body>
    </html>
  );
}
