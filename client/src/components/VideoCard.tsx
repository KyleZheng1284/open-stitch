interface VideoInfo {
  id: string;
  filename: string;
  duration_s: number;
  summary: string;
  ingestion_status: string;
}

export default function VideoCard({
  video,
  index,
}: {
  video: VideoInfo;
  index: number;
}) {
  const isReady = video.ingestion_status === "complete";

  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-4">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 bg-neutral-800 rounded-lg flex items-center justify-center text-sm font-bold text-neutral-400 shrink-0">
          {index + 1}
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium truncate">{video.filename}</p>
          <p className="text-sm text-neutral-500">
            {video.duration_s > 0 ? `${Math.round(video.duration_s)}s` : ""}
          </p>
          {isReady && video.summary ? (
            <p className="mt-2 text-sm text-neutral-400 leading-relaxed">
              {video.summary}
            </p>
          ) : (
            <div className="mt-2 flex items-center gap-2">
              <div className="w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-neutral-500">Analyzing...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
