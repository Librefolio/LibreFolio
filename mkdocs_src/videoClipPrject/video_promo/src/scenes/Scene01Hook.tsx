/**
 * Scene 01 — Investment Overload / Product Reveal
 * ---------------------------------------------------------------------------
 * Duration:
 *   360 frames @ 30fps (12s)
 *
 * Purpose:
 *   Make the viewer feel the investment-tracking problem before presenting
 *   LibreFolio as the solution. Investing may be enjoyable, but keeping brokers,
 *   apps, reports, spreadsheets, wallets, FX rates and disconnected analysis
 *   under control quickly becomes overwhelming.
 *
 * Creative direction:
 *   The scene starts immediately with a living dark fintech background and the
 *   simple statement “Bello investire!”. It then makes the obvious problem
 *   explicit: keeping everything under control is another story.
 *   Source words and rich glass problem shards appear together, populating the space.
 *   As source words fade, three problem statements pop out separately from different 
 *   screen areas without bounding boxes. 
 *   The pressure resolves into “Troppe fonti. Poca chiarezza.”, then the chaos
 *   collapses into a clean product reveal: “E se tutto tornasse chiaro?” appears
 *   large at the top during the spiral, followed by the standard LibreFolio 
 *   white logo tile with the LibreFolio wordmark in a horizontal layout.
 *
 * Keyframes:
 *   000–015f  Dark financial noise is already alive; no long empty pause.
 *   015–070f  “Bello investire!”
 *   065–120f  “Tenere tutto sotto controllo è un’altra storia.”
 *   055–335f  Shards start with a continuous orbital motion that progressively tightens.
 *   100–190f  Source words appear quickly alongside the orbiting problem shards.
 *   290–335f  The spiral converges toward the center fluidly.
 *   315–360f  “E se tutto tornasse chiaro?” appears high and remains visible until the end.
 *   315–360f  The LibreFolio logo tile appears mid-spiral as the absorbing core.
 *
 * Handoff:
 *   Scene 01 must not fade to black and must not start expanding the dashboard.
 *   It ends with the centered LibreFolio horizontal logo and wordmark. Scene 02
 *   starts from that same visual seed and will handle the expansion into the
 *   product.
 */
