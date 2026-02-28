import React from "react";
import {
  AbsoluteFill,
  OffthreadVideo,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

interface CropRegion {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface TransitionIn {
  type: string;
  duration_ms: number;
}

interface VideoLayerProps {
  src: string;
  speed?: number;
  crop?: CropRegion;
  transitionIn?: TransitionIn;
}

/**
 * Base video segment with crop, speed adjustment, and incoming transition.
 * Maps to a trimmed chunk of source footage at z=0.
 */
export const VideoLayer: React.FC<VideoLayerProps> = ({
  src,
  speed = 1.0,
  crop,
  transitionIn,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Transition entrance opacity
  let opacity = 1;
  if (transitionIn) {
    const transFrames = Math.round((transitionIn.duration_ms / 1000) * fps);
    if (transitionIn.type === "crossfade") {
      opacity = interpolate(frame, [0, transFrames], [0, 1], {
        extrapolateRight: "clamp",
      });
    }
  }

  // Crop transform: scale up and offset to simulate crop region
  const cropStyle: React.CSSProperties = crop
    ? {
        transform: `scale(${1 / crop.width}) translate(-${crop.x * 100}%, -${crop.y * 100}%)`,
        transformOrigin: "top left",
      }
    : {};

  return (
    <AbsoluteFill style={{ opacity }}>
      <AbsoluteFill style={cropStyle}>
        <OffthreadVideo
          src={src}
          playbackRate={speed}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
