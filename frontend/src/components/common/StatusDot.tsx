"use client";

import React from "react";

interface StatusDotProps {
  status: string;
  size?: "sm" | "md";
}

const statusColorMap: Record<string, string> = {
  pending: "bg-gray-500",
  processing: "bg-blue-500 animate-pulse",
  running: "bg-blue-500 animate-pulse",
  complete: "bg-green-500",
  done: "bg-green-500",
  success: "bg-green-500",
  error: "bg-red-500",
  failed: "bg-red-500",
};

export const StatusDot: React.FC<StatusDotProps> = ({
  status,
  size = "sm",
}) => {
  const colorClass = statusColorMap[status] || "bg-gray-500";
  const sizeClass = size === "sm" ? "w-1.5 h-1.5" : "w-2.5 h-2.5";

  return <span className={`inline-block rounded-full ${sizeClass} ${colorClass}`} />;
};
