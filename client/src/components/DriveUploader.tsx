import { useRef, useState } from 'react';
import { useGoogleDriveAuth } from '../hooks/useGoogleDriveAuth';
import {
  getOrCreateUploadsFolderId,
  startResumableSession,
  uploadToSession,
} from '../lib/drive';

type FileStatus = 'ready' | 'invalid' | 'uploading' | 'done' | 'error';

interface FileEntry {
  file: File;
  status: FileStatus;
  driveId?: string;
  errorMsg?: string;
}

function isValid(file: File): boolean {
  const name = file.name.toLowerCase();
  return name.endsWith('.mp4') || name.endsWith('.mov');
}

function formatSize(bytes: number): string {
  if (bytes < 1_048_576) return `${(bytes / 1_024).toFixed(1)} KB`;
  return `${(bytes / 1_048_576).toFixed(1)} MB`;
}

const STATUS_STYLES: Record<FileStatus, string> = {
  ready:     'bg-green-500/15 text-green-400',
  invalid:   'bg-red-500/15 text-red-400',
  uploading: 'bg-blue-500/15 text-blue-400',
  done:      'bg-emerald-500/15 text-emerald-400',
  error:     'bg-red-500/15 text-red-400',
};

export default function DriveUploader() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [uploading, setUploading] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const { getAccessToken } = useGoogleDriveAuth();

  // Cache the access token across batches.
  //
  // useGoogleDriveAuth initialises the GIS TokenClient once and its callback
  // closes over the resolve/reject of the *first* Promise created by
  // getAccessToken(). Calling getAccessToken() a second time creates a new
  // Promise whose resolve2/reject2 are never called — the old callback still
  // fires resolve from batch 1, which is already settled. The second Promise
  // hangs forever, keeping uploading=true indefinitely.
  //
  // Caching the token here means getAccessToken() is called at most once per
  // page load. GIS tokens are valid for ~3600 s, which is fine for a session.
  const accessTokenRef = useRef<string | null>(null);

  /** Update a single entry by File object identity. */
  const patchEntry = (file: File, patch: Partial<FileEntry>) => {
    setEntries((prev) => prev.map((e) => (e.file === file ? { ...e, ...patch } : e)));
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? []);
    if (selected.length === 0) return;

    setEntries((prev) => [
      ...prev,
      ...selected.map((file) => ({
        file,
        status: (isValid(file) ? 'ready' : 'invalid') as FileStatus,
      })),
    ]);

    // Reset so the same file can be re-selected if needed.
    e.target.value = '';
  };

  const handleUpload = async () => {
    // Capture File references (not entry objects) at click time so the loop
    // target is a stable, closed-over list regardless of state updates mid-run.
    const targetFiles = entries
      .filter((e) => e.status === 'ready')
      .map((e) => e.file);

    if (targetFiles.length === 0) return;

    setUploading(true);
    setGlobalError(null);

    try {
      // Reuse a cached token if available; otherwise acquire one (first batch).
      if (!accessTokenRef.current) {
        accessTokenRef.current = await getAccessToken();
      }
      const token = accessTokenRef.current;
      const folderId = await getOrCreateUploadsFolderId(token);

      for (const file of targetFiles) {
        patchEntry(file, { status: 'uploading' });
        try {
          const uploadUrl = await startResumableSession(token, file, folderId);
          const result = await uploadToSession(uploadUrl, file);
          patchEntry(file, { status: 'done', driveId: result.id });
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err);
          patchEntry(file, { status: 'error', errorMsg: msg });
        }
      }
    } catch (err) {
      // Auth or folder-creation failed; clear cached token so next attempt
      // retries the OAuth flow rather than reusing a potentially bad token.
      accessTokenRef.current = null;
      setGlobalError(err instanceof Error ? err.message : String(err));
    } finally {
      // Guaranteed to run even if an unexpected error escapes the inner catches.
      setUploading(false);
    }
  };

  const readyCount = entries.filter((e) => e.status === 'ready').length;
  const invalidCount = entries.filter((e) => e.status === 'invalid').length;

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

      <div className="flex items-center gap-3 flex-wrap">
        <button
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          className="px-5 py-2.5 rounded-lg bg-neutral-800 border border-neutral-700 text-sm font-medium hover:bg-neutral-700 disabled:opacity-40 transition"
        >
          Select videos
        </button>

        <button
          onClick={handleUpload}
          disabled={readyCount === 0 || uploading}
          className="px-5 py-2.5 rounded-lg bg-blue-600 text-sm font-medium hover:bg-blue-500 disabled:opacity-40 transition"
        >
          {uploading
            ? 'Uploading\u2026'
            : `Upload ${readyCount} to Drive`}
        </button>
      </div>

      {globalError && (
        <p className="mt-3 text-sm text-red-400">{globalError}</p>
      )}

      {/* File status list */}
      {entries.length > 0 && (
        <div className="mt-6">
          <p className="text-xs text-neutral-500 mb-3">
            {readyCount} ready&nbsp;&nbsp;·&nbsp;&nbsp;{invalidCount} invalid
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

                  {entry.status === 'done' && entry.driveId && (
                    <a
                      href={`https://drive.google.com/file/d/${entry.driveId}/view`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-400 hover:text-blue-300 mt-1 inline-block"
                    >
                      Open in Drive ↗
                    </a>
                  )}

                  {entry.status === 'error' && entry.errorMsg && (
                    <p
                      className="text-xs text-red-400 mt-1 truncate"
                      title={entry.errorMsg}
                    >
                      {entry.errorMsg}
                    </p>
                  )}
                </div>

                <span
                  className={`ml-4 shrink-0 text-xs font-semibold px-2.5 py-1 rounded-full ${STATUS_STYLES[entry.status]}`}
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
