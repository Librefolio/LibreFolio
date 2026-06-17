// src/scenes/Scene05OpenSource.tsx
// Scene 05 — Open Source (210 frames / 7s)
// AI infografica con testo animato
// Fallback: gradient se opensource_infographic.png non ancora disponibile
import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, Img, staticFile } from "remotion";
import { Locale } from "../types/i18n";
import { dictionaries } from "../i18n";

interface Props { locale: Locale }

export const Scene05OpenSource: React.FC<Props> = ({ locale }) => {
  const frame = useCurrentFrame();
  const t = dictionaries[locale].scene05;

  const fadeIn  = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: "clamp" });
  const bgScale = interpolate(frame, [0, 210], [1.06, 1.0], { extrapolateRight: "clamp" });
  const textIn  = interpolate(frame, [20, 55], [0, 1], { extrapolateRight: "clamp" });
  const subIn   = interpolate(frame, [50, 85], [0, 1], { extrapolateRight: "clamp" });

  // Tre pillole animate in sequenza
  const pillars = [
    { icon: "🔓", label: "Open Source", delay: 60, color: "#34d399" },
    { icon: "🖥️", label: "Self-Hosted", delay: 90, color: "#60a5fa" },
    { icon: "☁️", label: "Cloud Option", delay: 120, color: "#c084fc" },
  ];

  return (
    <AbsoluteFill style={{
      background: "linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%)",
      overflow: "hidden",
      opacity: fadeIn,
    }}>
      {/* AI infographic background */}
      <Img
        src={staticFile("ai/opensource_infographic.png")}
        onError={() => {}}
        style={{
          position: "absolute", inset: 0,
          width: "100%", height: "100%",
          objectFit: "cover",
          opacity: 0.25,
          transform: `scale(${bgScale})`,
          filter: "blur(2px) saturate(1.2)",
        }}
      />

      {/* Vignette */}
      <div style={{
        position: "absolute", inset: 0,
        background: "radial-gradient(ellipse at center, transparent 20%, rgba(0,0,0,0.6) 100%)",
      }} />

      {/* Content */}
      <div style={{
        position: "relative",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
        gap: 40,
      }}>
        <h1 style={{
          color: "#ffffff",
          fontSize: 86,
          fontFamily: "system-ui, sans-serif",
          fontWeight: 800,
          textAlign: "center",
          margin: 0,
          padding: "0 120px",
          opacity: textIn,
          transform: `translateY(${interpolate(frame, [20, 55], [30, 0], { extrapolateRight: "clamp" })}px)`,
          textShadow: "0 6px 30px rgba(0,0,0,0.8)",
        }}>
          {t.headline}
        </h1>

        <p style={{
          color: "#67e8f9",
          fontSize: 46,
          fontFamily: "system-ui, sans-serif",
          fontWeight: 400,
          textAlign: "center",
          margin: 0,
          opacity: subIn,
          textShadow: "0 2px 12px rgba(0,0,0,0.7)",
        }}>
          {t.sub}
        </p>

        {/* Tre pillole animate */}
        <div style={{
          display: "flex",
          gap: 32,
          marginTop: 20,
        }}>
          {pillars.map(({ icon, label, delay, color }) => {
            const pillOpacity = interpolate(frame, [delay, delay + 25], [0, 1], { extrapolateRight: "clamp" });
            const pillY = interpolate(frame, [delay, delay + 25], [20, 0], { extrapolateRight: "clamp" });
            return (
              <div key={label} style={{
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
                opacity: pillOpacity,
                transform: `translateY(${pillY}px)`,
                backdropFilter: "blur(8px)",
              }}>
                <span style={{ fontSize: 36 }}>{icon}</span>
                {label}
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
