/**
 * Scene 02 — Dashboard Seed Reveal / Private Dashboard
 * ---------------------------------------------------------------------------
 * Purpose:
 *   Transform the LibreFolio logo tile produced by Scene 01 into the first clear
 *   view of the product: one private dashboard where scattered financial data
 *   becomes connected and readable.
 *
 * Creative direction:
 *   Scene 02 should not start abruptly with a fully formed dashboard. It begins
 *   from the same centered LibreFolio white logo tile used at the end of
 *   Scene 01. The tile emits clean geometry, the dashboard frame emerges behind
 *   it, then the full dashboard reveal, callouts and dark/light diagonal sweep
 *   can take over.
 *
 * Keyframes:
 *   000–020f  Continue from Scene 01 with centered LibreFolio logo tile.
 *   020–045f  Clean dashboard outline/geometry expands from the tile.
 *   045–080f  Dark dashboard emerges behind the seed; tile reduces or settles.
 *   080–120f  Dashboard becomes readable; supporting crops/callouts may enter.
 *   120–180f  Diagonal dark/light reveal becomes the main visual moment.
 *   180–240f  Headline/subtitle hold: one private dashboard, all wealth
 *             connected.
 *
 * Handoff:
 *   The first frames must visually match the final Scene 01 seed state. Avoid a
 *   hard cut, fade to black or dashboard entering as a disconnected full-screen
 *   screenshot.
 */
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
import { LibreFolioSeed } from "../components/LibreFolioSeed";

export const Scene02Hero: React.FC<{ locale: Locale }> = ({ locale }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = dictionaries[locale].scene02;
  const calloutsDict = dictionaries[locale].callouts;

  const darkMain = staticFile(`assets/${locale}/dark/desktop/dashboard/main.png`);
  const lightMain = staticFile(`assets/${locale}/light/desktop/dashboard/main.png`);

  const scene01Dict = dictionaries[locale].scene01;

  // Dashboard expanding from the seed
  const dashboardExpand = spring({
    frame: frame - 25,
    fps,
    config: { damping: 16, stiffness: 80 },
  });
  
  const dashboardScale = interpolate(dashboardExpand, [0, 1], [0.1, 1]);
  const dashboardOpacity = interpolate(frame, [25, 45], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });

  // Seed vanishing as dashboard expands
  const seedScale = interpolate(dashboardExpand, [0, 1], [1, 0], { extrapolateRight: "clamp" });
  const seedOpacity = interpolate(dashboardExpand, [0, 0.5], [1, 0], { extrapolateRight: "clamp" });
  const seedGlow = interpolate(frame, [0, 25], [1.0, 2.0], { extrapolateRight: "clamp" });

  return (
    <SceneShell bg="#050510">
      {/* Delayed whoosh perfectly synced with the expansion */}
      <Audio src={staticFile("ai/sfx_transition_whoosh_cut_a.mp3")} volume={0.6} />

      {/* The Seed from Scene 01 */}
      {frame < 80 && (
        <LibreFolioSeed 
          scale={seedScale}
          opacity={seedOpacity}
          glow={seedGlow}
          showWordmark={true}
          wordmark={scene01Dict.productName}
          wordmarkOpacity={seedOpacity}
          layout="horizontal-wordmark"
          tileSize={220}
          iconSize={170}
          wordmarkFontSize={88}
          wordmarkGap={36}
        />
      )}

      {/* The Dashboard expanding */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          transform: `scale(${dashboardScale})`,
          opacity: dashboardOpacity,
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
          <div style={{ position: "absolute", left: -60, top: 100, opacity: interpolate(frame, [60, 75], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" }) }}>
            <ScreenCrop src={darkMain} crop={cropPresets.dashboard.leftSidebar} baseWidth={1600} baseHeight={900} style={{ transform: 'scale(0.8)' }} />
          </div>

          <div style={{ position: "absolute", right: -40, top: 200, opacity: interpolate(frame, [75, 90], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" }) }}>
             <ScreenCrop src={darkMain} crop={cropPresets.dashboard.allocationChart} baseWidth={1600} baseHeight={900} style={{ transform: 'scale(0.7)' }} />
          </div>

          {/* Callouts */}
          <Callout label={calloutsDict.netWorth} x={300} y={150} enterAt={90} />
          <Callout label={calloutsDict.allocation} x={1100} y={350} enterAt={110} />
        </div>
      </div>

      <AnimatedHeadline headline={t.headline} sub={t.sub} enterAt={150} />
    </SceneShell>
  );
};
