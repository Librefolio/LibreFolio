import React from "react";
import { useCurrentFrame, staticFile, interpolate, spring, useVideoConfig, Audio } from "remotion";
import { SceneShell } from "../components/SceneShell";
import { AnimatedHeadline } from "../components/AnimatedHeadline";
import { DiagonalThemeReveal } from "../components/DiagonalThemeReveal";
import { ScreenCrop } from "../components/ScreenCrop";
import { Callout } from "../components/Callout";
import { cropPresets } from "../config/crops";
import { dictionaries } from "../i18n";
import { Locale } from "../types/i18n";

export const Scene02Hero: React.FC<{ locale: Locale }> = ({ locale }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = dictionaries[locale].scene02;
  const calloutsDict = dictionaries[locale].callouts;

  const darkMain = staticFile(`assets/${locale}/dark/desktop/dashboard/main.png`);
  const lightMain = staticFile(`assets/${locale}/light/desktop/dashboard/main.png`);

  const dashboardScale = spring({
    frame: frame - 10,
    fps,
    config: { damping: 14, stiffness: 80 },
    from: 0.8,
    to: 1.0,
  });

  const dashboardY = spring({
    frame: frame - 10,
    fps,
    config: { damping: 14, stiffness: 80 },
    from: 200,
    to: 0,
  });

  return (
    <SceneShell bg="#050510">
      <Audio src={staticFile("ai/sfx_transition_whoosh_cut_a.mp3")} volume={0.6} />
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          transform: `scale(${dashboardScale}) translateY(${dashboardY}px)`,
        }}
      >
        <div
          style={{
            width: 1600,
            height: 900,
            borderRadius: 24,
            overflow: "hidden",
            boxShadow: "0 40px 100px rgba(0,0,0,0.8)",
            position: "relative",
          }}
        >
          <DiagonalThemeReveal
            darkSrc={darkMain}
            lightSrc={lightMain}
            enterAt={120}
            duration={60}
          />

          {/* Mini-cards (Crops) */}
          <div style={{ position: "absolute", left: -60, top: 100, opacity: interpolate(frame, [30, 45], [0, 1]) }}>
            <ScreenCrop src={darkMain} crop={cropPresets.dashboard.leftSidebar} baseWidth={1600} baseHeight={900} style={{ transform: 'scale(0.8)' }} />
          </div>

          <div style={{ position: "absolute", right: -40, top: 200, opacity: interpolate(frame, [45, 60], [0, 1]) }}>
             <ScreenCrop src={darkMain} crop={cropPresets.dashboard.allocationChart} baseWidth={1600} baseHeight={900} style={{ transform: 'scale(0.7)' }} />
          </div>

          {/* Callouts */}
          <Callout label={calloutsDict.netWorth} x={300} y={150} enterAt={60} />
          <Callout label={calloutsDict.allocation} x={1100} y={350} enterAt={80} />
        </div>
      </div>

      <AnimatedHeadline headline={t.headline} sub={t.sub} enterAt={150} />
    </SceneShell>
  );
};
