import { useNavigate } from "react-router";
import { motion } from "motion/react";
import { Button } from "../components/ui/button";

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#121212] flex items-center justify-center relative overflow-hidden">
      {/* Animated background pattern */}
      <div className="absolute inset-0 opacity-10">
        {[...Array(20)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-32 h-32 border border-[#7F00FF] rounded-lg"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
            }}
            animate={{
              x: [0, Math.random() * 100 - 50],
              y: [0, Math.random() * 100 - 50],
              rotate: [0, 360],
              scale: [1, 1.2, 1],
            }}
            transition={{
              duration: 20 + Math.random() * 10,
              repeat: Infinity,
              repeatType: "reverse",
            }}
          />
        ))}
      </div>

      {/* Main content */}
      <motion.div
        className="relative z-10 text-center px-8 max-w-4xl"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
      >
        {/* Logo/Title */}
        <motion.h1
          className="text-7xl font-bold mb-6 bg-gradient-to-r from-white to-[#7F00FF] bg-clip-text text-transparent"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1, delay: 0.2 }}
        >
          Open Stitch
        </motion.h1>

        {/* Tagline */}
        <motion.p
          className="text-2xl text-gray-300 mb-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.4 }}
        >
          The AI Video Assistant that turns raw footage into polished stories.
        </motion.p>

        {/* Description */}
        <motion.p
          className="text-lg text-gray-400 mb-12 max-w-2xl mx-auto leading-relaxed"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.6 }}
        >
          Open Stitch analyzes your videos, helps you organize them, and uses
          conversational AI to understand the mood, style, and structure you
          want. Upload, reorganize, and let our agents handle the editing flow.
        </motion.p>

        {/* CTA Button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.8 }}
        >
          <Button
            size="lg"
            className="bg-[#7F00FF] hover:bg-[#6600CC] text-white px-12 py-6 text-xl rounded-lg shadow-lg shadow-[#7F00FF]/50 transition-all duration-300 hover:shadow-[#7F00FF]/80 hover:scale-105"
            onClick={() => navigate("/auth")}
          >
            Log In to Begin
          </Button>
        </motion.div>
      </motion.div>
    </div>
  );
}
