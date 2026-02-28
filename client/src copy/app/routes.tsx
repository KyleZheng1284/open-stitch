import { createBrowserRouter } from "react-router";
import Landing from "./screens/Landing";
import Auth from "./screens/Auth";
import Upload from "./screens/Upload";
import Assembly from "./screens/Assembly";
import Progress from "./screens/Progress";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Landing />,
  },
  {
    path: "/auth",
    element: <Auth />,
  },
  {
    path: "/upload",
    element: <Upload />,
  },
  {
    path: "/assembly",
    element: <Assembly />,
  },
  {
    path: "/progress",
    element: <Progress />,
  },
]);
