import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { DndProvider, useDrag, useDrop } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { CloudUpload, Upload as UploadIcon, X, Send, Sparkles } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { ScrollArea } from "../components/ui/scroll-area";
import { uploadFiles } from "../lib/api";
import DriveUploader from "../components/DriveUploader";

interface UploadedFile {
  id: string;
  name: string;
  size: number;
  progress: number;
  order: number;
  thumbnail?: string;
  raw: File;
}

interface Message {
  id: string;
  text: string;
  sender: "ai" | "user";
}

const DraggableVideoCard = ({
  file,
  index,
  moveFile,
  onRemove,
}: {
  file: UploadedFile;
  index: number;
  moveFile: (dragIndex: number, hoverIndex: number) => void;
  onRemove: (id: string) => void;
}) => {
  const [{ isDragging }, drag] = useDrag({
    type: "video",
    item: { index },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  });

  const [, drop] = useDrop({
    accept: "video",
    hover: (item: { index: number }) => {
      if (item.index !== index) {
        moveFile(item.index, index);
        item.index = index;
      }
    },
  });

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  return (
    <motion.div
      ref={(node) => { drag(drop(node)); }}
      className={`relative bg-[#242424] rounded-lg p-4 border-2 transition-all cursor-move ${
        isDragging
          ? "opacity-50 border-[#7F00FF]"
          : "border-transparent hover:border-[#7F00FF]"
      }`}
      whileHover={{ scale: 1.02 }}
      layout
    >
      {/* Order Badge */}
      <div className="absolute -top-2 -left-2 w-8 h-8 bg-[#7F00FF] rounded-full flex items-center justify-center text-white font-bold text-sm z-10">
        #{index + 1}
      </div>

      {/* Remove Button */}
      <button
        onClick={() => onRemove(file.id)}
        className="absolute -top-2 -right-2 w-8 h-8 bg-red-500 hover:bg-red-600 rounded-full flex items-center justify-center text-white transition-colors z-10"
      >
        <X className="w-4 h-4" />
      </button>

      {/* Video Thumbnail */}
      <div className="aspect-video bg-gradient-to-br from-[#7F00FF]/20 to-[#4B0082]/20 rounded-lg mb-3 flex items-center justify-center overflow-hidden">
        {file.thumbnail ? (
          <img
            src={file.thumbnail}
            alt={file.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="text-5xl">🎬</div>
        )}
      </div>

      {/* File Info */}
      <p className="text-white text-sm font-medium truncate mb-1">{file.name}</p>
      <p className="text-gray-400 text-xs">{formatFileSize(file.size)}</p>

      {/* Progress Bar */}
      {file.progress < 100 && (
        <div className="mt-2">
          <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-[#7F00FF]"
              initial={{ width: 0 }}
              animate={{ width: `${file.progress}%` }}
            />
          </div>
          <p className="text-xs text-gray-400 mt-1">{file.progress.toFixed(0)}%</p>
        </div>
      )}
    </motion.div>
  );
};

function UploadContent() {
  const navigate = useNavigate();
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      text: "Hello! I'm your AI Video Assistant. Upload your videos and I'll help you create something amazing. What type of video are you working on today?",
      sender: "ai",
    },
  ]);
  const [inputValue, setInputValue] = useState("");

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(Array.from(e.dataTransfer.files));
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFiles(Array.from(e.target.files));
    }
  };

  const handleFiles = (files: File[]) => {
    const newFiles: UploadedFile[] = files.map((file, index) => ({
      id: Math.random().toString(36).substring(2, 11),
      name: file.name,
      size: file.size,
      progress: 0,
      order: uploadedFiles.length + index,
      thumbnail: undefined,
      raw: file,
    }));

    setUploadedFiles((prev) => [...prev, ...newFiles]);
    setError("");

    newFiles.forEach((uploadedFile) => {
      const file = files.find((f) => f.name === uploadedFile.name);
      if (file) {
        const video = document.createElement("video");
        video.preload = "metadata";
        video.muted = true;
        video.onloadeddata = () => { video.currentTime = 1; };
        video.onseeked = () => {
          const canvas = document.createElement("canvas");
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          const ctx = canvas.getContext("2d");
          if (ctx) {
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            setUploadedFiles((prev) =>
              prev.map((f) =>
                f.id === uploadedFile.id
                  ? { ...f, thumbnail: canvas.toDataURL("image/jpeg", 0.7) }
                  : f
              )
            );
          }
          video.src = "";
        };
        video.src = URL.createObjectURL(file);
      }

      // Animate progress bar
      let progress = 0;
      const interval = setInterval(() => {
        progress += Math.random() * 30;
        if (progress >= 100) {
          progress = 100;
          clearInterval(interval);
        }
        setUploadedFiles((prev) =>
          prev.map((f) => (f.id === uploadedFile.id ? { ...f, progress } : f))
        );
      }, 300);
    });
  };

  const moveFile = useCallback((dragIndex: number, hoverIndex: number) => {
    setUploadedFiles((prevFiles) => {
      const newFiles = [...prevFiles];
      const [removed] = newFiles.splice(dragIndex, 1);
      newFiles.splice(hoverIndex, 0, removed);
      return newFiles.map((file, index) => ({ ...file, order: index }));
    });
  }, []);

  const removeFile = (id: string) => {
    setUploadedFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;
    setMessages((prev) => [
      ...prev,
      { id: Date.now().toString(), text: inputValue, sender: "user" },
    ]);
    setInputValue("");
    setTimeout(() => {
      const responses = [
        "Great! What mood or style are you going for - energetic, calm, professional, or cinematic?",
        "Perfect! Do you want background music in your video?",
        "Excellent choice! Would you like me to add transitions between your clips?",
        "I understand. What's your target duration for the final video?",
        "Nice! Should I focus on any particular scenes or moments?",
        "Got it! Do you want any text overlays or captions?",
      ];
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          text: responses[Math.floor(Math.random() * responses.length)],
          sender: "ai",
        },
      ]);
    }, 1000);
  };

  const handleContinue = async () => {
    setUploading(true);
    setError("");
    try {
      const project = await uploadFiles(uploadedFiles.map((f) => f.raw));
      navigate(`/setup/${project.id}`);
    } catch (e: any) {
      setError(e.message || "Upload failed");
      setUploading(false);
    }
  };

  const allFilesReady =
    uploadedFiles.length > 0 && uploadedFiles.every((f) => f.progress === 100);

  return (
    <div className="min-h-screen bg-[#121212] flex">
      {/* Main Content Area */}
      <div className="flex-1 p-8 overflow-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          {/* Header */}
          <div className={`mb-8 ${uploadedFiles.length === 0 ? "text-center" : ""}`}>
            <h1 className="text-4xl font-bold text-white mb-2">
              Upload & Organize Your Videos
            </h1>
            <p className="text-gray-400">
              Upload your videos and drag to reorder them
            </p>
          </div>

          {/* Uploaded Videos Grid */}
          {uploadedFiles.length > 0 && (
            <motion.div
              className="bg-[#1a1a1a]/80 rounded-2xl p-6 border border-gray-800 mb-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <h3 className="text-xl font-bold text-white mb-4">
                Your Videos ({uploadedFiles.length})
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {uploadedFiles.map((file, index) => (
                  <DraggableVideoCard
                    key={file.id}
                    file={file}
                    index={index}
                    moveFile={moveFile}
                    onRemove={removeFile}
                  />
                ))}
              </div>
            </motion.div>
          )}

          {/* Upload Zone */}
          <motion.div
            className={`border-2 border-dashed rounded-xl transition-all duration-300 ${
              isDragging
                ? "border-[#7F00FF] bg-[#7F00FF]/10"
                : "border-gray-700 bg-[#1a1a1a]/50"
            } ${
              uploadedFiles.length === 0
                ? "p-20 min-h-[500px] flex items-center justify-center max-w-4xl mx-auto"
                : "p-8"
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            whileHover={{ scale: uploadedFiles.length === 0 ? 1.02 : 1.01 }}
          >
            <div className={`flex items-center justify-center gap-8 ${uploadedFiles.length === 0 ? "flex-col" : ""}`}>
              <motion.div
                animate={{ y: [0, -10, 0] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <CloudUpload
                  className={`text-[#7F00FF] ${uploadedFiles.length === 0 ? "w-32 h-32" : "w-16 h-16"}`}
                />
              </motion.div>

              <div className={uploadedFiles.length === 0 ? "text-center" : "text-left"}>
                <h3 className={`font-bold text-white mb-2 ${uploadedFiles.length === 0 ? "text-3xl" : "text-xl"}`}>
                  {uploadedFiles.length > 0 ? "Add More Videos" : "Drag & Drop Your Videos Here"}
                </h3>
                <p className={`text-gray-400 ${uploadedFiles.length === 0 ? "text-lg mb-6" : "text-sm mb-3"}`}>
                  Support for MP4, MOV, AVI, and more
                </p>

                <input
                  type="file"
                  id="fileInput"
                  className="hidden"
                  multiple
                  accept="video/*"
                  onChange={handleFileInput}
                />
                <Button
                  className={`bg-[#7F00FF] hover:bg-[#6600CC] text-white ${uploadedFiles.length === 0 ? "px-8 py-6 text-lg" : ""}`}
                  onClick={() => document.getElementById("fileInput")?.click()}
                >
                  <UploadIcon className={`mr-2 ${uploadedFiles.length === 0 ? "w-6 h-6" : "w-4 h-4"}`} />
                  Browse Files
                </Button>
              </div>
            </div>
          </motion.div>

          {error && (
            <p className="mt-4 text-red-400 text-sm text-center">{error}</p>
          )}

          {/* Continue Button */}
          {allFilesReady && (
            <motion.div
              className="mt-8 text-center"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <Button
                size="lg"
                className="bg-gradient-to-r from-[#7F00FF] to-[#4B0082] hover:from-[#6600CC] hover:to-[#3a0062] text-white px-12 py-6"
                onClick={handleContinue}
                disabled={uploading}
              >
                {uploading ? "Uploading..." : "Continue to Setup"}
              </Button>
            </motion.div>
          )}

          {/* Google Drive upload status — appears automatically once files are added */}
          <DriveUploader files={uploadedFiles.map((f) => f.raw)} />
        </motion.div>
      </div>

      {/* Right Sidebar - AI Video Assistant */}
      {uploadedFiles.length > 0 && (
        <motion.div
          className="w-96 bg-[#1a1a1a] border-l border-gray-800 flex flex-col"
          initial={{ x: 100, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          {/* Sidebar Header */}
          <div className="p-6 border-b border-gray-800">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-[#7F00FF] to-[#4B0082] rounded-full flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">AI Video Assistant</h3>
                <p className="text-xs text-gray-400">Ready to help you edit</p>
              </div>
            </div>
          </div>

          {/* Chat Messages */}
          <ScrollArea className="flex-1 p-6">
            <div className="space-y-4">
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}
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
            <div className="flex gap-2">
              <Input
                placeholder="Type your message..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
                className="flex-1 bg-[#242424] border-gray-700 text-white placeholder:text-gray-500"
              />
              <Button
                onClick={handleSendMessage}
                className="bg-[#7F00FF] hover:bg-[#6600CC] text-white"
                disabled={!inputValue.trim()}
              >
                <Send className="w-5 h-5" />
              </Button>
            </div>
            <p className="text-xs text-gray-500 mt-2 text-center">
              Ask me anything about your video editing needs
            </p>
          </div>
        </motion.div>
      )}
    </div>
  );
}

export default function Upload() {
  return (
    <DndProvider backend={HTML5Backend}>
      <UploadContent />
    </DndProvider>
  );
}
