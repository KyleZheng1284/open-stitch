import { useEffect } from "react";
import { useTraceStore } from "../stores/traceStore";
import type { TraceEvent } from "../types/trace";

const EVENT_TYPES = [
  "pipeline.start",
  "pipeline.end",
  "ingestion.start",
  "ingestion.end",
  "ingestion.complete",
  "summary.start",
  "summary.end",
  "asr.start",
  "asr.end",
  "vlm.start",
  "vlm.end",
  "agent.start",
  "agent.end",
  "llm.start",
  "llm.chunk",
  "llm.end",
  "tool.start",
  "tool.end",
  "render.start",
  "render.end",
] as const;

/**
 * Connect to the SSE trace stream for a project and feed events
 * into the Zustand store. EventSource handles reconnection natively
 * using the Last-Event-ID header.
 *
 * The store tracks activeProjectId so navigating away and back to
 * the same project preserves all accumulated trace state. Only
 * resets when switching to a different project.
 */
export function useTraceEvents(projectId: string | undefined) {
  const handleEvent = useTraceStore((s) => s.handleEvent);
  const resetForProject = useTraceStore((s) => s.resetForProject);

  useEffect(() => {
    if (!projectId) return;

    resetForProject(projectId);

    const es = new EventSource(`/api/jobs/${projectId}/events`);

    function onEvent(evt: MessageEvent) {
      try {
        const event: TraceEvent = JSON.parse(evt.data);
        handleEvent(event);
      } catch {
        // skip malformed events
      }
    }

    for (const type of EVENT_TYPES) {
      es.addEventListener(type, onEvent as EventListener);
    }

    return () => {
      es.close();
    };
  }, [projectId, handleEvent, resetForProject]);
}
