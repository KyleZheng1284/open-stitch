import React from "react";
import { AbsoluteFill, Sequence, useVideoConfig } from "remotion";
import { VideoLayer } from "./VideoLayer";
import { MemeOverlay } from "./MemeOverlay";
import { KineticSubtitle } from "./KineticSubtitle";
import { TransitionEffect } from "./TransitionEffect";

/**
 * Main composition that reads TimelineJSON props and renders all layers
 * sorted by z_index. This is the 1:1 mapping from the Python
 * RemotionComposition -> React component tree.
 *
 * Audio layers are handled separately by FFmpeg post-render.
 */

interface TimelineLayer {
  type: string;
  z_index: number;
  source?: string;
  start_ms?: number;
  end_ms?: number;
  at_ms?: number;
  duration_ms?: number;
  crop?: { x: number; y: number; width: number; height: number };
  speed?: number;
  transition_in?: { type: string; duration_ms: number };
  position?: { x: number; y: number } | string;
  scale?: number;
  rotation?: number;
  opacity?: number;
  animation?: string;
  keyframes?: Array<Record<string, any>>;
  sound_effect?: string;
  text?: string;
  style?: string | Record<string, any>;
  volume?: number;
  duck_points?: Array<Record<string, any>>;
  fade_in_ms?: number;
  fade_out_ms?: number;
  pitch_shift?: number;
}

interface TimelineProps {
  clip_id: string;
  output: {
    format: string;
    codec: string;
    width: number;
    height: number;
    fps: number;
  };
  layers: TimelineLayer[];
}

export const TimelineComposition: React.FC<TimelineProps> = ({
  layers,
  output,
}) => {
  const { fps } = useVideoConfig();

  // Sort layers by z_index for proper stacking
  const sortedLayers = [...layers]
    .filter((l) => l.type !== "audio") // audio handled by FFmpeg
    .sort((a, b) => a.z_index - b.z_index);

  const msToFrames = (ms: number) => Math.round((ms / 1000) * fps);

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {sortedLayers.map((layer, idx) => {
        switch (layer.type) {
          case "video": {
            const from = msToFrames(layer.start_ms || 0);
            const duration = msToFrames(
              (layer.end_ms || 0) - (layer.start_ms || 0)
            );
            return (
              <Sequence key={`video-${idx}`} from={from} durationInFrames={duration}>
                <VideoLayer
                  src={layer.source || ""}
                  speed={layer.speed || 1.0}
                  crop={layer.crop}
                  transitionIn={layer.transition_in}
                />
              </Sequence>
            );
          }

          case "meme_overlay": {
            const from = msToFrames(layer.at_ms || 0);
            const duration = msToFrames(layer.duration_ms || 2000);
            const pos =
              typeof layer.position === "object" && layer.position !== null
                ? layer.position
                : { x: 0.5, y: 0.5 };
            return (
              <Sequence key={`overlay-${idx}`} from={from} durationInFrames={duration}>
                <MemeOverlay
                  src={layer.source || ""}
                  x={"x" in pos ? pos.x : 0.5}
                  y={"y" in pos ? pos.y : 0.5}
                  scale={layer.scale || 1.0}
                  rotation={layer.rotation || 0}
                  opacity={layer.opacity ?? 1.0}
                  animation={layer.animation || "none"}
                  keyframes={layer.keyframes}
                />
              </Sequence>
            );
          }

          case "subtitle": {
            const from = msToFrames(layer.start_ms || 0);
            const duration = msToFrames(
              (layer.end_ms || 0) - (layer.start_ms || 0)
            );
            return (
              <Sequence key={`sub-${idx}`} from={from} durationInFrames={duration}>
                <KineticSubtitle
                  text={layer.text || ""}
                  style={layer.style || "tiktok_pop"}
                  position={
                    typeof layer.position === "string"
                      ? layer.position
                      : "center_bottom"
                  }
                  keyframes={layer.keyframes}
                />
              </Sequence>
            );
          }

          case "transition": {
            const from = msToFrames(layer.at_ms || 0);
            const duration = msToFrames(layer.duration_ms || 500);
            return (
              <Sequence key={`trans-${idx}`} from={from} durationInFrames={duration}>
                <TransitionEffect
                  type={(layer as any).transition_type || "crossfade"}
                />
              </Sequence>
            );
          }

          default:
            return null;
        }
      })}
    </AbsoluteFill>
  );
};
