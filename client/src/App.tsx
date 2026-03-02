import { Routes, Route, Navigate } from "react-router-dom";
import Landing from "./pages/Landing";
import Upload from "./pages/Upload";
import Setup from "./pages/Setup";
import Progress from "./pages/Progress";
import Review from "./pages/Review";
import FinalRender from "./pages/FinalRender";
import DevNav from "./components/DevNav";

export default function App() {
  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100">
      <DevNav />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/setup/:projectId" element={<Setup />} />
        <Route path="/progress/:projectId" element={<Progress />} />
        <Route path="/review" element={<Review />} />
        <Route path="/review/:projectId" element={<Review />} />
        <Route path="/final-render" element={<FinalRender />} />
        <Route path="/final-render/:projectId" element={<FinalRender />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}