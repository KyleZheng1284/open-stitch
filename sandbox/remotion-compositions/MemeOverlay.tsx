import React from "react";
import {
  Img,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

interface KeyframeData {
  time_ms: number;
  scale?: number;
  y?: number;
  x?: number;
  opacity?: number;
  rotation?: number;
  easing?: string;
}

interface MemeOverlayProps {
  src: string;
  x: number;
  y: number;
  scale: number;
  rotation: number;
  opacity?: number;
  animation: string;
  keyframes?: KeyframeData[];
}

/**
 * Meme image/GIF overlay with position, rotation, scale, and entrance animation.
 * Coordinates come from VLM spatial grounding (subject bounding boxes).
 * Supports spring physics, bounce, and slide-down animations.
 */
export const MemeOverlay: React.FC<MemeOverlayProps> = ({
  src,
  x,
  y,
  scale,
  rotation,
  opacity = 1.0,
  animation,
  keyframes,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  let animatedScale = scale;
  let animatedY = y;
  let animatedOpacity = opacity;
  let animatedRotation = rotation;

  // Built-in animation presets
  switch (animation) {
    case "pop_in": {
      const s = spring({ frame, fps, config: { damping: 12, stiffness: 200 } });
      animatedScale = s * scale;
      animatedOpacity = interpolate(frame, [0, 5], [0, opacity], {
        extrapolateRight: "clamp",
      });
      break;
    }
    case "spring": {
      const s = spring({ frame, fps, config: { damping: 10, stiffness: 150 } });
      animatedScale = s * scale;
      break;
    }
    case "slide_down_and_bounce": {
      const progress = spring({
        frame,
        fps,
        config: { damping: 8, stiffness: 100 },
      });
      animatedY = interpolate(progress, [0, 1], [y - 0.3, y]);
      animatedOpacity = interpolate(frame, [0, 8], [0, opacity], {
        extrapolateRight: "clamp",
      });
      break;
    }
    case "shake": {
      const shakeAmount = interpolate(
        frame,
        [0, durationInFrames],
        [5, 0],
        { extrapolateRight: "clamp" }
      );
      animatedRotation =
        rotation + Math.sin(frame * 2) * shakeAmount;
      break;
    }
    case "fade": {
      animatedOpacity = interpolate(frame, [0, 10], [0, opacity], {
        extrapolateRight: "clamp",
      });
      break;
    }
  }

  // Custom keyframe overrides (if provided, they take precedence)
  if (keyframes && keyframes.length > 0) {
    const msPerFrame = 1000 / fps;
    const currentMs = frame * msPerFrame;

    for (let i = 0; i < keyframes.length - 1; i++) {
      const kf = keyframes[i];
      const nextKf = keyframes[i + 1];
      if (currentMs >= kf.time_ms && currentMs <= nextKf.time_ms) {
        const progress =
          (currentMs - kf.time_ms) / (nextKf.time_ms - kf.time_ms);
        if (kf.scale !== undefined && nextKf.scale !== undefined) {
          animatedScale = interpolate(progress, [0, 1], [kf.scale, nextKf.scale]);
        }
        if (kf.y !== undefined && nextKf.y !== undefined) {
          animatedY = interpolate(progress, [0, 1], [kf.y, nextKf.y]);
        }
        if (kf.opacity !== undefined && nextKf.opacity !== undefined) {
          animatedOpacity = interpolate(progress, [0, 1], [kf.opacity, nextKf.opacity]);
        }
        if (kf.rotation !== undefined && nextKf.rotation !== undefined) {
          animatedRotation = interpolate(progress, [0, 1], [kf.rotation, nextKf.rotation]);
        }
        break;
      }
    }
  }

  return (
    <Img
      src={src}
      style={{
        position: "absolute",
        left: `${x * 100}%`,
        top: `${animatedY * 100}%`,
        transform: `translate(-50%, -50%) scale(${animatedScale}) rotate(${animatedRotation}deg)`,
        opacity: animatedOpacity,
        pointerEvents: "none",
      }}
    />
  );
};
