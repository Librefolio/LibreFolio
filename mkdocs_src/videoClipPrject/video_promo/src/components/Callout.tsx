import React from "react";
import { useCurrentFrame, spring, useVideoConfig } from "remotion";

export const Callout: React.FC<{
  label: string;
  x: number;
  y: number;
  enterAt: number;
  color?: string;
}> = ({ label, x, y, enterAt, color = "#67e8f9" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({
    frame: frame - enterAt,
    fps,
    config: { damping: 14, stiffness: 120 },
  });

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        transform: `scale(${scale})`,
        display: "flex",
        alignItems: "center",
        gap: 12,
        zIndex: 20,
      }}
    >
      <div
        style={{
          width: 16,
          height: 16,
          borderRadius: "50%",
          backgroundColor: color,
          boxShadow: `0 0 15px ${color}`,
        }}
      />
      <div
        style={{
          width: 60,
          height: 2,
          backgroundColor: color,
          opacity: 0.8,
        }}
      />
      <div
        style={{
          background: "rgba(10, 10, 26, 0.85)",
          border: `1px solid ${color}`,
          color: "#fff",
          padding: "8px 16px",
          borderRadius: 8,
          fontSize: 24,
          fontFamily: "system-ui, sans-serif",
          fontWeight: 600,
          backdropFilter: "blur(8px)",
        }}
      >
        {label}
      </div>
    </div>
  );
};
