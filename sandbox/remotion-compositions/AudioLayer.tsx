import React, { useCallback } from "react";
import { Audio, interpolate, useVideoConfig } from "remotion";

interface AudioLayerProps {
  src: string;
  volume?: number;
  fadeInFrames?: number;
  fadeOutFrames?: number;
}

/**
 * Renders a single audio track (music, SFX) within a Sequence.
 * Supports base volume, fade-in, and fade-out via Remotion's
 * volume callback + interpolate.
 *
 * When placed inside <Sequence from={X}>, useVideoConfig().durationInFrames
 * returns the remaining composition frames (totalFrames - X), so fade-out
 * timing is relative to the composition end automatically.
 */
export const AudioLayer: React.FC<AudioLayerProps> = ({
  src,
  volume: baseVolume = 0.8,
  fadeInFrames = 0,
  fadeOutFrames = 0,
}) => {
  const { durationInFrames } = useVideoConfig();

  const volumeFn = useCallback(
    (frame: number) => {
      let v = baseVolume;

      if (fadeInFrames > 0) {
        v *= interpolate(frame, [0, fadeInFrames], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
      }

      if (fadeOutFrames > 0 && durationInFrames > fadeOutFrames) {
        const fadeStart = durationInFrames - fadeOutFrames;
        v *= interpolate(frame, [fadeStart, durationInFrames], [1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
      }

      return v;
    },
    [baseVolume, fadeInFrames, fadeOutFrames, durationInFrames],
  );

  if (fadeInFrames > 0 || fadeOutFrames > 0) {
    return <Audio src={src} volume={volumeFn} />;
  }

  return <Audio src={src} volume={baseVolume} />;
};
