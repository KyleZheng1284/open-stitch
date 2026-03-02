import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useDevStore } from "../stores/devStore";
import { ChevronUp, ChevronDown, FlaskConical } from "lucide-react";

const PAGES = [
  { label: "Landing", path: "/" },
  { label: "Upload", path: "/upload" },
  { label: "Setup", path: "/setup/demo" },
  { label: "Progress", path: "/progress/demo" },
  { label: "Review", path: "/review" },
  { label: "Final Render", path: "/final-render" },
];

export default function DevNav() {
  const devMode = useDevStore((s) => s.devMode);
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  if (!devMode) return null;

  return (
    <div className="fixed bottom-0 left-1/2 -translate-x-1/2 z-[9999] flex flex-col items-center">
      {open && (
        <div className="mb-2 bg-[#1a1a1a] border border-[#7F00FF]/50 rounded-xl px-4 py-3 shadow-2xl shadow-[#7F00FF]/20 flex flex-wrap gap-2 justify-center max-w-2xl">
          {PAGES.map((page) => {
            const active = location.pathname === page.path ||
              (page.path !== "/" && location.pathname.startsWith(page.path.replace("/demo", "")));
            return (
              <button
                key={page.path}
                onClick={() => navigate(page.path)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  active
                    ? "bg-[#7F00FF] text-white shadow-md shadow-[#7F00FF]/40"
                    : "bg-[#242424] text-gray-300 hover:bg-[#2f2f2f] hover:text-white border border-gray-700"
                }`}
              >
                {page.label}
              </button>
            );
          })}
        </div>
      )}

      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 bg-[#7F00FF] hover:bg-[#6600CC] text-white text-xs font-semibold px-4 py-2 rounded-t-xl shadow-lg shadow-[#7F00FF]/40 transition-colors select-none"
      >
        <FlaskConical className="w-3.5 h-3.5" />
        DEV MODE
        {open ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
      </button>
    </div>
  );
}