import React from "react";
import { interpolate, useCurrentFrame, spring, useVideoConfig } from "remotion";

export const AnimatedHeadline: React.FC<{
  headline: string;
  sub?: string;
  enterAt?: number;
  yOffset?: number;
}> = ({ headline, sub, enterAt = 0, yOffset = 30 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const textIn = spring({
    frame: frame - enterAt,
    fps,
    config: { damping: 14, stiffness: 100 },
  });

  const subIn = spring({
    frame: frame - enterAt - 15,
    fps,
    config: { damping: 14, stiffness: 100 },
  });

  return (
    <div
      style={{
        position: "absolute",
        bottom: 80,
        left: 0,
        right: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 16,
        zIndex: 10,
      }}
    >
      <h1
        style={{
          color: "#ffffff",
          fontSize: 76,
          fontFamily: "system-ui, sans-serif",
          fontWeight: 800,
          textAlign: "center",
          margin: 0,
          opacity: textIn,
          transform: `translateY(${(1 - textIn) * yOffset}px)`,
          textShadow: "0 6px 30px rgba(0,0,0,0.9)",
          letterSpacing: "-0.5px",
        }}
      >
        {headline}
      </h1>
      {sub && (
        <p
          style={{
            color: "#67e8f9",
            fontSize: 42,
            fontFamily: "system-ui, sans-serif",
            fontWeight: 500,
            textAlign: "center",
            margin: 0,
            opacity: subIn,
            transform: `translateY(${(1 - subIn) * yOffset}px)`,
            textShadow: "0 2px 12px rgba(0,0,0,0.8)",
          }}
        >
          {sub}
        </p>
      )}
    </div>
  );
};
