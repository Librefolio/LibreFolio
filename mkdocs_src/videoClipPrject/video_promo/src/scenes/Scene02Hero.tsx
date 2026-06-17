// src/scenes/Scene02Hero.tsx
// Scene 02 — Hero (210 frames / 7s)
// Carousel dark → light desktop dashboard con cross-fade + headline
import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, Img, staticFile } from "remotion";
import { Locale } from "../types/i18n";
import { dictionaries } from "../i18n";

interface Props { locale: Locale }

// Cross-fade tra due immagini a metà scena
function CrossFade({
  srcA, srcB, frame, switchAt, duration,
}: { srcA: string; srcB: string; frame: number; switchAt: number; duration: number }) {
  const opacityB = interpolate(
    frame,
    [switchAt - 20, switchAt + 20],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const scale = interpolate(frame, [0, duration], [1.06, 1.0], { extrapolateRight: "clamp" });

  return (
    <>
      <Img src={srcA} style={{
        position: "absolute", inset: 0, width: "100%", height: "100%",
        objectFit: "cover", filter: "brightness(0.38)",
        transform: `scale(${scale})`,
        opacity: 1 - opacityB,
      }} />
      <Img src={srcB} style={{
        position: "absolute", inset: 0, width: "100%", height: "100%",
        objectFit: "cover", filter: "brightness(0.50)",
        transform: `scale(${interpolate(frame, [switchAt, duration], [1.06, 1.0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })})`,
        opacity: opacityB,
      }} />
    </>
  );
}

export const Scene02Hero: React.FC<Props> = ({ locale }) => {
  const frame = useCurrentFrame();
  const t = dictionaries[locale].scene02;

  const fadeIn    = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const textIn    = interpolate(frame, [15, 50], [0, 1], { extrapolateRight: "clamp" });
  const translateY = interpolate(frame, [15, 50], [40, 0], { extrapolateRight: "clamp" });

  const darkSrc  = staticFile(`assets/${locale}/dark/desktop/dashboard_main.png`);
  const lightSrc = staticFile(`assets/${locale}/light/desktop/dashboard_main.png`);

  return (
    <AbsoluteFill style={{
      background: "linear-gradient(135deg, #0a0a1a 0%, #0d1b3e 100%)",
      overflow: "hidden",
      opacity: fadeIn,
    }}>
      {/* Dark → Light cross-fade al frame 105 (3.5s) */}
      <CrossFade srcA={darkSrc} srcB={lightSrc} frame={frame} switchAt={105} duration={210} />

      {/* Etichette tema — compaiono al cambio */}
      <div style={{
        position: "absolute",
        top: 48, right: 64,
        display: "flex", gap: 16,
        opacity: interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" }),
      }}>
        {(["dark", "light"] as const).map((t) => {
          const active = frame < 105 ? t === "dark" : t === "light";
          return (
            <span key={t} style={{
              padding: "8px 22px",
              borderRadius: 999,
              background: active ? "rgba(255,255,255,0.18)" : "rgba(255,255,255,0.06)",
              border: `1px solid ${active ? "rgba(255,255,255,0.5)" : "rgba(255,255,255,0.15)"}`,
              color: active ? "#fff" : "rgba(255,255,255,0.4)",
              fontSize: 26,
              fontFamily: "system-ui, sans-serif",
              fontWeight: 500,
              backdropFilter: "blur(12px)",
              transition: "all 0.3s",
            }}>
              {t === "dark" ? "🌙 Dark" : "☀️ Light"}
            </span>
          );
        })}
      </div>

      {/* Vignette */}
      <div style={{
        position: "absolute", inset: 0,
        background: "linear-gradient(to top, rgba(0,0,0,0.85) 0%, transparent 50%)",
      }} />

      <h1 style={{
        position: "absolute",
        bottom: 100, left: 0, right: 0,
        color: "#ffffff",
        fontSize: 80,
        fontFamily: "system-ui, sans-serif",
        fontWeight: 700,
        textAlign: "center",
        margin: 0,
        padding: "0 120px",
        opacity: textIn,
        transform: `translateY(${translateY}px)`,
        textShadow: "0 6px 30px rgba(0,0,0,0.9)",
        letterSpacing: "-0.5px",
      }}>
        {t.headline}
      </h1>
    </AbsoluteFill>
  );
};
