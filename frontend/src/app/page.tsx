"use client";

import { ReactFlowProvider } from "@xyflow/react";
import { CanvasPanel } from "@/components/canvas/CanvasPanel";
import { SidebarPanel } from "@/components/sidebar/SidebarPanel";
import { useProjectState } from "@/hooks/useProjectState";
import { useWebSocket } from "@/hooks/useWebSocket";

/**
 * Main editor page: Sidebar (~25%) + Canvas (~75%)
 *
 * The sidebar contains upload zone, draggable video list, style prompt,
 * and clip previews. The canvas shows the interactive React Flow node graph
 * with video nodes, agent nodes, and tool nodes.
 */
export default function EditorPage() {
  const project = useProjectState();
  const ws = useWebSocket(project.jobId);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 h-12 bg-canvas-surface border-b border-canvas-border z-50 flex items-center px-4 gap-4">
        <h1 className="text-sm font-bold tracking-wide">Auto-Vid</h1>
        <div className="flex-1 mx-4">
          <span className="text-xs text-gray-400">
            {project.stylePrompt
              ? `Style: "${project.stylePrompt}"`
              : "Upload videos and describe your style"}
          </span>
        </div>
        <a
          href="/traces"
          className="text-xs text-canvas-accent hover:underline"
        >
          Traces
        </a>
      </header>

      {/* Main content below header */}
      <div className="flex w-full pt-12">
        {/* Sidebar: ~25% */}
        <aside className="w-80 min-w-72 border-r border-canvas-border bg-canvas-surface overflow-y-auto">
          <SidebarPanel
            videos={project.videos}
            clips={project.clips}
            onReorder={project.reorderVideos}
            onUpload={project.uploadVideo}
            onSubmit={project.startEditing}
            stylePrompt={project.stylePrompt}
            onStylePromptChange={project.setStylePrompt}
            isProcessing={project.isProcessing}
          />
        </aside>

        {/* Canvas: ~75% */}
        <main className="flex-1 relative">
          <ReactFlowProvider>
            <CanvasPanel
              videos={project.videos}
              agentStates={ws.agentStates}
              onVideoReorder={project.reorderVideos}
            />
          </ReactFlowProvider>
        </main>
      </div>
    </div>
  );
}
