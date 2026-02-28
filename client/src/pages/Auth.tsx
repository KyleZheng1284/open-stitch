import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { Button } from "../components/ui/button";

export default function Auth() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#121212] flex items-center justify-center relative overflow-hidden px-4">
      {/* Subtle background glow */}
      <div className="absolute inset-0">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-[#7F00FF] opacity-10 blur-[120px] rounded-full" />
      </div>

      {/* Glassmorphism card */}
      <motion.div
        className="relative z-10 w-full max-w-md"
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div className="bg-[#1a1a1a]/80 backdrop-blur-xl border border-[#7F00FF]/30 rounded-2xl p-10 shadow-2xl shadow-[#7F00FF]/20">
          {/* Card Title */}
          <motion.h2
            className="text-3xl font-bold text-white mb-3 text-center"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            Sign In to Open Stitch
          </motion.h2>

          {/* Sub-text */}
          <motion.p
            className="text-gray-400 text-center mb-8 leading-relaxed"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            To access and edit your videos, please log in with your Google
            account.
          </motion.p>

          {/* Google Login Button */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
          >
            <Button
              className="w-full bg-white hover:bg-gray-100 text-gray-900 py-6 rounded-lg flex items-center justify-center gap-3 transition-all duration-300 shadow-lg hover:shadow-xl"
              onClick={() => navigate("/upload")}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 48 48"
                className="w-6 h-6"
              >
                <path
                  fill="#FFC107"
                  d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z"
                />
                <path
                  fill="#FF3D00"
                  d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z"
                />
                <path
                  fill="#4CAF50"
                  d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z"
                />
                <path
                  fill="#1976D2"
                  d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z"
                />
              </svg>
              <span className="text-lg">Continue with Google</span>
            </Button>
          </motion.div>

          {/* Decorative elements */}
          <div className="absolute -top-4 -left-4 w-24 h-24 border-2 border-[#7F00FF]/20 rounded-full" />
          <div className="absolute -bottom-4 -right-4 w-32 h-32 border-2 border-[#7F00FF]/20 rounded-full" />
        </div>
      </motion.div>
    </div>
  );
}