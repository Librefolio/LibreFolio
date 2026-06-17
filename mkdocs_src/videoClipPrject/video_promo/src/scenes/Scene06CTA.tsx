// src/scenes/Scene06CTA.tsx
// Scene 06 — CTA (150 frames / 5s)
// Logo LibreFolio centrato + scale-in + headline + CTA + fade-out finale
import React from "react";
import {
  AbsoluteFill, useCurrentFrame, interpolate, Img, staticFile,
} from "remotion";
import { Locale } from "../types/i18n";
import { dictionaries } from "../i18n";

interface Props { locale: Locale }

export const Scene06CTA: React.FC<Props> = ({ locale }) => {
  const frame = useCurrentFrame();
  const t = dictionaries[locale].scene06;

  // Fade-in globale + fade-out all'uscita
  const sceneOpacity = interpolate(frame, [0, 20, 125, 150], [0, 1, 1, 0], {
    extrapolateRight: "clamp",
  });

  // Logo: scale-in elastico
  const logoScale = interpolate(frame, [0, 40], [0.3, 1.0], {
    extrapolateRight: "clamp",
  });
  const logoOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });

  // Headline dopo logo
  const headlineOpacity = interpolate(frame, [35, 65], [0, 1], { extrapolateRight: "clamp" });
  const headlineY = interpolate(frame, [35, 65], [24, 0], { extrapolateRight: "clamp" });

  // CTA ancora dopo
  const ctaOpacity = interpolate(frame, [60, 90], [0, 1], { extrapolateRight: "clamp" });
  const ctaY = interpolate(frame, [60, 90], [16, 0], { extrapolateRight: "clamp" });

  // Glow pulsante sul logo (loop ogni 60f)
  const glowIntensity = Math.sin((frame % 60) / 60 * Math.PI * 2) * 0.5 + 0.5;

  return (
    <AbsoluteFill style={{
      background: "linear-gradient(135deg, #0f0c29 0%, #1a0a2e 50%, #0d1b3e 100%)",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      gap: 40,
      opacity: sceneOpacity,
    }}>
      {/* Stars background (puntini statici con CSS) */}
      <div style={{
        position: "absolute", inset: 0,
        backgroundImage: "radial-gradient(1px 1px at 10% 15%, rgba(255,255,255,0.3) 0%, transparent 100%), radial-gradient(1px 1px at 25% 40%, rgba(255,255,255,0.2) 0%, transparent 100%), radial-gradient(2px 2px at 60% 20%, rgba(255,255,255,0.25) 0%, transparent 100%), radial-gradient(1px 1px at 80% 70%, rgba(255,255,255,0.2) 0%, transparent 100%), radial-gradient(1px 1px at 45% 80%, rgba(255,255,255,0.15) 0%, transparent 100%)",
      }} />

      {/* Logo */}
      <div style={{
        transform: `scale(${logoScale})`,
        opacity: logoOpacity,
        position: "relative",
      }}>
        <div style={{
          position: "absolute",
          inset: -30,
          borderRadius: "50%",
          background: `radial-gradient(circle, rgba(129,140,248,${0.3 + glowIntensity * 0.2}) 0%, transparent 70%)`,
          filter: "blur(20px)",
        }} />
        <Img
          src={staticFile("assets/shared/logo.png")}
          style={{
            height: 160,
            width: "auto",
            position: "relative",
            filter: "drop-shadow(0 8px 30px rgba(129,140,248,0.6))",
          }}
        />
      </div>

      {/* Headline */}
      <h1 style={{
        color: "#ffffff",
        fontSize: 86,
        fontFamily: "system-ui, sans-serif",
        fontWeight: 800,
        textAlign: "center",
        margin: 0,
        opacity: headlineOpacity,
        transform: `translateY(${headlineY}px)`,
        textShadow: "0 6px 30px rgba(0,0,0,0.8)",
        letterSpacing: "-1px",
      }}>
        {t.headline}
      </h1>

      {/* CTA */}
      <div style={{
        opacity: ctaOpacity,
        transform: `translateY(${ctaY}px)`,
        background: "rgba(129,140,248,0.12)",
        border: "2px solid rgba(129,140,248,0.5)",
        borderRadius: 16,
        padding: "20px 48px",
        backdropFilter: "blur(12px)",
      }}>
        <p style={{
          color: "#c4b5fd",
          fontSize: 36,
          fontFamily: "system-ui, sans-serif",
          fontWeight: 500,
          textAlign: "center",
          margin: 0,
          textShadow: "0 2px 12px rgba(0,0,0,0.6)",
          letterSpacing: "0.5px",
        }}>
          {t.cta}
        </p>
      </div>
    </AbsoluteFill>
  );
};
