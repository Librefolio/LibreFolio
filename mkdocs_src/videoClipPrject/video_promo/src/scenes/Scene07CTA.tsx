import React from "react";
import { useCurrentFrame, staticFile, interpolate, Img, Audio } from "remotion";
import { SceneShell } from "../components/SceneShell";
import { AnimatedHeadline } from "../components/AnimatedHeadline";
import { RepoCard } from "../components/RepoCard";
import { dictionaries } from "../i18n";
import { Locale } from "../types/i18n";

export const Scene07CTA: React.FC<{ locale: Locale }> = ({ locale }) => {
  const frame = useCurrentFrame();
  const t = dictionaries[locale].scene07;

  const logoScale = interpolate(frame, [0, 60], [0.5, 1.0], { extrapolateRight: "clamp" });
  const logoOpacity = interpolate(frame, [0, 40], [0, 1], { extrapolateRight: "clamp" });

  return (
    <SceneShell bg="#0A0A1A">
      <Audio src={staticFile("ai/sfx_logo_sting_cut_a.mp3")} volume={0.8} />
      <Img
        src={staticFile("ai/cta_particles_bg.png")}
        onError={(e) => { e.currentTarget.style.display = 'none'; }}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
          opacity: 0.6,
          filter: "brightness(0.5)",
        }}
      />
      {/* Particles effect simulated via static CSS radial gradients + slight movement */}
      <div
        style={{
          position: "absolute",
          inset: -200,
          backgroundImage: "radial-gradient(2px 2px at 10% 15%, rgba(129,140,248,0.4) 0%, transparent 100%), radial-gradient(3px 3px at 25% 40%, rgba(103,232,249,0.3) 0%, transparent 100%), radial-gradient(2px 2px at 60% 20%, rgba(129,140,248,0.5) 0%, transparent 100%), radial-gradient(3px 3px at 80% 70%, rgba(103,232,249,0.4) 0%, transparent 100%), radial-gradient(2px 2px at 45% 80%, rgba(129,140,248,0.3) 0%, transparent 100%)",
          transform: `scale(${interpolate(frame, [0, 210], [1.0, 1.2])}) rotate(${interpolate(frame, [0, 210], [0, 5])}deg)`,
          opacity: 0.8,
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
          gap: 60,
        }}
      >
        <div style={{ transform: `scale(${logoScale})`, opacity: logoOpacity, position: "relative" }}>
          <div
            style={{
              position: "absolute",
              inset: -40,
              borderRadius: "50%",
              background: "radial-gradient(circle, rgba(129,140,248,0.4) 0%, transparent 70%)",
              filter: "blur(20px)",
            }}
          />
          <div
            style={{
              background: "white",
              width: 220,
              height: 220,
              borderRadius: 36,
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              position: "relative",
              boxShadow: "0 20px 50px rgba(0,0,0,0.6)",
            }}
          >
            <Img src={staticFile("assets/shared/logo.png")} style={{ height: 150, width: "auto" }} />
          </div>
        </div>

        <AnimatedHeadline headline={t.headline} sub={t.sub} enterAt={60} yOffset={20} />

        <div style={{ marginTop: 120 }}>
          <RepoCard enterAt={120} locale={locale} />
        </div>
      </div>
    </SceneShell>
  );
};
