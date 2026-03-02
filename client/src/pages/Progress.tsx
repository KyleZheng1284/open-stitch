import { useNavigate, useParams } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { useTraceEvents } from "../hooks/useTraceEvents";
import { useTraceStore } from "../stores/traceStore";
import TraceTree from "../components/TraceTree";
import TraceDetailPanel from "../components/TraceDetailPanel";

export default function Progress() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  useTraceEvents(projectId);

  const jobStatus = useTraceStore((s) => s.jobStatus);
  const selectedNodeId = useTraceStore((s) => s.selectedNodeId);

  return (
    <div className="h-screen flex">
      <div className="flex-1 relative">
        <div className="absolute inset-0">
          <TraceTree />
        </div>

        <div className="absolute top-0 inset-x-0 p-6 pointer-events-none z-10">
          <h1 className="text-2xl font-bold">Creating Your Video</h1>
          <p className="text-neutral-400 text-sm mt-1">
            Watch the agent work in real-time
          </p>
        </div>

        {jobStatus === "complete" && (
          <div className="absolute bottom-8 inset-x-0 flex justify-center z-10">
            <button
              onClick={() => navigate(`/final-render/${projectId}`)}
              className="flex items-center gap-2 px-6 py-3 bg-green-600 hover:bg-green-500 text-white font-semibold rounded-xl shadow-lg shadow-green-600/20 transition-all hover:scale-[1.02]"
            >
              View Result
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {jobStatus === "error" && (
          <div className="absolute bottom-8 inset-x-0 flex justify-center z-10">
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-2 rounded-lg">
              Pipeline failed. Check the trace tree for details.
            </div>
          </div>
        )}
      </div>

      {selectedNodeId && <TraceDetailPanel />}
    </div>
  );
}
