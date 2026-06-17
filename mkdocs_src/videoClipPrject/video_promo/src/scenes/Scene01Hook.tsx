// src/scenes/Scene01Hook.tsx
// Scene 01 — Hook (150 frames / 5s)
// Sfondo AI "caos finanziario" + headline fade-in
// Fallback: gradient animato se chaos_bg.png non ancora disponibile
import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, Img, staticFile } from "remotion";
import { Locale } from "../types/i18n";
import { dictionaries } from "../i18n";

interface Props { locale: Locale }

export const Scene01Hook: React.FC<Props> = ({ locale }) => {
  const frame = useCurrentFrame();
  const t = dictionaries[locale].scene01;

  const fadeIn   = interpolate(frame, [0, 25],  [0, 1], { extrapolateRight: "clamp" });
  const textIn   = interpolate(frame, [20, 50], [0, 1], { extrapolateRight: "clamp" });
  const subIn    = interpolate(frame, [40, 70], [0, 1], { extrapolateRight: "clamp" });
  const bgScale  = interpolate(frame, [0, 150], [1.08, 1.0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
      }}
    >
      {/* AI-generated chaos background — graceful fallback if missing */}
      <Img
        src={staticFile("ai/chaos_bg.png")}
        onError={() => {}} // silent fallback
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
          opacity: fadeIn * 0.55,
          transform: `scale(${bgScale})`,
          filter: "blur(1px) brightness(0.5) saturate(1.4)",
        }}
      />

      {/* Vignette overlay */}
      <div style={{
        position: "absolute",
        inset: 0,
        background: "radial-gradient(ellipse at center, transparent 30%, rgba(0,0,0,0.7) 100%)",
      }} />

      <h1 style={{
        position: "relative",
        color: "#ffffff",
        fontSize: 96,
        fontFamily: "system-ui, sans-serif",
        fontWeight: 800,
        textAlign: "center",
        margin: 0,
        padding: "0 120px",
        opacity: textIn,
        transform: `translateY(${interpolate(frame, [20, 50], [30, 0], { extrapolateRight: "clamp" })}px)`,
        textShadow: "0 6px 30px rgba(0,0,0,0.9), 0 2px 8px rgba(0,0,0,0.6)",
        letterSpacing: "-1px",
      }}>
        {t.headline}
      </h1>

      {t.sub && (
        <p style={{
          position: "relative",
          color: "#c4b5fd",
          fontSize: 52,
          fontFamily: "system-ui, sans-serif",
          fontWeight: 400,
          textAlign: "center",
          marginTop: 32,
          opacity: subIn,
          transform: `translateY(${interpolate(frame, [40, 70], [20, 0], { extrapolateRight: "clamp" })}px)`,
          textShadow: "0 4px 16px rgba(0,0,0,0.8)",
        }}>
          {t.sub}
        </p>
      )}
    </AbsoluteFill>
  );
};
