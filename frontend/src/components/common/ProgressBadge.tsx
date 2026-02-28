"use client";

import React from "react";

interface ProgressBadgeProps {
  progress: number; // 0-100
  label?: string;
}

export const ProgressBadge: React.FC<ProgressBadgeProps> = ({
  progress,
  label,
}) => {
  const isComplete = progress >= 100;

  return (
    <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-canvas-bg border border-canvas-border text-[10px]">
      {isComplete ? (
        <span className="text-green-400">✓</span>
      ) : (
        <span className="text-blue-400">{Math.round(progress)}%</span>
      )}
      {label && <span className="text-gray-400">{label}</span>}
    </div>
  );
};
