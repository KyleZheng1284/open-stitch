import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Auto-Vid | Agentic Video Editor",
  description: "AI-powered short-form video editing platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-canvas-bg text-white antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
