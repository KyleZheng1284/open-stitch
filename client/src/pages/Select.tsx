import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listDriveFiles, downloadFiles, createProject } from "../lib/api";

interface DriveFile {
  id: string;
  name: string;
  size_bytes: number;
  thumbnail_url: string;
  duration_s: number;
}

export default function Select() {
  const navigate = useNavigate();
  const [files, setFiles] = useState<DriveFile[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    listDriveFiles()
      .then((data) => setFiles(data.files))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const handleContinue = async () => {
    if (selected.size === 0) return;
    setCreating(true);
    try {
      const ids = Array.from(selected);
      await downloadFiles(ids);
      const project = await createProject(ids);
      navigate(`/setup/${project.id}`);
    } catch (e) {
      console.error(e);
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-neutral-400">Loading your videos...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-12 px-6">
      <h1 className="text-3xl font-bold mb-2">Select Videos</h1>
      <p className="text-neutral-400 mb-8">Choose mp4 files from your Google Drive</p>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
        {files.map((f) => (
          <button
            key={f.id}
            onClick={() => toggle(f.id)}
            className={`relative rounded-xl border-2 p-3 text-left transition ${
              selected.has(f.id)
                ? "border-blue-500 bg-blue-500/10"
                : "border-neutral-800 bg-neutral-900 hover:border-neutral-600"
            }`}
          >
            {f.thumbnail_url && (
              <img
                src={f.thumbnail_url}
                alt={f.name}
                className="w-full h-32 object-cover rounded-lg mb-2"
              />
            )}
            <p className="text-sm font-medium truncate">{f.name}</p>
            <p className="text-xs text-neutral-500">
              {f.duration_s > 0 ? `${Math.round(f.duration_s)}s` : ""}{" "}
              {f.size_bytes > 0 ? `${(f.size_bytes / 1e6).toFixed(1)} MB` : ""}
            </p>
            {selected.has(f.id) && (
              <div className="absolute top-2 right-2 w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center text-xs font-bold">
                {Array.from(selected).indexOf(f.id) + 1}
              </div>
            )}
          </button>
        ))}
      </div>

      {files.length === 0 && (
        <p className="text-center text-neutral-500">No mp4 files found in your Drive</p>
      )}

      <div className="flex justify-end">
        <button
          onClick={handleContinue}
          disabled={selected.size === 0 || creating}
          className="px-6 py-3 bg-blue-600 rounded-lg font-semibold disabled:opacity-40 hover:bg-blue-500 transition"
        >
          {creating ? "Setting up..." : `Continue with ${selected.size} video${selected.size !== 1 ? "s" : ""}`}
        </button>
      </div>
    </div>
  );
}
