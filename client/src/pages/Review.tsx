import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate, useLocation, useParams } from "react-router-dom";
import { motion, AnimatePresence } from "motion/react";
import {
  Film,
  ArrowLeft,
  Send,
  X,
  Check,
  Activity,
} from "lucide-react";
import aiAssistantPfp from "../assets/ai-video-assistant-pfp.png";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { ScrollArea } from "../components/ui/scroll-area";
import TraceTreeModal from "../components/TraceTreeModal";

interface VideoClip {
  id: string;
  name: string;
  thumbnail?: string;
  duration: string;
  position: { x: number; y: number };
  edits: string[];
}

interface Transition {
  id: string;
  from: string;
  to: string;
  type: string;
  edits: string[];
}

interface Message {
  id: string;
  text: string;
  sender: "ai" | "user";
}

type ViewMode = "overview" | "clip" | "transition";

export default function Review() {
  const navigate = useNavigate();
  const location = useLocation();
  const { projectId } = useParams<{ projectId: string }>();
  const uploadedClips = location.state?.uploadedClips || [];

  const [viewMode, setViewMode] = useState<ViewMode>("overview");
  const [selectedClip, setSelectedClip] = useState<VideoClip | null>(null);
  const [selectedTransition, setSelectedTransition] =
    useState<Transition | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [traceOpen, setTraceOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [clips, setClips] = useState<VideoClip[]>(() => {
    if (uploadedClips.length > 0) {
      const spacing = 450;
      const startX = 200;
      const centerY = 300;

      return uploadedClips.map((clip: any, index: number) => ({
        id: clip.id,
        name: clip.name,
        thumbnail: clip.thumbnail,
        duration: clip.duration || "0:15",
        position: { x: startX + index * spacing, y: centerY },
        edits: [],
      }));
    }
    return [
      {
        id: "1",
        name: "Clip 1",
        thumbnail: undefined,
        duration: "0:15",
        position: { x: 200, y: 300 },
        edits: [],
      },
      {
        id: "2",
        name: "Clip 2",
        thumbnail: undefined,
        duration: "0:22",
        position: { x: 650, y: 300 },
        edits: [],
      },
      {
        id: "3",
        name: "Clip 3",
        thumbnail: undefined,
        duration: "0:18",
        position: { x: 1100, y: 300 },
        edits: [],
      },
    ];
  });

  const [transitions, setTransitions] = useState<Transition[]>(() => {
    const trans: Transition[] = [];
    for (let i = 0; i < clips.length - 1; i++) {
      trans.push({
        id: `t${i + 1}`,
        from: clips[i].id,
        to: clips[i + 1].id,
        type: "Fade",
        edits: [],
      });
    }
    return trans;
  });

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const closeTrace = useCallback(() => setTraceOpen(false), []);

  const handleClipClick = (clip: VideoClip) => {
    setSelectedClip(clip);
    setViewMode("clip");
    setMessages([
      {
        id: "1",
        text: `I'm ready to help you edit "${clip.name}". What changes would you like to make? You can ask me to adjust color grading, add effects, trim the clip, or enhance the audio.`,
        sender: "ai",
      },
    ]);
  };

  const handleTransitionClick = (transition: Transition) => {
    const fromClip = clips.find((c) => c.id === transition.from);
    const toClip = clips.find((c) => c.id === transition.to);
    setSelectedTransition(transition);
    setViewMode("transition");
    setMessages([
      {
        id: "1",
        text: `Let's edit the transition between "${fromClip?.name}" and "${toClip?.name}". Current transition: ${transition.type}. You can change the transition style, add memes, adjust timing, or add text overlays.`,
        sender: "ai",
      },
    ]);
  };

  const handleBackToOverview = () => {
    setViewMode("overview");
    setSelectedClip(null);
    setSelectedTransition(null);
    setMessages([]);
    setInputValue("");
  };

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputValue,
      sender: "user",
    };

    setMessages((prev) => [...prev, userMessage]);

    setTimeout(() => {
      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        text:
          viewMode === "clip"
            ? `Great! I've applied those changes to ${selectedClip?.name}. The clip now has enhanced visuals and better audio quality. Would you like to make any other adjustments?`
            : `Perfect! I've updated the transition with your preferences. The connection between these clips now flows smoothly. Any other changes you'd like?`,
        sender: "ai",
      };
      setMessages((prev) => [...prev, aiResponse]);

      if (viewMode === "clip" && selectedClip) {
        setClips((prev) =>
          prev.map((c) =>
            c.id === selectedClip.id
              ? { ...c, edits: [...c.edits, inputValue] }
              : c
          )
        );
      } else if (viewMode === "transition" && selectedTransition) {
        setTransitions((prev) =>
          prev.map((t) =>
            t.id === selectedTransition.id
              ? { ...t, edits: [...t.edits, inputValue] }
              : t
          )
        );
      }
    }, 1000);

    setInputValue("");
  };

  const handleFinishEditing = () => {
    navigate("/final-render");
  };

  const getConnectionPath = (transition: Transition) => {
    const fromClip = clips.find((c) => c.id === transition.from);
    const toClip = clips.find((c) => c.id === transition.to);
    if (!fromClip || !toClip) return null;

    const x1 = fromClip.position.x + 320;
    const y1 = fromClip.position.y + 125;
    const x2 = toClip.position.x - 20;
    const y2 = toClip.position.y + 125;

    return { x1, y1, x2, y2 };
  };

  return (
    <div className="h-screen bg-[#121212] flex flex-col overflow-hidden">
      {/* Header */}
      <div className="bg-[#1a1a1a] border-b border-gray-800 p-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Review & Edit</h1>
          <p className="text-gray-400">
            Click on clips or transitions to make AI-powered edits
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={() => setTraceOpen(true)}
            className="border-gray-700 text-gray-300 hover:text-white hover:bg-[#242424]"
          >
            <Activity className="w-4 h-4 mr-2 text-blue-400" />
            View Trace
          </Button>
          {viewMode === "overview" && (
            <Button
              onClick={handleFinishEditing}
              className="bg-gradient-to-r from-[#7F00FF] to-[#4B0082] hover:from-[#6600CC] hover:to-[#3a0062] text-white px-8 py-6"
            >
              <Check className="w-5 h-5 mr-2" />
              Finish Editing
            </Button>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Canvas Area */}
        <div className="flex-1 relative overflow-hidden">
          <AnimatePresence mode="wait">
            {viewMode === "overview" && (
              <OverviewMode
                clips={clips}
                transitions={transitions}
                onClipClick={handleClipClick}
                onTransitionClick={handleTransitionClick}
                getConnectionPath={getConnectionPath}
              />
            )}

            {viewMode === "clip" && selectedClip && (
              <ClipEditMode clip={selectedClip} onBack={handleBackToOverview} />
            )}

            {viewMode === "transition" && selectedTransition && (
              <TransitionEditMode
                transition={selectedTransition}
                clips={clips}
                onBack={handleBackToOverview}
              />
            )}
          </AnimatePresence>
        </div>

        {/* Chatbot Sidebar */}
        {viewMode !== "overview" && (
          <motion.div
            className="w-96 bg-[#1a1a1a] border-l border-gray-800 flex flex-col"
            initial={{ x: 400 }}
            animate={{ x: 0 }}
            exit={{ x: 400 }}
            transition={{ type: "spring", damping: 25 }}
          >
            {/* Chat Header */}
            <div className="p-6 border-b border-gray-800 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <img
                  src={aiAssistantPfp}
                  alt="AI Editor"
                  className="w-10 h-10 rounded-full object-cover object-center shrink-0"
                />
                <div>
                  <h3 className="text-white font-semibold">AI Editor</h3>
                  <p className="text-gray-400 text-sm">
                    {viewMode === "clip" ? "Clip Editing" : "Transition Editing"}
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleBackToOverview}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </Button>
            </div>

            {/* Messages */}
            <ScrollArea className="flex-1 p-6">
              <div className="space-y-4">
                {messages.map((message) => (
                  <motion.div
                    key={message.id}
                    className={`flex ${
                      message.sender === "user" ? "justify-end" : "justify-start"
                    }`}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    <div
                      className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                        message.sender === "user"
                          ? "bg-gradient-to-r from-[#7F00FF] to-[#4B0082] text-white"
                          : "bg-[#242424] text-gray-200"
                      }`}
                    >
                      {message.text}
                    </div>
                  </motion.div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            {/* Input */}
            <div className="p-6 border-t border-gray-800">
              <div className="flex gap-2">
                <Input
                  placeholder="Describe your edits..."
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
                  className="bg-[#242424] border-gray-700 text-white"
                />
                <Button
                  onClick={handleSendMessage}
                  className="bg-gradient-to-r from-[#7F00FF] to-[#4B0082] hover:from-[#6600CC] hover:to-[#3a0062]"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </div>

      {projectId && (
        <TraceTreeModal
          projectId={projectId}
          open={traceOpen}
          onClose={closeTrace}
        />
      )}
    </div>
  );
}

function OverviewMode({
  clips,
  transitions,
  onClipClick,
  onTransitionClick,
  getConnectionPath,
}: {
  clips: VideoClip[];
  transitions: Transition[];
  onClipClick: (clip: VideoClip) => void;
  onTransitionClick: (transition: Transition) => void;
  getConnectionPath: (transition: Transition) => any;
}) {
  return (
    <motion.div
      key="overview"
      className="w-full h-full flex items-center justify-center p-8 overflow-auto"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
    >
      <div className="relative" style={{ minWidth: "1600px", minHeight: "700px" }}>
        <div className="absolute inset-0">
          <svg width="100%" height="100%">
            <defs>
              <pattern
                id="dot-pattern"
                width="30"
                height="30"
                patternUnits="userSpaceOnUse"
              >
                <circle cx="2" cy="2" r="1.5" fill="rgba(255,255,255,0.15)" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#dot-pattern)" />
          </svg>
        </div>

        <svg className="absolute inset-0 w-full h-full" style={{ zIndex: 1 }}>
          {transitions.map((transition) => {
            const path = getConnectionPath(transition);
            if (!path) return null;

            const midX = (path.x1 + path.x2) / 2;
            const midY = (path.y1 + path.y2) / 2;

            return (
              <g key={transition.id}>
                <line
                  x1={path.x1}
                  y1={path.y1}
                  x2={path.x2}
                  y2={path.y2}
                  stroke="white"
                  strokeWidth="3"
                  style={{ cursor: "pointer" }}
                  onClick={() => onTransitionClick(transition)}
                />
                <circle
                  cx={midX}
                  cy={midY}
                  r="16"
                  fill="#1a1a1a"
                  stroke="white"
                  strokeWidth="2"
                  className="cursor-pointer hover:fill-[#7F00FF] transition-colors"
                  onClick={() => onTransitionClick(transition)}
                />
                <g
                  onClick={() => onTransitionClick(transition)}
                  style={{ cursor: "pointer" }}
                >
                  <line
                    x1={midX - 6}
                    y1={midY}
                    x2={midX + 6}
                    y2={midY}
                    stroke="white"
                    strokeWidth="2"
                  />
                  <line
                    x1={midX}
                    y1={midY - 6}
                    x2={midX}
                    y2={midY + 6}
                    stroke="white"
                    strokeWidth="2"
                  />
                </g>
                {transition.edits.length > 0 && (
                  <g>
                    <circle cx={midX + 12} cy={midY - 12} r="10" fill="#10b981" />
                    <text
                      x={midX + 12}
                      y={midY - 8}
                      textAnchor="middle"
                      fill="white"
                      fontSize="10"
                      fontWeight="bold"
                    >
                      {transition.edits.length}
                    </text>
                  </g>
                )}
              </g>
            );
          })}
        </svg>

        {clips.map((clip, index) => (
          <motion.div
            key={clip.id}
            className="absolute"
            style={{ left: clip.position.x, top: clip.position.y, zIndex: 10 }}
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.1 }}
          >
            <div
              onClick={() => onClipClick(clip)}
              className="w-[300px] bg-[#1a1a1a] border-2 border-gray-700 rounded-xl overflow-hidden cursor-pointer hover:border-white hover:shadow-lg hover:shadow-white/20 transition-all group"
            >
              <div className="relative">
                {clip.thumbnail ? (
                  <img
                    src={clip.thumbnail}
                    alt={clip.name}
                    className="w-full h-[200px] object-cover"
                  />
                ) : (
                  <div className="w-full h-[200px] bg-gradient-to-br from-[#7F00FF]/20 to-[#4B0082]/20 flex items-center justify-center">
                    <div className="text-6xl">🎬</div>
                  </div>
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <div className="text-white text-sm font-semibold">
                    Click to Edit
                  </div>
                </div>
                {clip.edits.length > 0 && (
                  <div className="absolute top-2 right-2 bg-green-500 text-white text-xs px-2 py-1 rounded-full flex items-center gap-1">
                    <Check className="w-3 h-3" />
                    {clip.edits.length} edit{clip.edits.length > 1 ? "s" : ""}
                  </div>
                )}
              </div>

              <div className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Film className="w-5 h-5 text-white" />
                    <span className="text-white font-semibold">{clip.name}</span>
                  </div>
                  <span className="text-gray-400 text-sm">{clip.duration}</span>
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}

function ClipEditMode({
  clip,
  onBack,
}: {
  clip: VideoClip;
  onBack: () => void;
}) {
  return (
    <motion.div
      key="clip-edit"
      className="w-full h-full flex flex-col items-center justify-center p-8"
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
    >
      <Button
        onClick={onBack}
        className="absolute top-8 left-8 bg-[#242424] hover:bg-[#2a2a2a] text-white"
      >
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Overview
      </Button>

      <div className="max-w-4xl w-full">
        <div className="bg-[#1a1a1a] border-2 border-[#7F00FF] rounded-2xl overflow-hidden shadow-2xl shadow-[#7F00FF]/30">
          {clip.thumbnail ? (
            <img
              src={clip.thumbnail}
              alt={clip.name}
              className="w-full h-[500px] object-cover"
            />
          ) : (
            <div className="w-full h-[500px] bg-gradient-to-br from-[#7F00FF]/20 to-[#4B0082]/20 flex items-center justify-center">
              <div className="text-9xl">🎬</div>
            </div>
          )}
          <div className="p-6 bg-gradient-to-t from-[#1a1a1a] to-transparent">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-white mb-1">
                  {clip.name}
                </h2>
                <p className="text-gray-400">Duration: {clip.duration}</p>
              </div>
              {clip.edits.length > 0 && (
                <div className="bg-green-500/20 border border-green-500 text-green-400 px-4 py-2 rounded-full">
                  {clip.edits.length} edit{clip.edits.length > 1 ? "s" : ""} applied
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function TransitionEditMode({
  transition,
  clips,
  onBack,
}: {
  transition: Transition;
  clips: VideoClip[];
  onBack: () => void;
}) {
  const fromClip = clips.find((c) => c.id === transition.from);
  const toClip = clips.find((c) => c.id === transition.to);

  return (
    <motion.div
      key="transition-edit"
      className="w-full h-full flex flex-col items-center justify-center p-8"
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
    >
      <Button
        onClick={onBack}
        className="absolute top-8 left-8 bg-[#242424] hover:bg-[#2a2a2a] text-white"
      >
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Overview
      </Button>

      <div className="max-w-6xl w-full">
        <div className="flex items-center gap-6">
          <div className="flex-1">
            <div className="bg-[#1a1a1a] border-2 border-gray-800 rounded-xl overflow-hidden">
              {fromClip?.thumbnail ? (
                <img
                  src={fromClip.thumbnail}
                  alt={fromClip.name}
                  className="w-full h-[300px] object-cover"
                />
              ) : (
                <div className="w-full h-[300px] bg-gradient-to-br from-[#7F00FF]/20 to-[#4B0082]/20 flex items-center justify-center">
                  <div className="text-6xl">🎬</div>
                </div>
              )}
              <div className="p-4">
                <h3 className="text-white font-semibold">{fromClip?.name}</h3>
              </div>
            </div>
          </div>

          <div className="flex flex-col items-center gap-4">
            <div className="w-20 h-20 bg-gradient-to-br from-[#7F00FF] to-[#4B0082] rounded-full flex items-center justify-center">
              <div className="text-white text-3xl">→</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#7F00FF] px-4 py-2 rounded-full">
              <span className="text-white font-semibold">{transition.type}</span>
            </div>
            {transition.edits.length > 0 && (
              <div className="bg-green-500/20 border border-green-500 text-green-400 px-3 py-1 rounded-full text-sm">
                {transition.edits.length} edit{transition.edits.length > 1 ? "s" : ""}
              </div>
            )}
          </div>

          <div className="flex-1">
            <div className="bg-[#1a1a1a] border-2 border-gray-800 rounded-xl overflow-hidden">
              {toClip?.thumbnail ? (
                <img
                  src={toClip.thumbnail}
                  alt={toClip.name}
                  className="w-full h-[300px] object-cover"
                />
              ) : (
                <div className="w-full h-[300px] bg-gradient-to-br from-[#7F00FF]/20 to-[#4B0082]/20 flex items-center justify-center">
                  <div className="text-6xl">🎬</div>
                </div>
              )}
              <div className="p-4">
                <h3 className="text-white font-semibold">{toClip?.name}</h3>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 text-center">
          <p className="text-gray-400">
            Editing transition between {fromClip?.name} and {toClip?.name}
          </p>
        </div>
      </div>
    </motion.div>
  );
}
