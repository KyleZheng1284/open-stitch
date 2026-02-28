import { useState, useCallback } from "react";
import { listDriveFiles } from "../lib/api";

interface DriveFile {
  id: string;
  name: string;
  mime_type: string;
  size_bytes: number;
  thumbnail_url: string;
  duration_s: number;
}

export function useDrive() {
  const [files, setFiles] = useState<DriveFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [nextPageToken, setNextPageToken] = useState<string | undefined>();

  const loadFiles = useCallback(async (pageToken?: string) => {
    setLoading(true);
    try {
      const data = await listDriveFiles(pageToken);
      if (pageToken) {
        setFiles((prev) => [...prev, ...data.files]);
      } else {
        setFiles(data.files);
      }
      setNextPageToken(data.next_page_token || undefined);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMore = useCallback(() => {
    if (nextPageToken) loadFiles(nextPageToken);
  }, [nextPageToken, loadFiles]);

  return { files, loading, loadFiles, loadMore, hasMore: !!nextPageToken };
}
