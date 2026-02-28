"use client";

import { PhoenixEmbed } from "@/components/traces/PhoenixEmbed";

/**
 * NAT Trace Dashboard page.
 * Embeds Phoenix UI for observability (hackathon default).
 */
export default function TracesPage() {
  return (
    <div className="h-screen flex flex-col">
      <header className="h-12 bg-canvas-surface border-b border-canvas-border flex items-center px-4 gap-4">
        <a href="/" className="text-sm font-bold tracking-wide hover:text-canvas-accent">
          Auto-Vid
        </a>
        <span className="text-xs text-gray-400">/ Traces</span>
      </header>
      <main className="flex-1">
        <PhoenixEmbed />
      </main>
    </div>
  );
}
