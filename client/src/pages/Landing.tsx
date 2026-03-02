import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "motion/react";
import { Button } from "../components/ui/button";
import { useDevStore } from "../stores/devStore";
import {
  FlaskConical,
  Scissors,
  Music,
  Wand2,
  Clock,
  CheckCircle2,
  Type,
} from "lucide-react";

// ── Micro-animation components ────────────────────────────────────

function WaveformBars() {
  const heights = [4, 7, 5, 9, 6, 8, 4, 7, 5, 6, 9, 5];
  return (
    <div className="flex items-end gap-[3px]" style={{ height: 32 }}>
      {heights.map((h, i) => (
        <motion.div
          key={i}
          className="w-1.5 rounded-full bg-[#7F00FF]"
          style={{ height: h * 3, transformOrigin: "bottom" }}
          animate={{ scaleY: [1, 1.8, 0.6, 1.3, 1] }}
          transition={{
            duration: 1.4,
            repeat: Infinity,
            delay: i * 0.08,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
}

function SceneBars() {
  const bars = [55, 80, 40, 70, 90, 50, 75];
  return (
    <div className="flex items-end gap-1 h-8">
      {bars.map((pct, i) => (
        <motion.div
          key={i}
          className="flex-1 rounded-[3px] bg-gradient-to-t from-[#7F00FF] to-violet-400"
          animate={{ height: [`${pct * 0.6}%`, `${pct}%`, `${pct * 0.75}%`] }}
          transition={{
            duration: 2.5,
            repeat: Infinity,
            delay: i * 0.2,
            ease: "easeInOut",
          }}
          style={{ height: `${pct * 0.6}%` }}
        />
      ))}
    </div>
  );
}

function MiniTimeline() {
  const tracks = [
    {
      label: "V1",
      clips: [
        { w: 44, color: "#7F00FF" },
        { w: 28, color: "#6366f1" },
        { w: 36, color: "#7F00FF" },
      ],
    },
    {
      label: "V2",
      clips: [
        { w: 20, color: "#4B0082" },
        { w: 48, color: "#7c3aed" },
        { w: 24, color: "#4B0082" },
      ],
    },
    {
      label: "AU",
      clips: [
        { w: 72, color: "#4f46e5" },
        { w: 36, color: "#4338ca" },
      ],
    },
  ];
  return (
    <div className="relative flex flex-col gap-1.5 overflow-hidden">
      {tracks.map((track, ti) => (
        <div key={ti} className="flex items-center gap-1.5">
          <span className="text-[9px] font-mono text-gray-500 w-4 shrink-0">
            {track.label}
          </span>
          <div className="flex gap-0.5 flex-1 h-3.5">
            {track.clips.map((c, i) => (
              <motion.div
                key={i}
                className="h-full rounded-[2px]"
                style={{ width: c.w, backgroundColor: c.color }}
                animate={{ opacity: [0.6, 1, 0.6] }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  delay: ti * 0.3 + i * 0.5,
                }}
              />
            ))}
          </div>
        </div>
      ))}
      {/* Animated playhead */}
      <motion.div
        className="absolute top-0 bottom-0 w-px bg-white/70 shadow-[0_0_4px_white]"
        style={{ left: "20%" }}
        animate={{ left: ["20%", "80%", "20%"] }}
        transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
}

const DIRECTOR_STEPS = [
  "Analyzing footage...",
  "Detecting scenes...",
  "Syncing audio...",
  "Applying cuts...",
  "Rendering preview...",
];

function DirectorStatus() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const id = setInterval(
      () => setStep((s) => (s + 1) % DIRECTOR_STEPS.length),
      2200
    );
    return () => clearInterval(id);
  }, []);
  return (
    <AnimatePresence mode="wait">
      <motion.p
        key={step}
        className="text-[11px] text-violet-300 font-mono"
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -6 }}
        transition={{ duration: 0.3 }}
      >
        {DIRECTOR_STEPS[step]}
      </motion.p>
    </AnimatePresence>
  );
}

const CAPTION_WORDS = ["Upload.", "Describe.", "Publish."];

function CaptionCycle() {
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    const id = setInterval(
      () => setIdx((i) => (i + 1) % CAPTION_WORDS.length),
      2000
    );
    return () => clearInterval(id);
  }, []);
  return (
    <div className="flex items-center gap-1.5 mt-1">
      <span className="text-[10px] text-gray-500">→</span>
      <AnimatePresence mode="wait">
        <motion.span
          key={idx}
          className="text-xs text-white font-medium"
          initial={{ opacity: 0, x: 8 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -8 }}
          transition={{ duration: 0.3 }}
        >
          {CAPTION_WORDS[idx]}
        </motion.span>
      </AnimatePresence>
    </div>
  );
}

