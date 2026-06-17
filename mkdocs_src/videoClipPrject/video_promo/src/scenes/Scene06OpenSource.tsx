import React from "react";
import { useCurrentFrame, staticFile, interpolate, Img } from "remotion";
import { SceneShell } from "../components/SceneShell";
import { AnimatedHeadline } from "../components/AnimatedHeadline";
import { FeaturePill } from "../components/FeaturePill";
import { dictionaries } from "../i18n";
import { Locale } from "../types/i18n";

export const Scene06OpenSource: React.FC<{ locale: Locale }> = ({ locale }) => {
  const frame = useCurrentFrame();
  const t = dictionaries[locale].scene06;
  const badges = dictionaries[locale].badges;

  const bgScale = interpolate(frame, [0, 240], [1.1, 1.0], { extrapolateRight: "clamp" });

  const pillars = [
    { icon: "🔓", label: badges.openSource, delay: 30, color: "#34d399" },
    { icon: "🖥️", label: badges.selfHosted, delay: 60, color: "#60a5fa" },
    { icon: "☁️", label: badges.cloudComingSoon, delay: 90, color: "#c084fc" },
  ];

  const extraPillars = [
    { icon: "🧩", label: badges.extendable, delay: 120, color: "#fbbf24" },
    { icon: "🛡️", label: badges.privacyFirst, delay: 150, color: "#818cf8" },
  ];

  return (
    <SceneShell bg="#0f2027">
      <Img
        src={staticFile("ai/open_network_bg.png")}
        onError={(e) => { e.currentTarget.style.display = 'none'; }}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
          opacity: 0.25,
          transform: `scale(${bgScale})`,
          filter: "blur(4px) saturate(1.2)",
        }}
      />

      <div
        style={{
          position: "relative",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          gap: 32,
        }}
      >
        <div style={{ display: "flex", gap: 32 }}>
          {pillars.map((p) => (
            <FeaturePill key={p.label} {...p} />
          ))}
        </div>
        <div style={{ display: "flex", gap: 32 }}>
          {extraPillars.map((p) => (
            <FeaturePill key={p.label} {...p} />
          ))}
        </div>
      </div>

      <AnimatedHeadline headline={t.headline} sub={t.sub} enterAt={160} />
    </SceneShell>
  );
};
