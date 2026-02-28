import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getProject, submitClarifyAnswers, startEdit } from "../lib/api";
import VideoCard from "../components/VideoCard";
import ClarifyChat from "../components/ClarifyChat";

interface VideoInfo {
  id: string;
  filename: string;
  duration_s: number;
  summary: string;
  ingestion_status: string;
}

export default function Setup() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [videos, setVideos] = useState<VideoInfo[]>([]);
  const [status, setStatus] = useState("loading");
  const [structuredPrompt, setStructuredPrompt] = useState("");

  // Poll project status
  useEffect(() => {
    if (!projectId) return;
    const poll = setInterval(async () => {
      try {
        const proj = await getProject(projectId);
        setVideos(proj.videos);
        setStatus(proj.status);
        if (proj.status !== "ingesting") {
          clearInterval(poll);
        }
      } catch (e) {
        console.error(e);
      }
    }, 3000);
    return () => clearInterval(poll);
  }, [projectId]);

  const handleClarifyDone = async (answers: Record<string, string>) => {
    if (!projectId) return;
    const result = await submitClarifyAnswers(projectId, answers);
    if (result.structured_prompt) {
      setStructuredPrompt(result.structured_prompt);
    }
  };

  const handleStartEdit = async () => {
    if (!projectId || !structuredPrompt) return;
    await startEdit(projectId, structuredPrompt);
    navigate(`/progress/${projectId}`);
  };

  return (
    <div className="max-w-6xl mx-auto py-12 px-6">
      <h1 className="text-3xl font-bold mb-8">Setup Your Edit</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left: Video cards */}
        <div>
          <h2 className="text-lg font-semibold mb-4 text-neutral-300">
            Videos {status === "ingesting" && "(analyzing...)"}
          </h2>
          <div className="space-y-3">
            {videos.map((v, i) => (
              <VideoCard key={v.id} video={v} index={i} />
            ))}
          </div>
        </div>

        {/* Right: Clarifying chat */}
        <div>
          <h2 className="text-lg font-semibold mb-4 text-neutral-300">
            Tell us about your video
          </h2>
          <ClarifyChat
            summariesReady={status !== "ingesting"}
            onDone={handleClarifyDone}
          />

          {structuredPrompt && (
            <button
              onClick={handleStartEdit}
              className="mt-6 w-full py-3 bg-blue-600 rounded-lg font-semibold hover:bg-blue-500 transition"
            >
              Generate Edit Plan
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
