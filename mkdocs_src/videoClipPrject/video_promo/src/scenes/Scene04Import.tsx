import React from "react";
import { useCurrentFrame, staticFile, interpolate, spring, useVideoConfig, Img } from "remotion";
import { SceneShell } from "../components/SceneShell";
import { AnimatedHeadline } from "../components/AnimatedHeadline";
import { ScreenCrop } from "../components/ScreenCrop";
import { cropPresets } from "../config/crops";
import { dictionaries } from "../i18n";
import { Locale } from "../types/i18n";

export const Scene04Import: React.FC<{ locale: Locale }> = ({ locale }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = dictionaries[locale].scene04;
  const calloutsDict = dictionaries[locale].callouts;

  const importList = staticFile(`assets/${locale}/dark/desktop/brokers/list.png`);
  const schedulerConfig = staticFile(`assets/${locale}/dark/desktop/settings/scheduler-config.png`);

  return (
    <SceneShell bg="#050510">
      <Img
        src={staticFile("ai/import_pipeline_bg.png")}
        onError={(e) => { e.currentTarget.style.display = 'none'; }}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
          filter: "brightness(0.3) saturate(1.2)",
        }}
      />
      {/* Pipeline connection line */}
      <div
        style={{
          position: "absolute",
          top: "45%",
          left: 200,
          right: 200,
          height: 4,
          background: "linear-gradient(90deg, transparent, rgba(103, 232, 249, 0.5), transparent)",
          opacity: interpolate(frame, [20, 40], [0, 1]),
        }}
      />

      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: 60,
        }}
      >
        {/* Step 1: Import */}
        <div
          style={{
            transform: `scale(${spring({ frame: frame - 30, fps, config: { damping: 14 } })})`,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 20,
          }}
        >
          <ScreenCrop
            src={importList}
            crop={{ x: 0.1, y: 0.2, w: 0.5, h: 0.5 }}
            baseWidth={1200}
            baseHeight={800}
            style={{ width: 400, height: 300 }}
          />
          <div style={{ color: "#67e8f9", fontSize: 28, fontWeight: 600 }}>1. {calloutsDict.import}</div>
        </div>

        {/* Step 2: Reconcile / Automate */}
        <div
          style={{
            transform: `scale(${spring({ frame: frame - 80, fps, config: { damping: 14 } })})`,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 20,
          }}
        >
          <ScreenCrop
            src={schedulerConfig}
            crop={{ x: 0.2, y: 0.2, w: 0.6, h: 0.5 }}
            baseWidth={1200}
            baseHeight={800}
            style={{ width: 400, height: 300 }}
          />
          <div style={{ color: "#34d399", fontSize: 28, fontWeight: 600 }}>2. {calloutsDict.automate}</div>
        </div>
      </div>

      <AnimatedHeadline headline={t.headline} sub={t.sub} enterAt={180} />
    </SceneShell>
  );
};
