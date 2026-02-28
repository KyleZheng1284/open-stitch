import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getProject, createJobSocket } from "../lib/api";
import ProgressTimeline from "../components/ProgressTimeline";

interface Step {
  name: string;
  status: "pending" | "running" | "done" | "error";
  elapsed?: number;
}

export default function Progress() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [steps, setSteps] = useState<Step[]>([
    { name: "Downloading videos", status: "running" },
    { name: "Speech recognition (ASR)", status: "pending" },
    { name: "Visual analysis (VLM)", status: "pending" },
    { name: "Generating edit plan", status: "pending" },
    { name: "Rendering video", status: "pending" },
  ]);

  useEffect(() => {
    if (!projectId) return;

    // Poll for completion
    const poll = setInterval(async () => {
      try {
        const proj = await getProject(projectId);
        if (proj.status === "complete") {
          clearInterval(poll);
          navigate(`/review/${projectId}`);
        }
        if (proj.status === "error") {
          clearInterval(poll);
          setSteps((prev) =>
            prev.map((s) =>
              s.status === "running" ? { ...s, status: "error" } : s
            )
          );
        }
      } catch (e) {
        console.error(e);
      }
    }, 5000);

    // WebSocket for real-time updates
    let ws: WebSocket | null = null;
    try {
      ws = createJobSocket(projectId);
      ws.onmessage = (evt) => {
        const event = JSON.parse(evt.data);
        if (event.phase) {
          setSteps((prev) => {
            const idx = prev.findIndex(
              (s) => s.name.toLowerCase().includes(event.phase.toLowerCase())
            );
            if (idx >= 0) {
              return prev.map((s, i) => ({
                ...s,
                status: i < idx ? "done" : i === idx ? "running" : "pending",
              }));
            }
            return prev;
          });
        }
      };
    } catch {
      // WS not available — polling fallback
    }

    return () => {
      clearInterval(poll);
      ws?.close();
    };
  }, [projectId, navigate]);

  return (
    <div className="max-w-2xl mx-auto py-16 px-6">
      <h1 className="text-3xl font-bold mb-2">Processing Your Video</h1>
      <p className="text-neutral-400 mb-10">
        Sit tight while we analyze and edit your footage
      </p>
      <ProgressTimeline steps={steps} />
    </div>
  );
}
