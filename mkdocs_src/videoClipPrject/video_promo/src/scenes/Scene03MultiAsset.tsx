import React from "react";
import { useCurrentFrame, staticFile, interpolate, spring, useVideoConfig, Img } from "remotion";
import { SceneShell } from "../components/SceneShell";
import { AnimatedHeadline } from "../components/AnimatedHeadline";
import { ScreenCrop } from "../components/ScreenCrop";
import { Callout } from "../components/Callout";
import { cropPresets } from "../config/crops";
import { dictionaries } from "../i18n";
import { Locale } from "../types/i18n";

export const Scene03MultiAsset: React.FC<{ locale: Locale }> = ({ locale }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = dictionaries[locale].scene03;
  const calloutsDict = dictionaries[locale].callouts;

  const chartMain = staticFile(`assets/${locale}/dark/desktop/assets/detail-chart.png`);
  const chartSignals = staticFile(`assets/${locale}/dark/desktop/assets/detail-signals.png`);
  const chartClassification = staticFile(`assets/${locale}/dark/desktop/assets/detail-classification.png`);

  const mainScale = spring({
    frame: frame - 10,
    fps,
    config: { damping: 16, stiffness: 80 },
    from: 0.8,
    to: 1.0,
  });

  return (
    <SceneShell bg="#050510">
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          transform: `scale(${mainScale})`,
        }}
      >
        <div style={{ position: "relative", width: 1400, height: 800 }}>
          {/* Main Chart */}
          <Img
            src={chartMain}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              borderRadius: 24,
              boxShadow: "0 40px 100px rgba(0,0,0,0.8)",
            }}
          />

          {/* Callout Technical Analysis */}
          <Callout label={calloutsDict.technicalAnalysis} x={200} y={150} enterAt={40} />

          {/* Reveal Signals Panel Crop */}
          <div
            style={{
              position: "absolute",
              bottom: -40,
              right: 100,
              opacity: interpolate(frame, [80, 100], [0, 1]),
              transform: `translateY(${interpolate(frame, [80, 100], [40, 0])}px)`,
            }}
          >
            <ScreenCrop
              src={chartSignals}
              crop={cropPresets.assetChart.lowerSignals}
              baseWidth={1400}
              baseHeight={800}
            />
            <Callout label={calloutsDict.signals} x={-50} y={-20} enterAt={100} color="#f59e0b" />
          </div>

          {/* Secondary Classification Overlay */}
          <div
            style={{
              position: "absolute",
              top: 80,
              right: -80,
              opacity: interpolate(frame, [140, 160], [0, 1]),
              transform: `translateX(${interpolate(frame, [140, 160], [40, 0])}px)`,
            }}
          >
            <ScreenCrop
              src={chartClassification}
              crop={{ x: 0.1, y: 0.1, w: 0.4, h: 0.5 }} // Approximate crop
              baseWidth={1200}
              baseHeight={800}
              style={{ transform: "scale(0.8)" }}
            />
          </div>
        </div>
      </div>

      <AnimatedHeadline headline={t.headline} sub={t.sub} enterAt={220} />
    </SceneShell>
  );
};
