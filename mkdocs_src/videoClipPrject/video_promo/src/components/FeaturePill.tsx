import React from "react";
import { interpolate, useCurrentFrame } from "remotion";

export const FeaturePill: React.FC<{
  icon: string;
  label: string;
  delay: number;
  color: string;
}> = ({ icon, label, delay, color }) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [delay, delay + 20], [0, 1], { extrapolateRight: "clamp" });
  const y = interpolate(frame, [delay, delay + 20], [20, 0], { extrapolateRight: "clamp" });

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "14px 32px",
        borderRadius: 999,
        background: `${color}18`,
        border: `2px solid ${color}60`,
        color,
        fontSize: 32,
        fontFamily: "system-ui, sans-serif",
        fontWeight: 600,
        opacity,
        transform: `translateY(${y}px)`,
        backdropFilter: "blur(8px)",
      }}
    >
      <span style={{ fontSize: 36 }}>{icon}</span>
      {label}
    </div>
  );
};
