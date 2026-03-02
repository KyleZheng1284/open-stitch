import { useState, useEffect, useCallback } from "react";
import { getProject } from "../lib/api";

interface VideoInfo {
  id: string;
  filename: string;
  duration_s: number;
  summary: string;
  ingestion_status: string;
}

interface ProjectState {
  id: string;
  status: string;
  videos: VideoInfo[];
  outputUri: string | null;
}

export function useProject(projectId: string | undefined) {
  const [project, setProject] = useState<ProjectState | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!projectId) return;
    try {
      const data = await getProject(projectId);
      setProject({
        id: data.id,
        status: data.status,
        videos: data.videos,
        outputUri: data.output_uri || null,
      });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { project, loading, refresh };
}
