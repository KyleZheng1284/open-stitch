import React from "react";
import { Composition } from "remotion";
import { TimelineComposition } from "./TimelineComposition";

/**
 * Remotion entry point. Registers all compositions.
 * The sandbox server invokes `remotion render Root TimelineComposition`
 * with --props pointing to the timeline JSON written by the Assembly Agent.
 */
export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="TimelineComposition"
        component={TimelineComposition}
        durationInFrames={900} // overridden by calculateMetadata
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          clip_id: "",
          output: { format: "mp4", codec: "h264", width: 1080, height: 1920, fps: 30 },
          layers: [],
        }}
        calculateMetadata={async ({ props }) => {
          const fps = props.output?.fps || 30;
          const videoLayers = (props.layers || []).filter(
            (l: any) => l.type === "video"
          );
          const maxEndMs = videoLayers.reduce(
            (max: number, l: any) => Math.max(max, l.end_ms || 0),
            0
          );
          const durationInFrames = Math.max(
            1,
            Math.ceil((maxEndMs / 1000) * fps)
          );
          return {
            durationInFrames,
            fps,
            width: props.output?.width || 1080,
            height: props.output?.height || 1920,
          };
        }}
      />
    </>
  );
};
