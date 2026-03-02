// frontend/src/app/layout.tsx
// Faz 1 — Root layout

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Membro",
  description: "Agentic AI Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tr">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        {children}
      </body>
    </html>
  );
}
