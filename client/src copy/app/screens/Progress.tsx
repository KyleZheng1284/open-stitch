import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { CheckCircle2, Loader2 } from "lucide-react";

interface ProcessNode {
  id: string;
  label: string;
  status: "pending" | "processing" | "completed";
}

export default function Progress() {
  const [nodes, setNodes] = useState<ProcessNode[]>([
    { id: "1", label: "Scene Detection", status: "pending" },
    { id: "2", label: "Script Generation", status: "pending" },
    { id: "3", label: "Color Tuning", status: "pending" },
    { id: "4", label: "Final Render", status: "pending" },
  ]);

  useEffect(() => {
    // Simulate progressive completion
    const timeouts: NodeJS.Timeout[] = [];

    nodes.forEach((_, index) => {
      // Processing phase
      const processingTimeout = setTimeout(() => {
        setNodes((prev) =>
          prev.map((node, i) =>
            i === index ? { ...node, status: "processing" } : node
          )
        );
      }, index * 3000);

      // Completion phase
      const completionTimeout = setTimeout(() => {
        setNodes((prev) =>
          prev.map((node, i) =>
            i === index ? { ...node, status: "completed" } : node
          )
        );
      }, index * 3000 + 2500);

      timeouts.push(processingTimeout, completionTimeout);
    });

    return () => timeouts.forEach((timeout) => clearTimeout(timeout));
  }, []);

  const allCompleted = nodes.every((node) => node.status === "completed");

  return (
    <div className="min-h-screen bg-[#121212] flex items-center justify-center p-8">
      <motion.div
        className="w-full max-w-5xl"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        {/* Header */}
        <div className="text-center mb-16">
          <motion.h1
            className="text-4xl font-bold text-white mb-3"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {allCompleted
              ? "Your Video is Ready! 🎉"
              : "Processing Your Video..."}
          </motion.h1>
          <p className="text-gray-400">
            {allCompleted
              ? "All processing steps completed successfully"
              : "Our AI is working its magic on your footage"}
          </p>
        </div>

        {/* Process Flow */}
        <div className="relative">
          {/* Connection Lines */}
          <div className="absolute top-1/2 left-0 right-0 h-1 bg-gray-800 -translate-y-1/2 z-0">
            <motion.div
              className="h-full bg-gradient-to-r from-[#7F00FF] to-[#4B0082]"
              initial={{ width: "0%" }}
              animate={{
                width: allCompleted
                  ? "100%"
                  : `${
                      (nodes.filter((n) => n.status === "completed").length /
                        nodes.length) *
                      100
                    }%`,
              }}
              transition={{ duration: 0.5 }}
            />
          </div>

          {/* Nodes */}
          <div className="relative z-10 flex justify-between items-center">
            {nodes.map((node, index) => (
              <motion.div
                key={node.id}
                className="flex flex-col items-center"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                {/* Node Circle */}
                <motion.div
                  className={`w-24 h-24 rounded-full flex items-center justify-center mb-4 border-4 transition-all duration-500 ${
                    node.status === "completed"
                      ? "bg-[#7F00FF] border-[#7F00FF] shadow-lg shadow-[#7F00FF]/50"
                      : node.status === "processing"
                      ? "bg-[#7F00FF]/30 border-[#7F00FF] animate-pulse"
                      : "bg-[#242424] border-gray-700"
                  }`}
                  animate={
                    node.status === "processing"
                      ? { scale: [1, 1.1, 1] }
                      : {}
                  }
                  transition={{
                    duration: 1,
                    repeat: node.status === "processing" ? Infinity : 0,
                  }}
                >
                  {node.status === "completed" ? (
                    <CheckCircle2 className="w-12 h-12 text-white" />
                  ) : node.status === "processing" ? (
                    <Loader2 className="w-12 h-12 text-white animate-spin" />
                  ) : (
                    <div className="w-6 h-6 rounded-full bg-gray-600" />
                  )}
                </motion.div>

                {/* Node Label */}
                <p
                  className={`text-center font-medium transition-colors duration-300 ${
                    node.status === "completed"
                      ? "text-[#7F00FF]"
                      : node.status === "processing"
                      ? "text-white"
                      : "text-gray-500"
                  }`}
                >
                  {node.label}
                </p>

                {/* Status Text */}
                <p className="text-xs text-gray-400 mt-1">
                  {node.status === "completed"
                    ? "Complete"
                    : node.status === "processing"
                    ? "In Progress..."
                    : "Pending"}
                </p>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Progress Stats */}
        <motion.div
          className="mt-16 grid grid-cols-3 gap-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <div className="bg-[#1a1a1a]/80 rounded-xl p-6 border border-gray-800 text-center">
            <p className="text-gray-400 text-sm mb-2">Completion</p>
            <p className="text-3xl font-bold text-white">
              {Math.round(
                (nodes.filter((n) => n.status === "completed").length /
                  nodes.length) *
                  100
              )}
              %
            </p>
          </div>

          <div className="bg-[#1a1a1a]/80 rounded-xl p-6 border border-gray-800 text-center">
            <p className="text-gray-400 text-sm mb-2">Steps Completed</p>
            <p className="text-3xl font-bold text-white">
              {nodes.filter((n) => n.status === "completed").length} / {nodes.length}
            </p>
          </div>

          <div className="bg-[#1a1a1a]/80 rounded-xl p-6 border border-gray-800 text-center">
            <p className="text-gray-400 text-sm mb-2">Estimated Time</p>
            <p className="text-3xl font-bold text-white">
              {allCompleted ? "Done!" : "2-3 min"}
            </p>
          </div>
        </motion.div>

        {/* Completion Message */}
        {allCompleted && (
          <motion.div
            className="mt-8 bg-gradient-to-r from-[#7F00FF]/10 to-[#4B0082]/10 border border-[#7F00FF]/30 rounded-xl p-6 text-center"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.5 }}
          >
            <p className="text-lg text-white mb-2">
              Your video has been successfully processed!
            </p>
            <p className="text-gray-400">
              Download your video or share it with the world.
            </p>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}
