import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { motion } from "motion/react";
import {
  Video,
  Music,
  Scissors,
  Sparkles,
  FileVideo,
  Wand2,
  Check,
  Loader2,
} from "lucide-react";

interface ProcessNode {
  id: string;
  label: string;
  icon: React.ReactNode;
  status: "pending" | "active" | "complete";
  position: { x: number; y: number };
  description: string;
}

export default function VisualizingProgress() {
  const navigate = useNavigate();
  const location = useLocation();
  const uploadedClips = location.state?.uploadedClips || [];
  const [progress, setProgress] = useState(0);
  const [nodes, setNodes] = useState<ProcessNode[]>([
    {
      id: "1",
      label: "Upload Analysis",
      icon: <Video className="w-6 h-6" />,
      status: "pending",
      position: { x: 100, y: 200 },
      description: "Analyzing uploaded videos",
    },
    {
      id: "2",
      label: "AI Processing",
      icon: <Sparkles className="w-6 h-6" />,
      status: "pending",
      position: { x: 300, y: 100 },
      description: "Processing with AI",
    },
    {
      id: "3",
      label: "Scene Detection",
      icon: <Scissors className="w-6 h-6" />,
      status: "pending",
      position: { x: 300, y: 300 },
      description: "Detecting key scenes",
    },
    {
      id: "4",
      label: "Music Sync",
      icon: <Music className="w-6 h-6" />,
      status: "pending",
      position: { x: 500, y: 150 },
      description: "Syncing background music",
    },
    {
      id: "5",
      label: "Transition Effects",
      icon: <Wand2 className="w-6 h-6" />,
      status: "pending",
      position: { x: 500, y: 250 },
      description: "Adding transitions",
    },
    {
      id: "6",
      label: "Final Render",
      icon: <FileVideo className="w-6 h-6" />,
      status: "pending",
      position: { x: 700, y: 200 },
      description: "Rendering final video",
    },
  ]);

  const connections = [
    { from: "1", to: "2" },
    { from: "1", to: "3" },
    { from: "2", to: "4" },
    { from: "3", to: "5" },
    { from: "4", to: "6" },
    { from: "5", to: "6" },
  ];

  useEffect(() => {
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(progressInterval);
          setTimeout(() => {
            navigate("/review", { state: { uploadedClips } });
          }, 1000);
          return 100;
        }
        return prev + 1;
      });
    }, 100);

    const nodeInterval = setInterval(() => {
      setNodes((prevNodes) => {
        return prevNodes.map((node, index) => {
          const nodeProgress = (index / prevNodes.length) * 100;
          const nextNodeProgress = ((index + 1) / prevNodes.length) * 100;
          if (progress >= nextNodeProgress) {
            return { ...node, status: "complete" as const };
          } else if (progress >= nodeProgress && progress < nextNodeProgress) {
            return { ...node, status: "active" as const };
          }
          return node;
        });
      });
    }, 100);

    return () => {
      clearInterval(progressInterval);
      clearInterval(nodeInterval);
    };
  }, [progress, navigate, uploadedClips]);

  const getNodeColor = (status: string) => {
    switch (status) {
      case "complete": return "from-green-500 to-emerald-600";
      case "active": return "from-[#7F00FF] to-[#4B0082]";
      default: return "from-gray-600 to-gray-700";
    }
  };

  const getNodeBorder = (status: string) => {
    switch (status) {
      case "complete": return "border-green-500";
      case "active": return "border-[#7F00FF] shadow-lg shadow-[#7F00FF]/50";
      default: return "border-gray-700";
    }
  };

  return (
    <div className="min-h-screen bg-[#121212] flex flex-col items-center justify-center p-8">
      <motion.div
        className="w-full max-w-6xl"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        {/* Header */}
        <div className="text-center mb-12">
          <motion.div
            className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-[#7F00FF] to-[#4B0082] rounded-full mb-6"
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          >
            <Loader2 className="w-10 h-10 text-white" />
          </motion.div>
          <h1 className="text-5xl font-bold text-white mb-4">
            Visualizing Progress
          </h1>
          <p className="text-xl text-gray-400">AI is crafting your perfect video</p>
        </div>

        {/* Progress Bar */}
        <div className="mb-12">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">Overall Progress</span>
            <span className="text-lg font-bold text-white">{progress}%</span>
          </div>
          <div className="h-3 bg-gray-800 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-[#7F00FF] to-[#4B0082]"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
        </div>

        {/* Node Graph */}
        <div className="relative bg-[#1a1a1a]/80 rounded-2xl border border-gray-800 p-8 min-h-[500px]">
          {/* Grid Background */}
          <div className="absolute inset-0 opacity-20">
            <svg width="100%" height="100%">
              <defs>
                <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="gray" strokeWidth="0.5" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#grid)" />
            </svg>
          </div>

          {/* Connection Lines */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none">
            {connections.map((conn, index) => {
              const fromNode = nodes.find((n) => n.id === conn.from);
              const toNode = nodes.find((n) => n.id === conn.to);
              if (!fromNode || !toNode) return null;
              const isActive = fromNode.status === "complete" || fromNode.status === "active";
              return (
                <motion.line
                  key={index}
                  x1={fromNode.position.x + 60}
                  y1={fromNode.position.y + 40}
                  x2={toNode.position.x + 60}
                  y2={toNode.position.y + 40}
                  stroke={isActive ? "#7F00FF" : "#4a5568"}
                  strokeWidth="2"
                  initial={{ opacity: 0.3 }}
                  animate={{ opacity: isActive ? 1 : 0.3 }}
                  transition={{ duration: 0.5 }}
                />
              );
            })}
          </svg>

          {/* Nodes */}
          {nodes.map((node) => (
            <motion.div
              key={node.id}
              className="absolute"
              style={{ left: node.position.x, top: node.position.y }}
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.3, delay: parseInt(node.id) * 0.1 }}
            >
              <div
                className={`relative bg-gradient-to-br ${getNodeColor(node.status)} rounded-xl p-4 border-2 ${getNodeBorder(node.status)} transition-all duration-300 w-32 h-32 flex flex-col items-center justify-center`}
              >
                {/* Status Indicator */}
                <div className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-[#121212] flex items-center justify-center">
                  {node.status === "complete" ? (
                    <Check className="w-4 h-4 text-green-500" />
                  ) : node.status === "active" ? (
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                    >
                      <Loader2 className="w-4 h-4 text-[#7F00FF]" />
                    </motion.div>
                  ) : (
                    <div className="w-2 h-2 rounded-full bg-gray-600" />
                  )}
                </div>
                <div className="text-white mb-2">{node.icon}</div>
                <p className="text-xs text-white text-center font-semibold leading-tight">
                  {node.label}
                </p>
              </div>

              {/* Description Tooltip */}
              {node.status === "active" && (
                <motion.div
                  className="absolute -bottom-12 left-1/2 transform -translate-x-1/2 bg-[#242424] text-white text-xs px-3 py-2 rounded-lg whitespace-nowrap"
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  {node.description}
                  <div className="absolute -top-1 left-1/2 transform -translate-x-1/2 w-2 h-2 bg-[#242424] rotate-45" />
                </motion.div>
              )}
            </motion.div>
          ))}
        </div>

        {/* Status Message */}
        <motion.div
          className="mt-8 text-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          <p className="text-gray-400">
            {progress < 33 && "Analyzing your video content..."}
            {progress >= 33 && progress < 66 && "Applying AI enhancements..."}
            {progress >= 66 && progress < 100 && "Finalizing your video..."}
            {progress === 100 && "Complete! Redirecting..."}
          </p>
        </motion.div>
      </motion.div>
    </div>
  );
}