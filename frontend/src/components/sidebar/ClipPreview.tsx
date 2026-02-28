"use client";

import React from "react";

interface Clip {
  id: string;
  preview_url?: string;
  status: string;
}

interface ClipPreviewProps {
  clip: Clip;
}

export const ClipPreview: React.FC<ClipPreviewProps> = ({ clip }) => {
  return (
    <div className="bg-canvas-bg border border-canvas-border rounded-lg p-2 mb-2">
      <div className="w-full h-32 bg-gray-800 rounded mb-2 flex items-center justify-center">
        {clip.preview_url ? (
          <video
            src={clip.preview_url}
            className="w-full h-full object-contain rounded"
            controls
            muted
          />
        ) : (
          <span className="text-xs text-gray-500">{clip.status}</span>
        )}
      </div>
      <div className="flex gap-2">
        <button className="flex-1 py-1 text-[10px] bg-green-600 hover:bg-green-700 rounded text-white">
          Accept
        </button>
        <button className="flex-1 py-1 text-[10px] bg-red-600 hover:bg-red-700 rounded text-white">
          Reject
        </button>
        <button className="flex-1 py-1 text-[10px] bg-canvas-accent hover:bg-blue-600 rounded text-white">
          Publish
        </button>
      </div>
    </div>
  );
};
