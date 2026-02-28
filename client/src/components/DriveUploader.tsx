import { useCallback, useEffect, useRef, useState } from 'react';
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

interface Props {
  /**
   * File list owned by the parent upload UI (drag-and-drop / Browse Files).
   * DriveUploader watches this for newly added File objects and automatically
   * validates and uploads them — no separate file picker or upload button needed.
   */
  files: File[];
}

export default function DriveUploader({ files }: Props) {
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const { getAccessToken } = useGoogleDriveAuth();

  // Tracks which File object references have already been picked up so that
  // re-renders with the same array don't trigger duplicate uploads.
  const processedRef = useRef<Set<File>>(new Set());

  // Cached token — avoids repeated OAuth prompts within a session.
  // GIS tokens are valid for ~3600 s, which covers a normal upload session.
  const accessTokenRef = useRef<string | null>(null);

  /** Updates a single entry by File object identity (stable across re-renders). */
  const patchEntry = useCallback((file: File, patch: Partial<FileEntry>) => {
    setEntries((prev) => prev.map((e) => (e.file === file ? { ...e, ...patch } : e)));
  }, []);

  useEffect(() => {
    // Identify files the parent just added that we haven't seen before.
    const newFiles = files.filter((f) => !processedRef.current.has(f));
    if (newFiles.length === 0) return;

    // Mark immediately so a fast second render doesn't double-process.
    newFiles.forEach((f) => processedRef.current.add(f));

    // Add entries with initial validation status.
    setEntries((prev) => [
      ...prev,
      ...newFiles.map((file) => ({
        file,
        status: (isValid(file) ? 'ready' : 'invalid') as FileStatus,
      })),
    ]);

    const validBatch = newFiles.filter(isValid);
    if (validBatch.length === 0) return;

    // Fire-and-forget: start uploading without blocking the render cycle.
    void (async () => {
      try {
        if (!accessTokenRef.current) {
          accessTokenRef.current = await getAccessToken();
        }
        const token = accessTokenRef.current;
        const folderId = await getOrCreateUploadsFolderId(token);

        for (const file of validBatch) {
          patchEntry(file, { status: 'uploading' });
          try {
            const uploadUrl = await startResumableSession(token, file, folderId);
            const result = await uploadToSession(uploadUrl, file);
            patchEntry(file, { status: 'done', driveId: result.id });
          } catch (err) {
            patchEntry(file, {
              status: 'error',
              errorMsg: err instanceof Error ? err.message : String(err),
            });
          }
        }
      } catch (err) {
        // Auth or folder creation failed — clear cached token so the next
        // selection retries the OAuth flow rather than reusing a bad token.
        accessTokenRef.current = null;
        const msg = err instanceof Error ? err.message : String(err);
        for (const file of validBatch) {
          patchEntry(file, { status: 'error', errorMsg: msg });
        }
      }
    })();
  }, [files, getAccessToken, patchEntry]);

  // Render nothing until the parent feeds files in.
  if (entries.length === 0) return null;

  return (
    <div className="mt-6 pt-6 border-t border-neutral-800">
      <p className="text-xs text-neutral-500 mb-3 uppercase tracking-wide">
        Google Drive
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
  );
}
