import { useState, useCallback } from "react";
import { useNavigate } from "react-router";
import { motion } from "motion/react";
import { DndProvider, useDrag, useDrop } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { Plus, Send, Sparkles } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { ScrollArea } from "../components/ui/scroll-area";

interface VideoClip {
  id: string;
  name: string;
  thumbnail: string;
  duration: string;
}

interface Message {
  id: string;
  text: string;
  sender: "ai" | "user";
}

const DraggableClip = ({
  clip,
  index,
  moveClip,
}: {
  clip: VideoClip;
  index: number;
  moveClip: (dragIndex: number, hoverIndex: number) => void;
}) => {
  const [{ isDragging }, drag] = useDrag({
    type: "clip",
    item: { index },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  });

  const [, drop] = useDrop({
    accept: "clip",
    hover: (item: { index: number }) => {
      if (item.index !== index) {
        moveClip(item.index, index);
        item.index = index;
      }
    },
  });

  return (
    <motion.div
      ref={(node) => drag(drop(node))}
      className={`bg-[#242424] rounded-lg p-3 cursor-move border-2 border-transparent hover:border-[#7F00FF] transition-all ${
        isDragging ? "opacity-50" : "opacity-100"
      }`}
      whileHover={{ scale: 1.05 }}
    >
      <div className="aspect-video bg-gradient-to-br from-[#7F00FF]/20 to-[#4B0082]/20 rounded-lg mb-2 flex items-center justify-center">
        <div className="text-4xl">🎬</div>
      </div>
      <p className="text-white text-sm truncate">{clip.name}</p>
      <p className="text-gray-400 text-xs">{clip.duration}</p>
    </motion.div>
  );
};

function AssemblyContent() {
  const navigate = useNavigate();
  const [clips, setClips] = useState<VideoClip[]>([
    { id: "1", name: "intro-scene.mp4", thumbnail: "", duration: "0:15" },
    { id: "2", name: "main-action.mp4", thumbnail: "", duration: "1:23" },
    { id: "3", name: "closeup-shot.mp4", thumbnail: "", duration: "0:45" },
    { id: "4", name: "outro-scene.mp4", thumbnail: "", duration: "0:30" },
  ]);

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      text: "Hello! I'm your AI Video Assistant. Let me help you create something amazing. What is the primary mood of this video?",
      sender: "ai",
    },
  ]);

  const [inputValue, setInputValue] = useState("");

  const moveClip = useCallback((dragIndex: number, hoverIndex: number) => {
    setClips((prevClips) => {
      const newClips = [...prevClips];
      const [removed] = newClips.splice(dragIndex, 1);
      newClips.splice(hoverIndex, 0, removed);
      return newClips;
    });
  }, []);

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputValue,
      sender: "user",
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");

    // Simulate AI response
    setTimeout(() => {
      const aiResponses = [
        "Great choice! Do you want background music for this video?",
        "Perfect! What style are you aiming for - cinematic, energetic, or calm?",
        "Excellent! Would you like me to add transitions between clips?",
        "Understood! Let me help you refine the pacing. Any specific duration in mind?",
      ];
      const randomResponse =
        aiResponses[Math.floor(Math.random() * aiResponses.length)];
      
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: randomResponse,
        sender: "ai",
      };
      setMessages((prev) => [...prev, aiMessage]);
    }, 1000);
  };

  return (
    <div className="min-h-screen bg-[#121212] flex">
      {/* Main Content Area */}
      <div className="flex-1 p-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-white mb-2">
              Organize Your Clips
            </h1>
            <p className="text-gray-400">
              Drag and drop to reorder your video timeline
            </p>
          </div>

          {/* Video Timeline */}
          <div className="bg-[#1a1a1a]/80 rounded-2xl p-6 border border-gray-800 mb-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {clips.map((clip, index) => (
                <DraggableClip
                  key={clip.id}
                  clip={clip}
                  index={index}
                  moveClip={moveClip}
                />
              ))}
            </div>
          </div>

          {/* Add More Clips Button */}
          <Button
            variant="outline"
            className="w-full border-2 border-dashed border-gray-700 bg-transparent hover:bg-[#7F00FF]/10 hover:border-[#7F00FF] text-gray-400 hover:text-white py-8"
          >
            <Plus className="w-6 h-6 mr-2" />
            Add More Clips
          </Button>
        </motion.div>
      </div>

      {/* Right Sidebar - AI Assistant */}
      <motion.div
        className="w-96 bg-[#1a1a1a] border-l border-gray-800 flex flex-col"
        initial={{ x: 100, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.2 }}
      >
        {/* Sidebar Header */}
        <div className="p-6 border-b border-gray-800">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-gradient-to-br from-[#7F00FF] to-[#4B0082] rounded-full flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">AI Video Assistant</h3>
              <p className="text-xs text-gray-400">Always here to help</p>
            </div>
          </div>
        </div>

        {/* Chat Messages */}
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
                      ? "bg-[#7F00FF] text-white"
                      : "bg-[#242424] text-gray-200"
                  }`}
                >
                  <p className="text-sm">{message.text}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </ScrollArea>

        {/* Chat Input */}
        <div className="p-6 border-t border-gray-800">
          <div className="flex gap-2 mb-4">
            <Input
              placeholder="Type your message..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleSendMessage()}
              className="flex-1 bg-[#242424] border-gray-700 text-white"
            />
            <Button
              onClick={handleSendMessage}
              className="bg-[#7F00FF] hover:bg-[#6600CC] text-white"
            >
              <Send className="w-5 h-5" />
            </Button>
          </div>

          {/* Finalize Button */}
          <Button
            className="w-full bg-gradient-to-r from-[#7F00FF] to-[#4B0082] hover:from-[#6600CC] hover:to-[#3a0062] text-white py-6"
            onClick={() => navigate("/progress")}
          >
            Finalize & Stitch
          </Button>
        </div>
      </motion.div>
    </div>
  );
}

export default function Assembly() {
  return (
    <DndProvider backend={HTML5Backend}>
      <AssemblyContent />
    </DndProvider>
  );
}
