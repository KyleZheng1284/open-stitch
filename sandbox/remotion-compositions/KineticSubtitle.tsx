import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

interface KeyframeData {
  time_ms: number;
  scale?: number;
  opacity?: number;
  easing?: string;
}

interface KineticSubtitleProps {
  text: string;
  style: string | Record<string, any>;
  position: string;
  keyframes?: KeyframeData[];
}

/**
 * Kinetic subtitle component with per-word animation.
 * Supports style presets from config/subtitle_styles.yaml:
 * - tiktok_pop: Bold white + yellow highlight, pop-in animation
 * - minimal: Clean white, no animation
 * - karaoke: Word-by-word color fill
 * - outline: White text with black stroke
 */
export const KineticSubtitle: React.FC<KineticSubtitleProps> = ({
  text,
  style,
  position,
  keyframes,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const styleName = typeof style === "string" ? style : "tiktok_pop";

  // Position mapping
  const positionStyle: React.CSSProperties = (() => {
    switch (position) {
      case "center":
        return { top: "50%", transform: "translateY(-50%)" };
      case "top":
        return { top: "10%" };
      case "center_bottom":
      default:
        return { bottom: "15%" };
    }
  })();

  // Style presets
  const textStyle: React.CSSProperties = (() => {
    const base: React.CSSProperties = {
      fontFamily: "Montserrat, Arial, sans-serif",
      textAlign: "center",
      width: "90%",
      marginLeft: "5%",
      lineHeight: 1.3,
      wordWrap: "break-word",
    };

    switch (styleName) {
      case "tiktok_pop":
        return {
          ...base,
          fontSize: 48,
          fontWeight: 800,
          color: "#FFFFFF",
          textShadow: "3px 3px 6px rgba(0,0,0,0.8)",
          WebkitTextStroke: "1px rgba(0,0,0,0.3)",
        };
      case "minimal":
        return {
          ...base,
          fontSize: 36,
          fontWeight: 500,
          color: "#FFFFFF",
          textShadow: "1px 1px 3px rgba(0,0,0,0.5)",
        };
      case "karaoke":
        return {
          ...base,
          fontSize: 44,
          fontWeight: 700,
          color: "#FFD700",
          textShadow: "2px 2px 4px rgba(0,0,0,0.7)",
        };
      case "outline":
        return {
          ...base,
          fontSize: 42,
          fontWeight: 700,
          color: "#FFFFFF",
          WebkitTextStroke: "2px #000000",
          textShadow: "none",
        };
      default:
        return {
          ...base,
          fontSize: 44,
          fontWeight: 700,
          color: "#FFFFFF",
        };
    }
  })();

  // Entrance animation
  let animatedScale = 1;
  let animatedOpacity = 1;

  if (styleName === "tiktok_pop") {
    const s = spring({ frame, fps, config: { damping: 12, stiffness: 200 } });
    animatedScale = interpolate(s, [0, 1], [0.5, 1]);
    animatedOpacity = interpolate(frame, [0, 6], [0, 1], {
      extrapolateRight: "clamp",
    });
  }

  // Custom keyframe overrides
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
        if (kf.opacity !== undefined && nextKf.opacity !== undefined) {
          animatedOpacity = interpolate(progress, [0, 1], [kf.opacity, nextKf.opacity]);
        }
        break;
      }
    }
  }

  return (
    <AbsoluteFill
      style={{
        ...positionStyle,
        position: "absolute",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        style={{
          ...textStyle,
          transform: `scale(${animatedScale})`,
          opacity: animatedOpacity,
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};
