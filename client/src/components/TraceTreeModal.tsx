import { useEffect } from "react";
import { X } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { useTraceEvents } from "../hooks/useTraceEvents";
import { useTraceStore } from "../stores/traceStore";
import TraceTree from "./TraceTree";
import TraceDetailPanel from "./TraceDetailPanel";

interface TraceTreeModalProps {
  projectId: string;
  open: boolean;
  onClose: () => void;
}

export default function TraceTreeModal({
  projectId,
  open,
  onClose,
}: TraceTreeModalProps) {
  useTraceEvents(open ? projectId : undefined);
  const selectedNodeId = useTraceStore((s) => s.selectedNodeId);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-50 flex bg-neutral-950/90 backdrop-blur-sm"
        >
          <div className="flex-1 relative">
            <div className="absolute inset-0">
              <TraceTree />
            </div>

            <div className="absolute top-0 inset-x-0 p-5 flex items-start justify-between pointer-events-none z-10">
              <div>
                <h2 className="text-xl font-bold text-neutral-100">
                  Pipeline Trace
                </h2>
                <p className="text-neutral-400 text-sm mt-0.5">
                  Click any node to inspect its payload
                </p>
              </div>
              <button
                onClick={onClose}
                className="pointer-events-auto p-2 rounded-lg bg-neutral-900 border border-neutral-700 hover:bg-neutral-800 hover:border-neutral-600 text-neutral-400 hover:text-neutral-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {selectedNodeId && <TraceDetailPanel />}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
