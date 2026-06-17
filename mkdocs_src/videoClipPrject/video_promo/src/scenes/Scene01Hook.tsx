import React from "react";
import { Img, staticFile, useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { SceneShell } from "../components/SceneShell";
import { AnimatedHeadline } from "../components/AnimatedHeadline";
import { dictionaries } from "../i18n";
import { Locale } from "../types/i18n";

export const Scene01Hook: React.FC<{ locale: Locale }> = ({ locale }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = dictionaries[locale].scene01;

  const bgScale = interpolate(frame, [0, 150], [1.1, 1.0], { extrapolateRight: "clamp" });
  
  const cards = [
    { label: "Brokers", x: 200, y: 150, delay: 10 },
    { label: "Crypto", x: 1500, y: 200, delay: 20 },
    { label: "FX", x: 300, y: 700, delay: 30 },
    { label: "CSV Reports", x: 1400, y: 800, delay: 40 },
    { label: "Spreadsheets", x: 800, y: 100, delay: 50 },
  ];

  const collapseProgress = spring({
    frame: frame - 120, // Start collapsing near the end
    fps,
    config: { damping: 20, stiffness: 100 },
  });

  return (
    <SceneShell bg="#050510">
      <Img
        src={staticFile("ai/chaos_bg_v2.png")}
        onError={(e) => { e.currentTarget.style.display = 'none'; }}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${bgScale})`,
          filter: "brightness(0.3) saturate(1.2)",
        }}
      />
      
      {/* Floating abstract cards */}
      {cards.map((card, i) => {
        const enterScale = spring({
          frame: frame - card.delay,
          fps,
          config: { damping: 12, stiffness: 100 },
        });
        
        // Move towards center during collapse
        const currentX = interpolate(collapseProgress, [0, 1], [card.x, 960]);
        const currentY = interpolate(collapseProgress, [0, 1], [card.y, 540]);
        const currentScale = interpolate(collapseProgress, [0, 1], [enterScale, 0]);

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: currentX,
              top: currentY,
              transform: `scale(${currentScale})`,
              background: "rgba(30, 30, 40, 0.8)",
              border: "1px solid rgba(129, 140, 248, 0.4)",
              color: "#818cf8",
              padding: "12px 24px",
              borderRadius: 8,
              fontSize: 28,
              fontWeight: 600,
              fontFamily: "system-ui, sans-serif",
              backdropFilter: "blur(10px)",
              boxShadow: "0 10px 30px rgba(0,0,0,0.5)",
            }}
          >
            {card.label}
          </div>
        );
      })}

      {/* Main Text */}
      <div style={{ opacity: interpolate(collapseProgress, [0, 1], [1, 0]) }}>
        <AnimatedHeadline headline={t.headline} sub={t.sub} enterAt={60} />
      </div>
    </SceneShell>
  );
};