import React from "react";
import { Img, staticFile, useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { SceneShell } from "../components/SceneShell";
import { dictionaries } from "../i18n";
import { Locale } from "../types/i18n";
import { ProblemShard, ShardVariant, ShardVisualType } from "../components/ProblemShard";
import { LibreFolioSeed } from "../components/LibreFolioSeed";

const getShardsData = (t: any) => [
  { ...t.shards.csvReport, iconPath: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6 M8 13h8 M8 17h8 M8 9h2", startAngle: 0, startRadius: 400, variant: "hero", visualType: "table" as ShardVisualType },
  { ...t.shards.brokerExport, iconPath: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4 M7 10l5 5 5-5 M12 15V3", startAngle: 1.2, startRadius: 450, variant: "hero", visualType: "formats" as ShardVisualType },
  { ...t.shards.fxRates, iconPath: "M3 7h12l-4-4 M21 17H9l4 4", startAngle: 2.5, startRadius: 380, variant: "medium", visualType: "fx" as ShardVisualType },
  { ...t.shards.spreadsheets, iconPath: "M3 3h18v18H3z M3 9h18 M9 21V9", startAngle: 3.8, startRadius: 500, variant: "hero", visualType: "grid" as ShardVisualType },
  { ...t.shards.wallets, iconPath: "M20 12V8H6a2 2 0 0 1-2-2c0-1.1.9-2 2-2h12v4 M4 10v8a2 2 0 0 0 2 2h14v-8H4z M16 14h.01", startAngle: 5.0, startRadius: 420, variant: "medium", visualType: "wallet" as ShardVisualType },
  { ...t.shards.priceNoise, iconPath: "M3 3v18h18 M18 9l-5-5-4 4-6-6", startAngle: 0.6, startRadius: 550, variant: "medium", visualType: "chartNoise" as ShardVisualType },
  { ...t.shards.duplicates, iconPath: "M8 16H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v2 M16 8h2a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-8a2 2 0 0 1-2-2v-2", startAngle: 1.9, startRadius: 350, variant: "medium", visualType: "duplicates" as ShardVisualType },
  { ...t.shards.reports, iconPath: "M12 2v20 M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6", startAngle: 4.4, startRadius: 480, variant: "small", visualType: "reports" as ShardVisualType },
  { ...t.shards.alerts, iconPath: "M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9 M13.73 21a2 2 0 0 1-3.46 0", startAngle: 3.1, startRadius: 600, variant: "small", visualType: "alerts" as ShardVisualType }
];

const renderTextWithBreaks = (text: string) => {
  return text.split('\n').map((line, i) => (
    <React.Fragment key={i}>
      {line}
      {i !== text.split('\n').length - 1 && <br />}
    </React.Fragment>
  ));
};

export const Scene01Hook: React.FC<{ locale: Locale }> = ({ locale }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = dictionaries[locale].scene01;

  // Background drift
  const bgScale = interpolate(frame, [0, 360], [1.02, 1.0], { extrapolateRight: "clamp" });
  const bgBrightness = interpolate(frame, [0, 180, 360], [0.35, 0.5, 0.20], { extrapolateRight: "clamp" });

  // Compressed intro texts
  const introStatementOpacity = interpolate(frame, [15, 25, 58, 70], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const controlStatementOpacity = interpolate(frame, [65, 78, 108, 120], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  
  // Overload statement (shaved 30 frames, start anticipated 15 frames)
  const overloadStatementOpacity = interpolate(frame, [245, 257, 325, 337], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  
  // Reveal prefix (starts during spiral) (shaved 30 frames)
  const revealPrefixOpacity = interpolate(frame, [315, 328], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const revealPrefixScale = interpolate(frame, [315, 328, 360], [0.92, 1.04, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  const revealPrefixBlur = interpolate(frame, [315, 328], [8, 0], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });

  const sourceWordPlacements = [
    { index: 0, x: -420, y: -120, enterAt: 100, from: "left" },
    { index: 1, x: -60,  y: -40,  enterAt: 115, from: "bottom" },
    { index: 2, x: 280,  y: -120, enterAt: 130, from: "right" },
    { index: 3, x: -280, y: 90,   enterAt: 145, from: "left" },
    { index: 4, x: 200,  y: 90,   enterAt: 160, from: "right" },
  ];

  const problemStatementPlacements = [
    { index: 0, x: -500, y: -230, enterAt: 190, exitAt: 255, from: "left", rotate: -3 },
    { index: 1, x: 300,  y: -130, enterAt: 220, exitAt: 285, from: "right", rotate: 2 },
    { index: 2, x: 0,    y: 280,  enterAt: 250, exitAt: 305, from: "bottom", rotate: -1 },
  ];

  const problemShardsData = getShardsData(t);

  // LibreFolio Seed Entrance (starts mid-spiral)
  const seedOpacity = interpolate(frame, [315, 330], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  const seedScaleProgress = spring({
    frame: frame - 315,
    fps,
    config: { damping: 16, stiffness: 90 },
  });
  const seedScale = interpolate(seedScaleProgress, [0, 1], [0.65, 1], { extrapolateRight: "clamp" });
  const seedGlow = interpolate(frame, [325, 360], [0.35, 1.0], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });

  const wordmarkOpacity = interpolate(frame, [325, 340], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  // Suction effect opacity
  const suctionOpacity = interpolate(frame, [315, 330, 360], [0, 1, 0], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });

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
          filter: `brightness(${bgBrightness}) saturate(1.2)`,
        }}
      />
      
      {/* Suction Glow Layer behind shards */}
      <div style={{
        position: "absolute",
        left: "50%",
        top: "50%",
        transform: "translate(-50%, -50%)",
        width: 600,
        height: 600,
        background: "radial-gradient(circle, rgba(103,232,249,0.15) 0%, rgba(103,232,249,0) 70%)",
        opacity: suctionOpacity,
        zIndex: 4,
        pointerEvents: "none",
      }} />

      <div 
        style={{ 
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "system-ui, -apple-system, sans-serif",
          color: "white",
          textAlign: "center",
          textShadow: "0 10px 40px rgba(0,0,0,0.8)",
          zIndex: 10,
        }}
      >
        <h1 style={{ position: "absolute", fontSize: 72, fontWeight: 700, opacity: introStatementOpacity }}>
          {t.introStatement}
        </h1>

        <h1 style={{ position: "absolute", fontSize: 64, fontWeight: 700, opacity: controlStatementOpacity, lineHeight: 1.2 }}>
          {renderTextWithBreaks(t.controlStatement)}
        </h1>

        {/* Source Words Pop-outs */}
        <div style={{ position: "absolute", inset: 0, display: "flex", justifyContent: "center", alignItems: "center" }}>
          {sourceWordPlacements.map((pw, i) => {
            const word = t.sourceWords[pw.index];
            if (!word) return null;

            const enterProgress = spring({ frame: frame - pw.enterAt, fps, config: { damping: 14, stiffness: 120 } });
            const opacity = interpolate(enterProgress, [0, 1], [0, 1]);
            const scale = interpolate(enterProgress, [0, 0.6, 1], [0.75, 1.10, 1]);
            const blur = interpolate(enterProgress, [0, 1], [8, 0]);
            
            const dx = pw.from === "left" ? -40 : pw.from === "right" ? 40 : 0;
            const dy = pw.from === "bottom" ? 40 : pw.from === "top" ? -40 : 0;
            const tx = interpolate(enterProgress, [0, 1], [pw.x + dx, pw.x]);
            const ty = interpolate(enterProgress, [0, 1], [pw.y + dy, pw.y]);

            const fadeOut = interpolate(frame, [195, 230], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

            return (
              <span key={`sw-${i}`} style={{ 
                position: "absolute",
                fontSize: 40, 
                fontWeight: 500, 
                color: "#cbd5e1", 
                opacity: opacity * fadeOut, 
                filter: `blur(${blur}px)`,
                transform: `translate(${tx}px, ${ty}px) scale(${scale})`, 
                textShadow: "0 4px 12px rgba(0,0,0,0.6)" 
              }}>
                {word}
              </span>
            );
          })}
        </div>

        {/* Problem Statements Pop-outs (Free text) */}
        <div style={{ position: "absolute", inset: 0, display: "flex", justifyContent: "center", alignItems: "center" }}>
          {problemStatementPlacements.map((ps, i) => {
            const text = t.formatsStatement[ps.index];
            if (!text) return null;

            const enterProgress = spring({ frame: frame - ps.enterAt, fps, config: { damping: 12, stiffness: 80 } });
            const opacity = interpolate(enterProgress, [0, 1], [0, 1]);
            const scale = interpolate(enterProgress, [0, 0.6, 1], [0.65, 1.08, 1]);
            const blur = interpolate(enterProgress, [0, 1], [8, 0]);
            
            const dx = ps.from === "left" ? -60 : ps.from === "right" ? 60 : 0;
            const dy = ps.from === "bottom" ? 60 : ps.from === "top" ? -60 : 0;
            const driftY = interpolate(frame - ps.enterAt, [0, 100], [0, -20], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
            const tx = interpolate(enterProgress, [0, 1], [ps.x + dx, ps.x]);
            const ty = interpolate(enterProgress, [0, 1], [ps.y + dy, ps.y]) + driftY;

            const fadeOut = interpolate(frame, [ps.exitAt - 20, ps.exitAt], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            
            const statementFontSize = ps.index === 2 ? 58 : 62;

            return (
              <div key={`ps-${i}`} style={{ 
                position: "absolute",
                opacity: opacity * fadeOut, 
                filter: `blur(${blur}px)`,
                transform: `translate(${tx}px, ${ty}px) scale(${scale}) rotate(${ps.rotate}deg)`, 
                zIndex: 15,
              }}>
                <h2 style={{ 
                  fontSize: statementFontSize, 
                  fontWeight: 800, 
                  margin: 0, 
                  color: "#f8fafc", 
                  textShadow: "0 10px 40px rgba(0,0,0,0.8), 0 0 20px rgba(255,255,255,0.2)" 
                }}>
                  {text}
                </h2>
              </div>
            );
          })}
        </div>

        <div style={{ position: "absolute", display: "flex", flexDirection: "column", gap: 8, opacity: overloadStatementOpacity, zIndex: 20 }}>
          {t.overloadStatement.split('\n').map((line, i) => (
            <h1 key={`ol-${i}`} style={{ 
              fontSize: 84, 
              fontWeight: 800, 
              margin: 0,
              color: i === 0 ? "#f8fafc" : "#a78bfa",
              textShadow: i === 1 ? "0 0 40px rgba(167,139,250,0.4)" : "0 10px 40px rgba(0,0,0,0.8)"
            }}>
              {line}
            </h1>
          ))}
        </div>

        {/* Product Reveal Prefix (High and large) */}
        <div style={{
          position: "absolute",
          top: 120,
          left: 0,
          width: "100%",
          display: "flex",
          justifyContent: "center",
        }}>
          <h2 style={{ 
            fontSize: 76, 
            fontWeight: 800, 
            color: "#f8fafc", 
            letterSpacing: "0.02em",
            opacity: revealPrefixOpacity,
            filter: `blur(${revealPrefixBlur}px)`,
            transform: `scale(${revealPrefixScale}) translateY(${interpolate(frame, [315, 328], [-24, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}px)`,
            textShadow: "0 0 30px rgba(103,232,249,0.25), 0 10px 40px rgba(0,0,0,0.8)",
            margin: 0,
          }}>
            {t.revealPrefix}
          </h2>
        </div>
      </div>

      {/* Problem Shards (Spiraling) */}
      <div style={{ position: "absolute", inset: 0, zIndex: 5 }}>
        {problemShardsData.map((shard, i) => {
          // Keep delay slightly before the first source word, but softer pacing
          const delay = 68 + i * 11;
          
          const enterProgress = spring({
            frame: frame - delay,
            fps,
            config: { damping: 22, stiffness: 52 },
          });

          // Separate enter progress interpolation and limit to 1 so it doesn't cause scale spikes when clamped
          const clampedEnterProgress = Math.min(1, Math.max(0, enterProgress));
          const enterOpacity = interpolate(clampedEnterProgress, [0, 1], [0, 1]);

          // Continuous orbital mechanics
          const orbitStartFrame = 55;
          const orbitFrame = Math.max(0, frame - orbitStartFrame);
          const angularSpeed = 0.012;
          
          // Slight acceleration, minimal
          const acceleration = interpolate(frame, [55, 270, 335], [1.0, 1.06, 1.12], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          
          const currentAngle = Number(shard.startAngle) + orbitFrame * angularSpeed * acceleration;

          // Continuous progressive radius (much smoother trajectory)
          const radiusFactor = interpolate(
            frame,
            [55, 120, 190, 260, 310, 335],
            [1.00, 0.98, 0.88, 0.68, 0.38, 0.00],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }
          );
          
          const breathing = 1 + Math.sin(frame * 0.018 + i) * 0.015;
          
          const currentRadius = Number(shard.startRadius) * radiusFactor * breathing;

          // Intensity of collapse for visual fade/blur
          const collapseIntensity = interpolate(frame, [290, 335], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });

          // Scale only uses clampedEnterProgress and collapseIntensity, no spikes
          const currentScale = clampedEnterProgress * interpolate(collapseIntensity, [0, 1], [1, 0.18]);
          const currentBlur = interpolate(collapseIntensity, [0, 0.65, 1], [0, 0, 14]);
          const fadeOutProgress = interpolate(collapseIntensity, [0.75, 1], [1, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          
          const finalOpacity = enterOpacity * fadeOutProgress;

          const centerX = 960 - (shard.variant === "hero" ? 190 : shard.variant === "medium" ? 140 : 110);
          const centerY = 540 - (shard.variant === "hero" ? 70 : shard.variant === "medium" ? 40 : 38);
          
          const x = centerX + Math.cos(currentAngle) * currentRadius * 1.35;
          const y = centerY + Math.sin(currentAngle) * currentRadius * 0.75;

          const rotation = Math.sin(frame * 0.05 + i) * 5;

          return (
            <ProblemShard 
              key={`shard-${i}`}
              title={shard.title}
              subtitle={shard.subtitle}
              iconPath={shard.iconPath}
              opacity={finalOpacity}
              scale={currentScale}
              blur={currentBlur}
              x={x}
              y={y}
              rotation={rotation}
              variant={shard.variant as ShardVariant}
              visualType={shard.visualType}
            />
          );
        })}
      </div>

      {/* The Central Seed (LibreFolio Horizontal Logo) */}
      <div style={{ position: "absolute", inset: 0, zIndex: 100 }}>
         <LibreFolioSeed 
          scale={seedScale}
          opacity={seedOpacity}
          glow={seedGlow}
          showWordmark={true}
          wordmark={t.productName}
          wordmarkOpacity={wordmarkOpacity}
          layout="horizontal-wordmark"
          tileSize={220}
          iconSize={170}
          wordmarkFontSize={88}
          wordmarkGap={36}
        />
      </div>
      
    </SceneShell>
  );
};
