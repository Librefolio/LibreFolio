import React from "react";
import { useCurrentFrame, spring, useVideoConfig } from "remotion";
import { dictionaries } from "../i18n";
import { Locale } from "../types/i18n";

export const RepoCard: React.FC<{
  enterAt: number;
  locale: Locale;
}> = ({ enterAt, locale }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const dict = dictionaries[locale].repo;

  const scale = spring({
    frame: frame - enterAt,
    fps,
    config: { damping: 14, stiffness: 100 },
  });

  return (
    <div
      style={{
        transform: `scale(${scale})`,
        background: "rgba(129,140,248,0.12)",
        border: "2px solid rgba(129,140,248,0.5)",
        borderRadius: 24,
        padding: "32px 64px",
        backdropFilter: "blur(12px)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 16,
      }}
    >
      <div
        style={{
          background: "#818cf8",
          color: "#050510",
          padding: "6px 16px",
          borderRadius: 999,
          fontSize: 20,
          fontWeight: 800,
          textTransform: "uppercase",
          letterSpacing: "2px",
          marginBottom: 8,
        }}
      >
        {dict.alpha}
      </div>
      <p
        style={{
          color: "#fff",
          fontSize: 48,
          fontFamily: "system-ui, sans-serif",
          fontWeight: 700,
          margin: 0,
          display: "flex",
          alignItems: "center",
          gap: 16,
        }}
      >
        <svg height="48" viewBox="0 0 16 16" width="48" fill="white">
          <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
        </svg>
        {dict.url}
      </p>
    </div>
  );
};
