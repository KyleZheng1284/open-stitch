// Google Drive API helpers for folder creation and resumable uploads.
// All calls are made directly from the browser using a GIS OAuth access token.

const DRIVE_FILES_URL = 'https://www.googleapis.com/drive/v3/files';
const DRIVE_UPLOAD_URL = 'https://www.googleapis.com/upload/drive/v3/files';
const DEFAULT_FOLDER_NAME = 'Open Stitch Uploads';
const FOLDER_MIME = 'application/vnd.google-apps.folder';

/** Infer MIME type from file extension when File.type is absent (e.g. .mov on some browsers). */
function inferMimeType(file: File): string {
  if (file.type) return file.type;
  const ext = file.name.split('.').pop()?.toLowerCase();
  if (ext === 'mov') return 'video/quicktime';
  if (ext === 'mp4') return 'video/mp4';
  return 'application/octet-stream';
}

/**
 * Returns the Drive folder ID for the given folder name, creating it if needed.
 * The ID is cached in localStorage keyed by folder name so we only call the
 * Drive API once per browser per unique folder name.
 *
 * @param token   GIS OAuth access token with the `drive.file` scope.
 * @param folderName  Display name of the target folder. Defaults to "Open Stitch Uploads".
 */
export async function getOrCreateUploadsFolderId(
  token: string,
  folderName: string = DEFAULT_FOLDER_NAME,
): Promise<string> {
  const cacheKey = `driveFolder:${folderName}`;
  const cached = localStorage.getItem(cacheKey);
  if (cached) return cached;

  const res = await fetch(DRIVE_FILES_URL, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      name: folderName,
      mimeType: FOLDER_MIME,
    }),
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Failed to create Drive folder "${folderName}" (${res.status}): ${detail}`);
  }

  const data = await res.json() as { id: string };
  localStorage.setItem(cacheKey, data.id);
  return data.id;
}

/**
 * Initiates a resumable upload session with Drive and returns the session URL.
 * The URL is taken from the `Location` header of the initiation response.
 */
export async function startResumableSession(
  token: string,
  file: File,
  folderId: string,
): Promise<string> {
  const mimeType = inferMimeType(file);

  const res = await fetch(`${DRIVE_UPLOAD_URL}?uploadType=resumable&fields=id,name`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      'X-Upload-Content-Type': mimeType,
      'X-Upload-Content-Length': String(file.size),
    },
    body: JSON.stringify({
      name: file.name,
      mimeType,
      parents: [folderId],
    }),
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Failed to start resumable session for "${file.name}" (${res.status}): ${detail}`);
  }

  const uploadUrl = res.headers.get('Location');
  if (!uploadUrl) {
    throw new Error(`Drive did not return a Location header for "${file.name}".`);
  }

  return uploadUrl;
}

/**
 * Uploads file bytes to an active resumable session URL.
 * Returns the Drive file metadata (`id` and `name`) from the final response.
 */
export async function uploadToSession(
  uploadUrl: string,
  file: File,
): Promise<{ id: string; name: string }> {
  const res = await fetch(uploadUrl, {
    method: 'PUT',
    headers: {
      'Content-Type': inferMimeType(file),
      'Content-Length': String(file.size),
    },
    body: file,
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Upload failed for "${file.name}" (${res.status}): ${detail}`);
  }

  return res.json() as Promise<{ id: string; name: string }>;
}
