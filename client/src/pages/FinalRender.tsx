import { useState, useEffect, useRef } from "react";
import { motion } from "motion/react";
import { Play, Pause, Download, Share2, RotateCcw, Loader2 } from "lucide-react";
import { Button } from "../components/ui/button";
import { useNavigate, useParams } from "react-router-dom";
import { getProject } from "../lib/api";

export default function FinalRender() {
  const navigate = useNavigate();
  const { projectId } = useParams<{ projectId: string }>();
  const videoRef = useRef<HTMLVideoElement>(null);

  const [loading, setLoading] = useState(true);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [clipCount, setClipCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    const poll = async () => {
      while (!cancelled) {
        try {
          const proj = await getProject(projectId);
          if (proj.status === "complete" && proj.output_uri) {
            if (!cancelled) {
              setVideoUrl(`/files/${proj.output_uri.replace(/^data\//, "")}`);
              setClipCount(proj.videos?.length ?? 0);
              setLoading(false);
            }
            return;
          }
          if (proj.status === "error") {
            if (!cancelled) {
              setError(proj.error || "Rendering failed");
              setLoading(false);
            }
            return;
          }
        } catch {
          // keep polling
        }
        await new Promise((r) => setTimeout(r, 2000));
      }
    };
    poll();
    return () => { cancelled = true; };
  }, [projectId]);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play();
      setPlaying(true);
    } else {
      videoRef.current.pause();
      setPlaying(false);
    }
  };

  const handleDownload = () => {
    if (!videoUrl) return;
    const a = document.createElement("a");
    a.href = videoUrl;
    a.download = `open-stitch-${projectId || "edit"}.mp4`;
    a.click();
  };

  const formatDuration = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#121212] flex flex-col items-center justify-center p-8">
        <motion.div
          className="text-center"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <motion.div
            className="inline-flex items-center justify-center w-24 h-24 bg-gradient-to-br from-[#7F00FF] to-[#4B0082] rounded-full mb-8"
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          >
            <Loader2 className="w-12 h-12 text-white" />
          </motion.div>
          <h1 className="text-4xl font-bold text-white mb-4">
            Rendering Your Final Video
          </h1>
          <p className="text-xl text-gray-400">
            Applying all your edits and creating the masterpiece
          </p>
        </motion.div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#121212] flex flex-col items-center justify-center p-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-white mb-4">Rendering Failed</h1>
          <p className="text-red-400 mb-8">{error}</p>
          <Button onClick={() => navigate("/upload")} className="bg-[#7F00FF] text-white">
            Start Over
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#121212] flex flex-col items-center justify-center p-8">
      <motion.div
        className="w-full max-w-6xl"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div className="text-center mb-8">
          <h1 className="text-5xl font-bold text-white mb-4">Your Video is Ready!</h1>
          <p className="text-xl text-gray-400">
            AI has completed your video with all custom edits
          </p>
        </div>

        <div className="bg-[#1a1a1a]/80 rounded-2xl border-2 border-[#7F00FF] p-8 mb-8 shadow-2xl shadow-[#7F00FF]/20">
          <div
            className="aspect-video bg-black rounded-xl flex items-center justify-center relative overflow-hidden cursor-pointer"
            onClick={togglePlay}
          >
            {videoUrl ? (
              <video
                ref={videoRef}
                src={videoUrl}
                className="w-full h-full object-contain"
                onLoadedMetadata={() => {
                  if (videoRef.current) setDuration(videoRef.current.duration);
                }}
                onEnded={() => setPlaying(false)}
              />
            ) : (
              <p className="text-gray-500">No video available</p>
            )}

            {!playing && videoUrl && (
              <motion.div
                className="absolute inset-0 flex items-center justify-center bg-black/30"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
              >
                <div className="w-20 h-20 bg-white/20 backdrop-blur rounded-full flex items-center justify-center">
                  <Play className="w-10 h-10 text-white ml-1" />
                </div>
              </motion.div>
            )}
          </div>

          <div className="mt-6 flex items-center justify-between">
            <div>
              <h3 className="text-white text-lg font-semibold">Open Stitch - Final Edit</h3>
              <p className="text-gray-400 text-sm">
                Duration: {formatDuration(duration)} {"\u00b7"} 1920x1080
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={togglePlay}
                className="border-gray-700 text-gray-300"
              >
                {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              </Button>
              <div className="bg-green-500/20 border border-green-500 text-green-400 px-4 py-2 rounded-full text-sm">
                All Edits Applied
              </div>
            </div>
          </div>
        </div>

        <div className="flex gap-4 justify-center flex-wrap">
          <Button
            onClick={handleDownload}
            className="bg-gradient-to-r from-[#7F00FF] to-[#4B0082] hover:from-[#6600CC] hover:to-[#3a0062] text-white px-8 py-6 text-lg"
          >
            <Download className="w-5 h-5 mr-2" />
            Download Video
          </Button>
          <Button
            onClick={() => navigate("/upload")}
            className="bg-[#242424] hover:bg-[#2a2a2a] text-white px-8 py-6 text-lg border border-gray-700"
          >
            <RotateCcw className="w-5 h-5 mr-2" />
            Start New Project
          </Button>
        </div>

        <motion.div
          className="mt-12 grid grid-cols-2 gap-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <div className="bg-[#1a1a1a] border border-gray-800 rounded-xl p-6 text-center">
            <div className="text-3xl font-bold text-[#7F00FF] mb-2">{clipCount}</div>
            <div className="text-gray-400">Source Videos</div>
          </div>
          <div className="bg-[#1a1a1a] border border-gray-800 rounded-xl p-6 text-center">
            <div className="text-3xl font-bold text-[#7F00FF] mb-2">{formatDuration(duration)}</div>
            <div className="text-gray-400">Total Duration</div>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}
