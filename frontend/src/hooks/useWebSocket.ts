"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface AgentState {
  id: string;
  status: "idle" | "running" | "success" | "error";
  progress?: number;
  iteration?: number;
}

interface WebSocketEvent {
  type: string;
  [key: string]: unknown;
}

/**
 * WebSocket hook for real-time pipeline status updates.
 *
 * Connects to the backend WebSocket endpoint for a specific job and
 * maintains agent state that drives the React Flow canvas node status.
 */
export function useWebSocket(jobId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const [agentStates, setAgentStates] = useState<Record<string, AgentState>>({});
  const [events, setEvents] = useState<WebSocketEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  const connect = useCallback(() => {
    if (!jobId) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/api/v1/jobs/${jobId}/stream`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data: WebSocketEvent = JSON.parse(event.data);
        setEvents((prev) => [...prev, data]);

        // Update agent states based on event type
        switch (data.type) {
          case "job:status":
            // Update overall pipeline status
            break;
          case "job:react_iteration":
            setAgentStates((prev) => ({
              ...prev,
              "react-loop": {
                id: "react-loop",
                status: "running",
                iteration: data.iteration as number,
              },
            }));
            break;
          case "job:agent_log":
            setAgentStates((prev) => ({
              ...prev,
              [data.agent as string]: {
                id: data.agent as string,
                status: "running",
              },
            }));
            break;
          case "job:complete":
            // Mark all agents as success
            setAgentStates((prev) => {
              const updated = { ...prev };
              for (const key of Object.keys(updated)) {
                updated[key] = { ...updated[key], status: "success" };
              }
              return updated;
            });
            break;
          case "job:error":
            break;
        }
      } catch {
        // Ignore non-JSON messages
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    ws.onerror = () => {
      setIsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [jobId]);

  useEffect(() => {
    const cleanup = connect();
    return cleanup;
  }, [connect]);

  return { agentStates, events, isConnected };
}
