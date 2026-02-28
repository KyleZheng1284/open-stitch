import { useEffect, useRef, useState } from "react";
import { createJobSocket } from "../lib/api";

export function useSocket(projectId: string | undefined) {
  const wsRef = useRef<WebSocket | null>(null);
  const [lastEvent, setLastEvent] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    if (!projectId) return;

    try {
      const ws = createJobSocket(projectId);
      wsRef.current = ws;

      ws.onmessage = (evt) => {
        try {
          setLastEvent(JSON.parse(evt.data));
        } catch {
          // ignore parse errors
        }
      };

      return () => ws.close();
    } catch {
      // WebSocket not available
    }
  }, [projectId]);

  return { lastEvent };
}
