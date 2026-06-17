import React from "react";
import { AbsoluteFill, Img, useCurrentFrame, interpolate, Easing } from "remotion";

export const DiagonalThemeReveal: React.FC<{
  darkSrc: string;
  lightSrc: string;
  enterAt: number;
  duration: number;
}> = ({ darkSrc, lightSrc, enterAt, duration }) => {
  const frame = useCurrentFrame();

  const progress = interpolate(
    frame,
    [enterAt, enterAt + duration],
    [-20, 120],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.inOut(Easing.cubic),
    }
  );

  return (
    <AbsoluteFill>
      <Img
        src={darkSrc}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          clipPath: `polygon(0 0, ${progress}% 0, ${progress - 20}% 100%, 0 100%)`,
        }}
      >
        <Img
          src={lightSrc}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
        {/* Glow edge */}
        <div
          style={{
            position: "absolute",
            top: 0,
            bottom: 0,
            right: 0,
            width: 4,
            background: "#fff",
            boxShadow: "0 0 20px 4px rgba(255,255,255,0.8)",
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
