import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        canvas: {
          bg: "#0f1117",
          surface: "#1a1d27",
          border: "#2a2d3a",
          accent: "#3b82f6",
        },
        status: {
          idle: "#6b7280",
          running: "#3b82f6",
          success: "#22c55e",
          error: "#ef4444",
          warning: "#f59e0b",
        },
      },
      animation: {
        "pulse-border": "pulse-border 2s ease-in-out infinite",
        "flow-dot": "flow-dot 1.5s ease-in-out infinite",
      },
      keyframes: {
        "pulse-border": {
          "0%, 100%": { borderColor: "rgba(59, 130, 246, 0.3)" },
          "50%": { borderColor: "rgba(59, 130, 246, 0.8)" },
        },
        "flow-dot": {
          "0%": { offsetDistance: "0%" },
          "100%": { offsetDistance: "100%" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
