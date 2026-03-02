import React from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

interface TransitionEffectProps {
  type: string;
}

/**
 * Between-segment transition effects.
 * Renders as an overlay during the transition duration.
 *
 * Types: crossfade, swipe_left, swipe_right, zoom_in, glitch, cut
 */
export const TransitionEffect: React.FC<TransitionEffectProps> = ({ type }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const progress = frame / durationInFrames;

  switch (type) {
    case "crossfade":
      return (
        <AbsoluteFill
          style={{
            backgroundColor: "black",
            opacity: interpolate(
              progress,
              [0, 0.5, 1],
              [0, 0.8, 0],
              { extrapolateRight: "clamp" }
            ),
          }}
        />
      );

    case "swipe_left":
      return (
        <AbsoluteFill
          style={{
            backgroundColor: "black",
            transform: `translateX(${interpolate(progress, [0, 1], [100, -100])}%)`,
          }}
        />
      );

    case "swipe_right":
      return (
        <AbsoluteFill
          style={{
            backgroundColor: "black",
            transform: `translateX(${interpolate(progress, [0, 1], [-100, 100])}%)`,
          }}
        />
      );

    case "zoom_in":
      return (
        <AbsoluteFill
          style={{
            backgroundColor: "black",
            opacity: interpolate(progress, [0, 0.3, 0.7, 1], [0, 0.5, 0.5, 0]),
            transform: `scale(${interpolate(progress, [0, 1], [1, 3])})`,
          }}
        />
      );

    case "glitch": {
      const flickerOpacity =
        Math.sin(frame * 8) > 0.3
          ? interpolate(progress, [0, 0.5, 1], [0, 0.6, 0])
          : 0;
      return (
        <AbsoluteFill
          style={{
            backgroundColor: `rgb(${Math.random() * 50}, ${Math.random() * 255}, ${Math.random() * 50})`,
            opacity: flickerOpacity,
            mixBlendMode: "screen",
          }}
        />
      );
    }

    case "cut":
    default:
      // No visual effect for hard cuts
      return null;
  }
};
