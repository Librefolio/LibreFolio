import React from "react";
import { AbsoluteFill } from "remotion";

export const SceneShell: React.FC<{
  children: React.ReactNode;
  bg?: string;
  gradient?: string;
}> = ({ children, bg = "#050510", gradient }) => {
  return (
    <AbsoluteFill style={{ background: bg, overflow: "hidden" }}>
      {gradient && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: gradient,
          }}
        />
      )}
      {children}
      {/* Vignette */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: "radial-gradient(ellipse at center, transparent 30%, rgba(0,0,0,0.7) 100%)",
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};
