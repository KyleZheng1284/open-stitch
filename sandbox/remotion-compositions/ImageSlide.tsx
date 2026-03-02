import React from "react";
import {
  AbsoluteFill,
  Img,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

interface ImageSlideProps {
  src: string;
  animation?: string;
}

export const ImageSlide: React.FC<ImageSlideProps> = ({
  src,
  animation = "ken_burns",
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const progress = durationInFrames > 1
    ? interpolate(frame, [0, durationInFrames - 1], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 0;

  let transform = "";
  let opacity = 1;

  switch (animation) {
    case "ken_burns": {
      const scale = interpolate(progress, [0, 1], [1.0, 1.15]);
      const tx = interpolate(progress, [0, 1], [0, -3]);
      const ty = interpolate(progress, [0, 1], [0, -2]);
      transform = `scale(${scale}) translate(${tx}%, ${ty}%)`;
      break;
    }
    case "zoom_in": {
      const scale = interpolate(progress, [0, 1], [1.0, 1.25]);
      transform = `scale(${scale})`;
      break;
    }
    case "pan_left": {
      const tx = interpolate(progress, [0, 1], [5, -5]);
      transform = `scale(1.15) translateX(${tx}%)`;
      break;
    }
    case "fade": {
      opacity = interpolate(frame, [0, Math.min(15, durationInFrames)], [0, 1], {
        extrapolateRight: "clamp",
      });
      transform = "scale(1.02)";
      break;
    }
    default:
      break;
  }

  if (!src) {
    return (
      <AbsoluteFill style={{ backgroundColor: "#1a1a1a" }} />
    );
  }

  return (
    <AbsoluteFill>
      <div
        style={{
          width: "100%",
          height: "100%",
          overflow: "hidden",
          opacity,
        }}
      >
        <Img
          src={src}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform,
            transformOrigin: "center center",
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
