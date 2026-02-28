"use client";

import React from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { StatusDot } from "@/components/common/StatusDot";

interface Video {
  id: string;
  filename: string;
  duration_ms: number;
  thumbnail_url?: string;
  ingestion_status: string;
}

interface VideoCardProps {
  video: Video;
  index: number;
}

export const VideoCard: React.FC<VideoCardProps> = ({ video, index }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: video.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const durationStr = `${Math.floor(video.duration_ms / 60000)}:${String(
    Math.floor((video.duration_ms % 60000) / 1000)
  ).padStart(2, "0")}`;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="bg-canvas-bg border border-canvas-border rounded-lg p-3 mb-2 flex gap-3 items-center"
    >
      {/* Drag handle */}
      <div
        {...attributes}
        {...listeners}
        className="cursor-grab active:cursor-grabbing text-gray-500 hover:text-gray-300"
      >
        <span className="text-xs font-mono">{index + 1}.</span>
        <span className="ml-1">⠿</span>
      </div>

      {/* Thumbnail */}
      <div className="w-12 h-8 bg-gray-800 rounded overflow-hidden flex-shrink-0">
        {video.thumbnail_url && (
          <img
            src={video.thumbnail_url}
            alt={video.filename}
            className="w-full h-full object-cover"
          />
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium truncate">{video.filename}</p>
        <div className="flex items-center gap-1 mt-0.5">
          <StatusDot status={video.ingestion_status} />
          <span className="text-[10px] text-gray-400">
            {video.ingestion_status}
          </span>
          <span className="text-[10px] text-gray-500 ml-auto">
            {durationStr}
          </span>
        </div>
      </div>
    </div>
  );
};
