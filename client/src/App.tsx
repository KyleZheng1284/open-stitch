import { Routes, Route, Navigate } from "react-router-dom";
import Landing from "./pages/Landing";
import Auth from "./pages/Auth";
import Upload from "./pages/Upload";
import Setup from "./pages/Setup";
import Progress from "./pages/Progress";
import Review from "./pages/Review";

export default function App() {
  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100">
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/auth" element={<Auth />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/setup/:projectId" element={<Setup />} />
        <Route path="/progress/:projectId" element={<Progress />} />
        <Route path="/review/:projectId" element={<Review />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
