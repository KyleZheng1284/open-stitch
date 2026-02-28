"use client";

import { useCallback, useState } from "react";
import { api } from "@/lib/api";

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

/**
 * Project state management hook.
 *
 * Manages video list, sequence order, style prompt, and clip results.
 * Syncs sidebar <-> canvas through shared state.
 */
export function useProjectState() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [clips, setClips] = useState<Clip[]>([]);
  const [stylePrompt, setStylePrompt] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);

  const uploadVideo = useCallback(
    async (files: File[]) => {
      for (const file of files) {
        // Create project if not exists
        let pid = projectId;
        if (!pid) {
          const project = await api.createProject({
            video_uris: [],
            style_prompt: "",
          });
          pid = project.project_id;
          setProjectId(pid);
        }

        const result = await api.uploadVideo(pid, file);
        setVideos((prev) => [
          ...prev,
          {
            id: result.video_id,
            filename: file.name,
            duration_ms: 0, // Will be updated after probe
            ingestion_status: "processing",
          },
        ]);
      }
    },
    [projectId]
  );

  const reorderVideos = useCallback(
    async (videoIds: string[]) => {
      setVideos((prev) => {
        const map = new Map(prev.map((v) => [v.id, v]));
        return videoIds.map((id) => map.get(id)!).filter(Boolean);
      });

      if (projectId) {
        await api.reorderVideos(projectId, videoIds);
      }
    },
    [projectId]
  );

  const startEditing = useCallback(async () => {
    if (!projectId || !stylePrompt.trim()) return;

    setIsProcessing(true);
    try {
      const result = await api.startEditing(projectId, stylePrompt);
      setJobId(result.job_id);
    } catch (err) {
      console.error("Failed to start editing:", err);
      setIsProcessing(false);
    }
  }, [projectId, stylePrompt]);

  return {
    projectId,
    jobId,
    videos,
    clips,
    stylePrompt,
    setStylePrompt,
    isProcessing,
    uploadVideo,
    reorderVideos,
    startEditing,
  };
}
