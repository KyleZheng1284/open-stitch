/**
 * REST API client for the Auto-Vid backend.
 *
 * All requests are proxied through Next.js rewrites in development
 * (localhost:3000/api/* -> localhost:8080/api/*).
 */

const BASE_URL = "/api/v1";

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API error ${res.status}: ${error}`);
  }

  return res.json();
}

export const api = {
  // ─── Projects ──────────────────────────────────────────────────

  createProject: (data: {
    video_uris: string[];
    style_prompt: string;
  }) =>
    request<{ project_id: string; status: string }>("/projects", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getProject: (projectId: string) =>
    request<{
      project_id: string;
      status: string;
      videos: any[];
      clips: any[];
    }>(`/projects/${projectId}`),

  uploadVideo: async (projectId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${BASE_URL}/projects/${projectId}/upload`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    return res.json() as Promise<{ video_id: string }>;
  },

  reorderVideos: (projectId: string, videoIds: string[]) =>
    request<{ status: string }>(`/projects/${projectId}/order`, {
      method: "PUT",
      body: JSON.stringify(videoIds),
    }),

  startEditing: (projectId: string, stylePrompt: string) =>
    request<{ job_id: string; status: string }>(
      `/projects/${projectId}/edit`,
      {
        method: "POST",
        body: JSON.stringify({ style_prompt: stylePrompt }),
      }
    ),

  // ─── Jobs ──────────────────────────────────────────────────────

  getJobStatus: (jobId: string) =>
    request<{
      job_id: string;
      status: string;
      phase: string;
      progress: number;
    }>(`/jobs/${jobId}`),

  // ─── Clips ─────────────────────────────────────────────────────

  getClip: (clipId: string) =>
    request<{
      clip_id: string;
      download_url: string | null;
      status: string;
    }>(`/clips/${clipId}`),

  publishClip: (clipId: string, platforms: string[]) =>
    request<{ status: string }>(`/clips/${clipId}/publish`, {
      method: "POST",
      body: JSON.stringify({ platforms }),
    }),
};
