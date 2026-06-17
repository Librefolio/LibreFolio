import React from "react";
import { useCurrentFrame, staticFile, interpolate, spring, useVideoConfig, Img } from "remotion";
import { SceneShell } from "../components/SceneShell";
import { AnimatedHeadline } from "../components/AnimatedHeadline";
import { PhoneMockup } from "../components/PhoneMockup";
import { dictionaries } from "../i18n";
import { Locale } from "../types/i18n";

export const Scene05Mobile: React.FC<{ locale: Locale }> = ({ locale }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = dictionaries[locale].scene05;
  const badges = dictionaries[locale].badges;

  const mobileDashboard = staticFile(`assets/${locale}/dark/mobile/dashboard/main.png`);
  const mobileList = staticFile(`assets/${locale}/dark/mobile/assets/list.png`);
  const desktopBg = staticFile(`assets/${locale}/dark/desktop/dashboard/main.png`);

  const phoneY = spring({
    frame: frame - 10,
    fps,
    config: { damping: 16, stiffness: 80 },
    from: 1000,
    to: 0,
  });

  const swipeProgress = spring({
    frame: frame - 80,
    fps,
    config: { damping: 18, stiffness: 90 },
  });

  return (
    <SceneShell bg="#050510">
      {/* AI background */}
      <Img
        src={staticFile("ai/device_sync_bg.png")}
        onError={(e) => { e.currentTarget.style.display = 'none'; }}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
          filter: "brightness(0.4)",
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
        {/* Phone Mockup with swipe animation */}
        <div style={{ transform: `translateY(${phoneY}px)`, position: "relative", width: 360, height: 720 }}>
          <div style={{ position: "absolute", inset: 0, opacity: interpolate(swipeProgress, [0, 1], [1, 0]) }}>
            <PhoneMockup src={mobileDashboard} />
          </div>
          <div style={{ position: "absolute", inset: 0, opacity: interpolate(swipeProgress, [0, 1], [0, 1]) }}>
            <PhoneMockup src={mobileList} />
          </div>
        </div>

        {/* Badges */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {[badges.mobileReady, badges.darkLight, badges.multiLanguage].map((badge, i) => (
            <div
              key={badge}
              style={{
                transform: `translateX(${spring({ frame: frame - (40 + i * 15), fps, config: { damping: 14 } }) * 0 + interpolate(frame - (40 + i * 15), [0, 15], [200, 0], { extrapolateRight: "clamp" })}px)`,
                opacity: interpolate(frame - (40 + i * 15), [0, 15], [0, 1], { extrapolateRight: "clamp" }),
                background: "rgba(10, 10, 26, 0.8)",
                border: "1px solid rgba(103, 232, 249, 0.4)",
                padding: "16px 32px",
                borderRadius: 16,
                color: "#67e8f9",
                fontSize: 32,
                fontWeight: 600,
                backdropFilter: "blur(12px)",
              }}
            >
              {badge}
            </div>
          ))}
        </div>
      </div>

      <AnimatedHeadline headline={t.headline} sub={t.sub} enterAt={140} />
    </SceneShell>
  );
};
