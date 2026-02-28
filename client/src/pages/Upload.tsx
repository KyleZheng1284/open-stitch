import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { uploadFiles } from "../lib/api";

export default function Upload() {
  const navigate = useNavigate();
  const [dragging, setDragging] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const addFiles = useCallback((incoming: FileList | null) => {
    if (!incoming) return;
    const valid = Array.from(incoming).filter((f) => {
      const ext = f.name.toLowerCase();
      return ext.endsWith(".mp4") || ext.endsWith(".mov");
    });
    setFiles((prev) => [...prev, ...valid]);
    setError("");
  }, []);

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setError("");
    try {
      const project = await uploadFiles(files);
      navigate(`/setup/${project.id}`);
    } catch (e: any) {
      setError(e.message || "Upload failed");
      setUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-16 px-6">
      <div className="text-center mb-10">
        <h1 className="text-5xl font-bold tracking-tight">Auto-Vid</h1>
        <p className="mt-3 text-neutral-400 text-lg">
          Upload videos, describe your vision, get an edited video back
        </p>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          addFiles(e.dataTransfer.files);
        }}
        className={`border-2 border-dashed rounded-2xl p-12 text-center transition cursor-pointer ${
          dragging
            ? "border-blue-500 bg-blue-500/10"
            : "border-neutral-700 hover:border-neutral-500"
        }`}
        onClick={() => {
          const input = document.createElement("input");
          input.type = "file";
          input.multiple = true;
          input.accept = ".mp4,.mov";
          input.onchange = () => addFiles(input.files);
          input.click();
        }}
      >
        <p className="text-neutral-300 text-lg font-medium">
          Drop mp4 or mov files here
        </p>
        <p className="text-neutral-500 text-sm mt-1">or click to browse</p>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="mt-6 space-y-2">
          {files.map((f, i) => (
            <div
              key={i}
              className="flex items-center justify-between bg-neutral-900 border border-neutral-800 rounded-lg px-4 py-3"
            >
              <div>
                <p className="text-sm font-medium">{f.name}</p>
                <p className="text-xs text-neutral-500">
                  {(f.size / 1e6).toFixed(1)} MB
                </p>
              </div>
              <button
                onClick={() => removeFile(i)}
                className="text-neutral-500 hover:text-red-400 text-sm"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}

      {error && (
        <p className="mt-4 text-red-400 text-sm text-center">{error}</p>
      )}

      {/* Upload button */}
      <div className="mt-8 flex justify-center">
        <button
          onClick={handleUpload}
          disabled={files.length === 0 || uploading}
          className="px-8 py-3 bg-blue-600 rounded-lg font-semibold text-lg disabled:opacity-40 hover:bg-blue-500 transition"
        >
          {uploading
            ? "Uploading..."
            : `Upload ${files.length} file${files.length !== 1 ? "s" : ""}`}
        </button>
      </div>
    </div>
  );
}
