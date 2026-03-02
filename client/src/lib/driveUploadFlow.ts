// UI-agnostic orchestration layer for uploading files to Google Drive.
// No React imports. Safe to use in any framework or plain TypeScript.

import {
  getOrCreateUploadsFolderId,
  startResumableSession,
  uploadToSession,
} from './drive';

const DEFAULT_FOLDER_NAME = 'Open Stitch Uploads';

export interface UploadResult {
  file: File;
  status: 'done' | 'error';
  /** Drive file ID — present when status is 'done'. */
  id?: string;
  /** Error message — present when status is 'error'. */
  error?: string;
}

/**
 * Called once per file as its status changes during the upload sequence.
 * `meta.id`    is set when status is 'done'.
 * `meta.error` is set when status is 'error'.
 */
export type UploadProgressCallback = (
  file: File,
  status: 'uploading' | 'done' | 'error',
  meta?: { id?: string; error?: string },
) => void;

export interface UploadFilesArgs {
  /** GIS OAuth access token with the drive.file scope. */
  token: string;
  /** Files to upload. Only files in this array are processed. */
  files: File[];
  /**
   * Name of the Drive folder to upload into.
   * Created if it does not already exist.
   * @default "Open Stitch Uploads"
   */
  folderName?: string;
  /**
   * Optional progress callback fired before and after each file upload.
   * Useful for driving UI state without coupling this module to any framework.
   */
  onProgress?: UploadProgressCallback;
}

/**
 * Uploads an array of files to Google Drive sequentially inside a named folder.
 *
 * - Resolves with a result record for every file regardless of per-file errors,
 *   so callers always receive the full picture.
 * - Throws only if folder creation fails (unrecoverable for the whole batch).
 *
 * @example
 * const results = await uploadFilesToDrive({
 *   token,
 *   files: readyFiles,
 *   onProgress: (file, status, meta) => console.log(file.name, status, meta),
 * });
 */
export async function uploadFilesToDrive({
  token,
  files,
  folderName = DEFAULT_FOLDER_NAME,
  onProgress,
}: UploadFilesArgs): Promise<UploadResult[]> {
  const folderId = await getOrCreateUploadsFolderId(token, folderName);
  const results: UploadResult[] = [];

  for (const file of files) {
    onProgress?.(file, 'uploading');
    try {
      const uploadUrl = await startResumableSession(token, file, folderId);
      const { id } = await uploadToSession(uploadUrl, file);
      results.push({ file, status: 'done', id });
      onProgress?.(file, 'done', { id });
    } catch (err) {
      const error = err instanceof Error ? err.message : String(err);
      results.push({ file, status: 'error', error });
      onProgress?.(file, 'error', { error });
    }
  }

  return results;
}
