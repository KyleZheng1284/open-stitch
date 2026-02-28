import { useRef, useState } from 'react';

type FileStatus = 'ready' | 'invalid';

interface FileEntry {
  file: File;
  status: FileStatus;
}

function isValid(file: File): boolean {
  const name = file.name.toLowerCase();
  return name.endsWith('.mp4') || name.endsWith('.mov');
}

function formatSize(bytes: number): string {
  if (bytes < 1_048_576) return `${(bytes / 1_024).toFixed(1)} KB`;
  return `${(bytes / 1_048_576).toFixed(1)} MB`;
}

export default function DriveUploader() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [entries, setEntries] = useState<FileEntry[]>([]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? []);
    if (selected.length === 0) return;

    setEntries((prev) => [
      ...prev,
      ...selected.map((file) => ({ file, status: isValid(file) ? 'ready' : 'invalid' as FileStatus })),
    ]);

    // Reset so the same file can be re-selected after removal.
    e.target.value = '';
  };

  const ready = entries.filter((e) => e.status === 'ready').length;
  const invalid = entries.filter((e) => e.status === 'invalid').length;

  return (
    <div className="mt-12 border-t border-neutral-800 pt-10">
      <h2 className="text-xl font-semibold mb-1">Upload to Google Drive</h2>
      <p className="text-sm text-neutral-500 mb-5">
        Select .mp4 or .mov files to upload to your Drive.
      </p>

      {/* Hidden native file input */}
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".mp4,.mov,video/mp4,video/quicktime"
        className="sr-only"
        onChange={handleChange}
      />

      <button
        onClick={() => inputRef.current?.click()}
        className="px-5 py-2.5 rounded-lg bg-neutral-800 border border-neutral-700 text-sm font-medium hover:bg-neutral-700 transition"
      >
        Select videos
      </button>

      {/* File status list */}
      {entries.length > 0 && (
        <div className="mt-6">
          {/* Summary counts */}
          <p className="text-xs text-neutral-500 mb-3">
            {ready} ready&nbsp;&nbsp;·&nbsp;&nbsp;{invalid} invalid
          </p>

          <ul className="space-y-2">
            {entries.map((entry, i) => (
              <li
                key={i}
                className="flex items-center justify-between bg-neutral-900 border border-neutral-800 rounded-lg px-4 py-3"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{entry.file.name}</p>
                  <p className="text-xs text-neutral-500 mt-0.5">
                    {formatSize(entry.file.size)}
                  </p>
                </div>

                <span
                  className={`ml-4 shrink-0 text-xs font-semibold px-2.5 py-1 rounded-full ${
                    entry.status === 'ready'
                      ? 'bg-green-500/15 text-green-400'
                      : 'bg-red-500/15 text-red-400'
                  }`}
                >
                  {entry.status}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
