// src/scenes/Scene03MultiAsset.tsx
// Scene 03 — Multi-Asset (240 frames / 8s)
// Carousel 4 screenshot: echarts dark → echarts light → datatable dark → datatable light
// ogni screenshot dura ~55f con cross-fade 15f di overlap
import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, Img, staticFile } from "remotion";
import { Locale } from "../types/i18n";
import { dictionaries } from "../i18n";

interface Props { locale: Locale }

interface SlideProps {
  src: string;
  enterAt: number;
  exitAt: number;
  frame: number;
  label: string;
  labelColor: string;
}

function Slide({ src, enterAt, exitAt, frame, label, labelColor }: SlideProps) {
  const opacity = interpolate(
    frame,
    [enterAt, enterAt + 15, exitAt - 15, exitAt],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const scale = interpolate(frame, [enterAt, exitAt], [1.04, 1.0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  return (
    <div style={{ position: "absolute", inset: 0, opacity }}>
      <Img src={src} style={{
        width: "100%", height: "100%",
        objectFit: "cover",
        objectPosition: "top left",
        transform: `scale(${scale})`,
        filter: "brightness(0.45)",
      }} />
      {/* Slide label badge */}
      <div style={{
        position: "absolute", top: 48, left: 64,
        padding: "8px 22px",
        borderRadius: 999,
        background: "rgba(0,0,0,0.5)",
        border: `2px solid ${labelColor}`,
        color: labelColor,
        fontSize: 26,
        fontFamily: "system-ui, sans-serif",
        fontWeight: 600,
        backdropFilter: "blur(12px)",
      }}>
        {label}
      </div>
    </div>
  );
}

export const Scene03MultiAsset: React.FC<Props> = ({ locale }) => {
  const frame = useCurrentFrame();
  const t = dictionaries[locale].scene03;

  const textIn = interpolate(frame, [20, 55], [0, 1], { extrapolateRight: "clamp" });
  const subIn  = interpolate(frame, [50, 85], [0, 1], { extrapolateRight: "clamp" });

  // 4 slide: 0→65, 55→120, 110→175, 165→240 (overlap 10f)
  const slides = [
    {
      src:   staticFile(`assets/${locale}/dark/desktop/echarts_view.png`),
      enterAt: 0, exitAt: 68,
      label: "🌙 Charts — Dark", labelColor: "#818cf8",
    },
    {
      src:   staticFile(`assets/${locale}/light/desktop/echarts_view.png`),
      enterAt: 58, exitAt: 130,
      label: "☀️ Charts — Light", labelColor: "#f59e0b",
    },
    {
      src:   staticFile(`assets/${locale}/dark/desktop/datatable_view.png`),
      enterAt: 120, exitAt: 188,
      label: "🌙 Portfolio — Dark", labelColor: "#818cf8",
    },
    {
      src:   staticFile(`assets/${locale}/light/desktop/datatable_view.png`),
      enterAt: 178, exitAt: 240,
      label: "☀️ Portfolio — Light", labelColor: "#f59e0b",
    },
  ];

  return (
    <AbsoluteFill style={{
      background: "#050510",
      overflow: "hidden",
    }}>
      {slides.map((s, i) => (
        <Slide key={i} {...s} frame={frame} />
      ))}

      {/* Bottom gradient + text */}
      <div style={{
        position: "absolute", inset: 0,
        background: "linear-gradient(to top, rgba(0,0,0,0.90) 0%, transparent 55%)",
      }} />

      <div style={{
        position: "absolute",
        bottom: 90, left: 0, right: 0,
        display: "flex", flexDirection: "column", alignItems: "center", gap: 20,
      }}>
        <h1 style={{
          color: "#ffffff",
          fontSize: 80,
          fontFamily: "system-ui, sans-serif",
          fontWeight: 700,
          textAlign: "center",
          margin: 0,
          opacity: textIn,
          transform: `translateY(${interpolate(frame, [20, 55], [30, 0], { extrapolateRight: "clamp" })}px)`,
          textShadow: "0 4px 20px rgba(0,0,0,0.8)",
        }}>
          {t.headline}
        </h1>
        <p style={{
          color: "#34d399",
          fontSize: 46,
          fontFamily: "system-ui, sans-serif",
          fontWeight: 500,
          margin: 0,
          opacity: subIn,
          textShadow: "0 2px 12px rgba(0,0,0,0.7)",
        }}>
          {t.sub}
        </p>
      </div>

      {/* Slide indicator dots */}
      <div style={{
        position: "absolute", bottom: 40, left: 0, right: 0,
        display: "flex", justifyContent: "center", gap: 12,
      }}>
        {[0, 1, 2, 3].map((i) => {
          const active = (
            (i === 0 && frame < 58) ||
            (i === 1 && frame >= 58 && frame < 120) ||
            (i === 2 && frame >= 120 && frame < 178) ||
            (i === 3 && frame >= 178)
          );
          return (
            <div key={i} style={{
              width: active ? 28 : 10,
              height: 10,
              borderRadius: 999,
              background: active ? "#818cf8" : "rgba(255,255,255,0.3)",
              transition: "all 0.3s",
            }} />
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
