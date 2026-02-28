import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getProject } from "../lib/api";

export default function Review() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectId) return;
    getProject(projectId)
      .then((proj) => {
        const uri = proj.output_uri;
        // output_uri is like "data/output/clip_xxx.mp4" — serve via /files/
        setVideoUrl(uri ? `/files/${uri.replace(/^data\//, "")}` : null);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-neutral-400">Loading...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-12 px-6">
      <h1 className="text-3xl font-bold mb-8">Your Video</h1>

      {videoUrl ? (
        <div className="space-y-6">
          <div className="bg-neutral-900 rounded-2xl overflow-hidden">
            <video
              src={videoUrl}
              controls
              className="w-full max-h-[70vh]"
            />
          </div>

          <div className="flex gap-4">
            <a
              href={videoUrl}
              download
              className="px-6 py-3 bg-blue-600 rounded-lg font-semibold hover:bg-blue-500 transition"
            >
              Download
            </a>
            <button
              onClick={() => navigate(`/setup/${projectId}`)}
              className="px-6 py-3 border border-neutral-700 rounded-lg font-semibold hover:bg-neutral-800 transition"
            >
              Edit Again
            </button>
            <button
              onClick={() => navigate("/")}
              className="px-6 py-3 border border-neutral-700 rounded-lg font-semibold hover:bg-neutral-800 transition"
            >
              New Project
            </button>
          </div>
        </div>
      ) : (
        <div className="text-center py-20">
          <p className="text-neutral-500 text-lg">
            Video not ready yet. Check back soon.
          </p>
        </div>
      )}
    </div>
  );
}
