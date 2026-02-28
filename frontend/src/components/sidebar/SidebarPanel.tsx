"use client";

import React from "react";
import { UploadZone } from "./UploadZone";
import { VideoCard } from "./VideoCard";
import { StylePrompt } from "./StylePrompt";
import { ClipPreview } from "./ClipPreview";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";

interface Video {
  id: string;
  filename: string;
  duration_ms: number;
  thumbnail_url?: string;
  ingestion_status: string;
}

interface Clip {
  id: string;
  preview_url?: string;
  status: string;
}

interface SidebarPanelProps {
  videos: Video[];
  clips: Clip[];
  onReorder: (videoIds: string[]) => void;
  onUpload: (files: File[]) => void;
  onSubmit: () => void;
  stylePrompt: string;
  onStylePromptChange: (prompt: string) => void;
  isProcessing: boolean;
}

export const SidebarPanel: React.FC<SidebarPanelProps> = ({
  videos,
  clips,
  onReorder,
  onUpload,
  onSubmit,
  stylePrompt,
  onStylePromptChange,
  isProcessing,
}) => {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = videos.findIndex((v) => v.id === active.id);
    const newIndex = videos.findIndex((v) => v.id === over.id);
    if (oldIndex === -1 || newIndex === -1) return;

    const newOrder = [...videos];
    const [moved] = newOrder.splice(oldIndex, 1);
    newOrder.splice(newIndex, 0, moved);
    onReorder(newOrder.map((v) => v.id));
  };

  return (
    <div className="flex flex-col h-full p-4 gap-4">
      {/* Upload Zone */}
      <UploadZone onUpload={onUpload} />

      {/* Draggable Video List */}
      <div className="flex-1 overflow-y-auto">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={videos.map((v) => v.id)}
            strategy={verticalListSortingStrategy}
          >
            {videos.map((video, idx) => (
              <VideoCard key={video.id} video={video} index={idx} />
            ))}
          </SortableContext>
        </DndContext>

        {videos.length === 0 && (
          <p className="text-xs text-gray-500 text-center mt-4">
            Upload videos to get started
          </p>
        )}
      </div>

      {/* Style Prompt + GO */}
      <StylePrompt
        value={stylePrompt}
        onChange={onStylePromptChange}
        onSubmit={onSubmit}
        isProcessing={isProcessing}
        disabled={videos.length === 0}
      />

      {/* Clip Previews (after render) */}
      {clips.length > 0 && (
        <div className="border-t border-canvas-border pt-3">
          <h3 className="text-xs font-semibold text-gray-400 mb-2">
            Rendered Clips
          </h3>
          {clips.map((clip) => (
            <ClipPreview key={clip.id} clip={clip} />
          ))}
        </div>
      )}
    </div>
  );
};
