"use client";

import React from "react";

interface StylePromptProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isProcessing: boolean;
  disabled: boolean;
}

export const StylePrompt: React.FC<StylePromptProps> = ({
  value,
  onChange,
  onSubmit,
  isProcessing,
  disabled,
}) => {
  return (
    <div className="space-y-2">
      <label className="text-xs font-semibold text-gray-400">
        Style Prompt
      </label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Describe the style/vibe: funny vlog with memes, cinematic travel montage, fast-paced tech demo..."
        className="w-full h-20 bg-canvas-bg border border-canvas-border rounded-lg p-2 text-xs text-white placeholder-gray-500 resize-none focus:outline-none focus:border-canvas-accent"
        disabled={isProcessing}
      />
      <button
        onClick={onSubmit}
        disabled={disabled || isProcessing || !value.trim()}
        className="w-full py-2 rounded-lg text-xs font-bold transition-colors disabled:opacity-40 disabled:cursor-not-allowed bg-canvas-accent hover:bg-blue-600 text-white"
      >
        {isProcessing ? "Processing..." : "GO"}
      </button>
    </div>
  );
};
