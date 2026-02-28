"use client";

import React from "react";

/**
 * Phoenix UI embed for NAT trace visualization.
 * Hackathon default: iframe pointing to local Phoenix server.
 */
export const PhoenixEmbed: React.FC = () => {
  const phoenixUrl = process.env.NEXT_PUBLIC_PHOENIX_URL || "http://localhost:6006";

  return (
    <iframe
      src={phoenixUrl}
      className="w-full h-full border-0"
      title="Phoenix Trace Dashboard"
      allow="clipboard-read; clipboard-write"
    />
  );
};