// ── Floating card shell ───────────────────────────────────────────

function FloatCard({
  children,
  className = "",
  delay = 0,
  floatRange = 8,
  floatDuration = 5,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  floatRange?: number;
  floatDuration?: number;
}) {
  return (
    <motion.div
      className={`absolute pointer-events-none hidden lg:block ${className}`}
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, delay, ease: "easeOut" }}
    >
      <motion.div
        className="backdrop-blur-md bg-[#181818]/75 border border-white/[0.08] rounded-xl p-3.5 shadow-2xl shadow-black/50"
        animate={{ y: [0, -floatRange, 0] }}
        transition={{
          duration: floatDuration,
          repeat: Infinity,
          ease: "easeInOut",
          delay: delay + 0.8,
        }}
      >
        {children}
      </motion.div>
    </motion.div>
  );
}

function CardLabel({
  icon,
  label,
}: {
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <div className="flex items-center gap-2 mb-2.5">
      <div className="text-[#7F00FF]">{icon}</div>
      <span className="text-[11px] font-semibold text-gray-300 tracking-wide uppercase">
        {label}
      </span>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────

export default function Landing() {
  const navigate = useNavigate();
  const { devMode, setDevMode } = useDevStore();

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

      {/* Gradient blobs — sides only, z-0 */}
      <div className="absolute -top-40 -left-40 w-72 h-72 md:w-[28rem] md:h-[28rem] rounded-full bg-[#7F00FF] blur-3xl opacity-[0.18] pointer-events-none" />
      <div className="absolute -top-40 -right-40 w-72 h-72 md:w-[28rem] md:h-[28rem] rounded-full bg-indigo-700 blur-3xl opacity-[0.15] pointer-events-none" />
      <div className="absolute -bottom-40 left-1/2 -translate-x-1/2 w-72 h-72 md:w-[28rem] md:h-[28rem] rounded-full bg-[#3D0066] blur-3xl opacity-20 pointer-events-none" />

      {/* Dot-grid noise texture — z-5 */}
      <div className="absolute inset-0 z-[5] pointer-events-none bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.06)_1px,transparent_0)] [background-size:24px_24px]" />

      {/* Side vignettes — z-10 */}
      <div className="absolute inset-y-0 left-0 w-1/4 md:w-1/3 bg-gradient-to-r from-black/70 to-transparent pointer-events-none z-10" />
      <div className="absolute inset-y-0 right-0 w-1/4 md:w-1/3 bg-gradient-to-l from-black/70 to-transparent pointer-events-none z-10" />

      {/* ── LEFT FLOATING CARDS — z-[15] ── */}

      {/* Scene Analysis */}
      <FloatCard
        className="top-[18%] left-6 xl:left-14 w-44 z-[15]"
        delay={0.4}
        floatDuration={6}
      >
        <CardLabel
          icon={<Scissors className="w-3.5 h-3.5" />}
          label="Scene Analysis"
        />
        <SceneBars />
        <p className="text-[10px] text-gray-500 mt-2">12 scenes · 4K detected</p>
      </FloatCard>

      {/* Audio Sync */}
      <FloatCard
        className="top-[46%] -translate-y-1/2 left-4 xl:left-10 w-48 z-[15]"
        delay={0.7}
        floatRange={6}
        floatDuration={7}
      >
        <CardLabel
          icon={<Music className="w-3.5 h-3.5" />}
          label="Audio Sync"
        />
        <WaveformBars />
        <div className="flex items-center gap-1.5 mt-2">
          <motion.div
            className="w-1.5 h-1.5 rounded-full bg-green-400"
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
          <p className="text-[10px] text-green-400">Beat matched</p>
        </div>
      </FloatCard>

      {/* Caption Layer */}
      <FloatCard
        className="top-[74%] left-6 xl:left-14 w-44 z-[15]"
        delay={1.0}
        floatDuration={8}
      >
        <CardLabel
          icon={<Type className="w-3.5 h-3.5" />}
          label="Caption Layer"
        />
        <div className="bg-[#0f0f0f] rounded-lg px-2.5 py-2">
          <p className="text-[11px] text-white leading-relaxed">
            Word-level sync
          </p>
          <CaptionCycle />
        </div>
      </FloatCard>

      {/* ── RIGHT FLOATING CARDS — z-[15] ── */}

      {/* Director Agent */}
      <FloatCard
        className="top-[18%] right-6 xl:right-14 w-48 z-[15]"
        delay={0.5}
        floatDuration={5.5}
      >
        <CardLabel
          icon={<Wand2 className="w-3.5 h-3.5" />}
          label="Director Agent"
        />
        <div className="flex items-center gap-2 mb-1.5">
          <motion.div
            className="w-2 h-2 rounded-full bg-[#7F00FF]"
            animate={{ scale: [1, 1.5, 1], opacity: [1, 0.4, 1] }}
            transition={{ duration: 1.2, repeat: Infinity }}
          />
          <DirectorStatus />
        </div>
        <div className="h-1 bg-gray-800 rounded-full mt-2 overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-[#7F00FF] to-violet-400 rounded-full"
            animate={{ width: ["0%", "100%"] }}
            transition={{ duration: 11, repeat: Infinity, ease: "linear" }}
          />
        </div>
      </FloatCard>

      {/* Timeline */}
      <FloatCard
        className="top-[46%] -translate-y-1/2 right-4 xl:right-10 w-52 z-[15]"
        delay={0.8}
        floatRange={7}
        floatDuration={6.5}
      >
        <CardLabel
          icon={<Clock className="w-3.5 h-3.5" />}
          label="Timeline"
        />
        <MiniTimeline />
        <p className="text-[10px] text-gray-500 mt-2 font-mono">
          00:42 / 01:28
        </p>
      </FloatCard>

      {/* Export Ready */}
      <FloatCard
        className="top-[74%] right-6 xl:right-14 w-44 z-[15]"
        delay={1.1}
        floatDuration={7.5}
      >
        <CardLabel
          icon={<CheckCircle2 className="w-3.5 h-3.5" />}
          label="Export Ready"
        />
        {["TikTok", "Instagram", "YouTube"].map((platform, i) => (
          <motion.div
            key={platform}
            className="flex items-center gap-2 mb-1"
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 1.4 + i * 0.2 }}
          >
            <CheckCircle2 className="w-3 h-3 text-green-400 shrink-0" />
            <span className="text-[11px] text-gray-300">{platform}</span>
          </motion.div>
        ))}
      </FloatCard>

      {/* Dev mode toggle */}
      <button
        onClick={() => setDevMode(!devMode)}
        className={`absolute top-4 right-4 z-30 flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
          devMode
            ? "bg-[#7F00FF] border-[#7F00FF] text-white shadow-md shadow-[#7F00FF]/40"
            : "bg-[#1a1a1a]/80 border-gray-700 text-gray-400 hover:border-[#7F00FF]/50 hover:text-gray-200"
        }`}
      >
        <FlaskConical className="w-3.5 h-3.5" />
        Dev Mode
      </button>

      {/* Main content */}
      <motion.div
        className="relative z-20 text-center px-8 max-w-4xl"
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
            onClick={() => navigate("/upload")}
          >
            Get Started
          </Button>
        </motion.div>
      </motion.div>
    </div>
  );
}
