// src/scenes/Scene04Mobile.tsx
// Scene 04 — Mobile (240 frames / 8s)
// Dual-pane: mobile dark (sx) + mobile light (dx) side by side
// con slide-in dai lati + etichetta + cross-dissolve a un unico desktop alla fine
import React from "react";
import {
  AbsoluteFill, useCurrentFrame, interpolate, Img, staticFile,
} from "remotion";
import { Locale } from "../types/i18n";
import { dictionaries } from "../i18n";

interface Props { locale: Locale }

export const Scene04Mobile: React.FC<Props> = ({ locale }) => {
  const frame = useCurrentFrame();
  const t = dictionaries[locale].scene04;

  // — Fase 1 (0–120): i due phone entrano dai lati
  const slideInL = interpolate(frame, [0, 45], [-500, 0], { extrapolateRight: "clamp" });
  const slideInR = interpolate(frame, [0, 45], [500, 0], { extrapolateRight: "clamp" });
  const phonesOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });

  // — Fase 2 (120–180): dissolve verso desktop
  const desktopOpacity = interpolate(frame, [140, 175], [0, 1], { extrapolateRight: "clamp" });
  const phonesOut = interpolate(frame, [140, 175], [1, 0], { extrapolateRight: "clamp" });

  const textIn = interpolate(frame, [20, 55], [0, 1], { extrapolateRight: "clamp" });
  const textOut = interpolate(frame, [140, 170], [1, 0], { extrapolateRight: "clamp" });
  const subtitleIn = interpolate(frame, [175, 210], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{
      background: "linear-gradient(135deg, #0f0520 0%, #0d1b3e 100%)",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      overflow: "hidden",
    }}>

      {/* ── Fase 1: due phone side by side ─────────────────────────── */}
      <div style={{
        position: "absolute",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 60,
        opacity: phonesOpacity * phonesOut,
        width: "100%",
        height: "100%",
      }}>
        {/* Phone dark — slide da sinistra */}
        <div style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 20,
          transform: `translateX(${slideInL}px)`,
        }}>
          <Img
            src={staticFile(`assets/${locale}/dark/mobile/dashboard_main.png`)}
            style={{
              height: 680,
              width: "auto",
              borderRadius: 36,
              boxShadow: "0 40px 100px rgba(0,0,0,0.8), 0 0 0 2px rgba(129,140,248,0.4)",
            }}
          />
          <span style={{
            color: "#818cf8",
            fontSize: 28,
            fontFamily: "system-ui, sans-serif",
            fontWeight: 600,
            background: "rgba(129,140,248,0.12)",
            padding: "8px 22px",
            borderRadius: 999,
            border: "1px solid rgba(129,140,248,0.4)",
          }}>🌙 Dark Mode</span>
        </div>

        {/* Phone light — slide da destra */}
        <div style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 20,
          transform: `translateX(${slideInR}px)`,
        }}>
          <Img
            src={staticFile(`assets/${locale}/light/mobile/dashboard_main.png`)}
            style={{
              height: 680,
              width: "auto",
              borderRadius: 36,
              boxShadow: "0 40px 100px rgba(0,0,0,0.7), 0 0 0 2px rgba(251,191,36,0.4)",
            }}
          />
          <span style={{
            color: "#fbbf24",
            fontSize: 28,
            fontFamily: "system-ui, sans-serif",
            fontWeight: 600,
            background: "rgba(251,191,36,0.10)",
            padding: "8px 22px",
            borderRadius: 999,
            border: "1px solid rgba(251,191,36,0.4)",
          }}>☀️ Light Mode</span>
        </div>
      </div>

      {/* ── Fase 2: desktop dashboard (cross-fade) ─────────────────── */}
      <div style={{
        position: "absolute", inset: 0,
        opacity: desktopOpacity,
        overflow: "hidden",
      }}>
        <Img
          src={staticFile(`assets/${locale}/dark/desktop/dashboard_main.png`)}
          style={{
            width: "100%", height: "100%",
            objectFit: "cover",
            filter: "brightness(0.42)",
          }}
        />
        <div style={{
          position: "absolute", inset: 0,
          background: "linear-gradient(to top, rgba(0,0,0,0.85) 0%, transparent 55%)",
        }} />
      </div>

      {/* ── Testo headline (fase 1) ─────────────────────────────────── */}
      <h1 style={{
        position: "absolute",
        top: 60, left: 0, right: 0,
        color: "#ffffff",
        fontSize: 68,
        fontFamily: "system-ui, sans-serif",
        fontWeight: 700,
        textAlign: "center",
        margin: 0,
        padding: "0 120px",
        opacity: textIn * textOut,
        textShadow: "0 4px 20px rgba(0,0,0,0.9)",
      }}>
        {t.headline}
      </h1>

      {/* ── Subtitle (fase 2 — desktop) ─────────────────────────────── */}
      <div style={{
        position: "absolute",
        bottom: 80, left: 0, right: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 16,
        opacity: subtitleIn,
      }}>
        <p style={{
          color: "#a5f3fc",
          fontSize: 46,
          fontFamily: "system-ui, sans-serif",
          fontWeight: 500,
          textAlign: "center",
          margin: 0,
          textShadow: "0 2px 12px rgba(0,0,0,0.8)",
        }}>
          📱 Mobile &amp; 🖥️ Desktop
        </p>
      </div>
    </AbsoluteFill>
  );
};
