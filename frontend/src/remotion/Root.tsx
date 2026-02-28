import React from "react";
import { Composition } from "remotion";
import { TimelineComposition } from "./TimelineComposition";

/**
 * Frontend Remotion entry point.
 * Used with @remotion/player for in-browser preview (stretch goal).
 */
export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="TimelineComposition"
        component={TimelineComposition}
        durationInFrames={900}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          clip_id: "",
          output: { format: "mp4", codec: "h264", width: 1080, height: 1920, fps: 30 },
          layers: [],
        }}
      />
    </>
  );
};
