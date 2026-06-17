import React from "react";

export type ShardVariant = "hero" | "medium" | "small";
export type ShardVisualType = "table" | "formats" | "grid" | "fx" | "wallet" | "duplicates" | "chartNoise" | "reports" | "alerts";

export const ProblemShard: React.FC<{
  title: string;
  subtitle: string;
  iconPath: string;
  opacity: number;
  scale: number;
  blur: number;
  x: number;
  y: number;
  rotation: number;
  variant: ShardVariant;
  visualType?: ShardVisualType;
}> = ({ title, subtitle, iconPath, opacity, scale, blur, x, y, rotation, variant, visualType }) => {
  
  let width = 280;
  let height = 80;
  let iconSize = 48;
  let titleSize = 18;
  let subSize = 13;

  if (variant === "hero") {
    width = 380;
    height = 140;
    iconSize = 56;
    titleSize = 22;
    subSize = 15;
  } else if (variant === "small") {
    width = 220;
    height = 76;
    iconSize = 36;
    titleSize = 15;
    subSize = 11;
  }

  const renderVisual = () => {
    if (!visualType) return null;

    const visualStyle: React.CSSProperties = {
      flex: 1,
      display: "flex",
      alignItems: "center",
      justifyContent: "flex-end",
      marginLeft: "16px",
      opacity: 0.8,
    };

    switch (visualType) {
      case "table":
        return (
          <div style={{ ...visualStyle, flexDirection: "column", alignItems: "flex-end", gap: 4, opacity: 0.6 }}>
            <div style={{ display: "flex", gap: 12, fontSize: 10, fontFamily: "monospace", color: "#a78bfa" }}>
              <span>Date</span><span>Qty</span><span>Fee</span>
            </div>
            <div style={{ display: "flex", gap: 12 }}>
              <div style={{ width: 24, height: 2, background: "rgba(255,255,255,0.4)" }}/>
              <div style={{ width: 12, height: 2, background: "rgba(255,255,255,0.4)" }}/>
              <div style={{ width: 8, height: 2, background: "rgba(255,255,255,0.4)" }}/>
            </div>
            <div style={{ display: "flex", gap: 12 }}>
              <div style={{ width: 24, height: 2, background: "rgba(255,255,255,0.4)" }}/>
              <div style={{ width: 12, height: 2, background: "rgba(255,255,255,0.4)" }}/>
              <div style={{ width: 8, height: 2, background: "rgba(255,255,255,0.4)" }}/>
            </div>
          </div>
        );
      case "formats":
        return (
          <div style={{ ...visualStyle, gap: 6, fontSize: 12, color: "#fff", fontWeight: 600 }}>
            <span style={{ padding: "2px 6px", background: "rgba(255,255,255,0.1)", borderRadius: 4 }}>CSV</span>
            <span style={{ color: "rgba(255,255,255,0.3)" }}>→</span>
            <span style={{ padding: "2px 6px", background: "rgba(255,255,255,0.1)", borderRadius: 4 }}>PDF</span>
            <span style={{ color: "rgba(255,255,255,0.3)" }}>→</span>
            <span style={{ padding: "2px 6px", background: "rgba(255,255,255,0.1)", borderRadius: 4 }}>XLS</span>
          </div>
        );
      case "grid":
        return (
          <div style={{ ...visualStyle, flexDirection: "column", gap: 4 }}>
            <div style={{ display: "flex", gap: 4 }}>
              {[1, 2, 3, 4].map(i => <div key={i} style={{ width: 16, height: 10, background: "rgba(167,139,250,0.3)", borderRadius: 2 }} />)}
            </div>
            <div style={{ display: "flex", gap: 4 }}>
              {[1, 2, 3, 4].map(i => <div key={i} style={{ width: 16, height: 10, background: "rgba(255,255,255,0.1)", borderRadius: 2 }} />)}
            </div>
            <div style={{ display: "flex", gap: 4 }}>
              {[1, 2, 3, 4].map(i => <div key={i} style={{ width: 16, height: 10, background: "rgba(255,255,255,0.1)", borderRadius: 2 }} />)}
            </div>
          </div>
        );
      case "fx":
        return (
          <div style={{ ...visualStyle, fontSize: 16, fontWeight: 700, color: "#fff", gap: 8 }}>
            <span>🇪🇺 EUR</span>
            <span style={{ color: "#a78bfa" }}>⇄</span>
            <span>USD 🇺🇸</span>
          </div>
        );
      case "wallet":
        return (
          <div style={{ ...visualStyle, gap: 8 }}>
            <div style={{ width: 24, height: 16, borderRadius: 4, background: "rgba(167,139,250,0.4)" }} />
            <div style={{ width: 24, height: 16, borderRadius: 4, background: "rgba(255,255,255,0.2)" }} />
            <div style={{ width: 24, height: 16, borderRadius: 4, background: "rgba(255,255,255,0.1)" }} />
          </div>
        );
      case "duplicates":
        return (
          <div style={{ ...visualStyle, flexDirection: "column", gap: 6, fontSize: 11, fontFamily: "monospace", color: "#e2e8f0" }}>
            <div style={{ display: "flex", gap: 8, background: "rgba(255,0,0,0.1)", padding: "2px 6px", borderRadius: 4 }}>
              <span>#1284</span><span style={{ color: "#10b981" }}>BUY</span>
            </div>
            <div style={{ display: "flex", gap: 8, background: "rgba(255,0,0,0.1)", padding: "2px 6px", borderRadius: 4 }}>
              <span>#1284</span><span style={{ color: "#10b981" }}>BUY</span>
            </div>
          </div>
        );
      case "chartNoise":
        return (
          <div style={{ ...visualStyle }}>
            <svg width="60" height="30" viewBox="0 0 60 30" fill="none" stroke="#ef4444" strokeWidth="2" strokeLinejoin="round">
              <path d="M0 20 L10 10 L15 25 L25 5 L35 20 L40 10 L45 25 L60 0" />
            </svg>
          </div>
        );
      case "reports":
        return (
          <div style={{ ...visualStyle, position: "relative", width: 40, height: 40 }}>
            <div style={{ position: "absolute", bottom: 0, left: 0, width: 24, height: 32, background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.3)", borderRadius: 3, transform: "rotate(-15deg)" }} />
            <div style={{ position: "absolute", bottom: 2, left: 6, width: 24, height: 32, background: "rgba(167,139,250,0.2)", border: "1px solid rgba(167,139,250,0.5)", borderRadius: 3, transform: "rotate(-5deg)" }} />
            <div style={{ position: "absolute", bottom: 4, left: 12, width: 24, height: 32, background: "rgba(255,255,255,0.2)", border: "1px solid rgba(255,255,255,0.6)", borderRadius: 3, transform: "rotate(5deg)" }} />
          </div>
        );
      case "alerts":
        return (
          <div style={{ ...visualStyle, gap: 6 }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#ef4444", boxShadow: "0 0 8px #ef4444" }} />
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#f59e0b", boxShadow: "0 0 8px #f59e0b" }} />
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        transform: `translate(${x}px, ${y}px) scale(${scale}) rotate(${rotation}deg)`,
        opacity,
        filter: `blur(${blur}px)`,
        background: "rgba(10, 10, 20, 0.6)",
        border: "1px solid rgba(139, 92, 246, 0.4)",
        borderRadius: 20,
        padding: "16px 24px",
        display: "flex",
        alignItems: "center",
        gap: 16,
        boxShadow: "0 8px 32px rgba(139, 92, 246, 0.15), inset 0 1px 0 rgba(255,255,255,0.1)",
        backdropFilter: "blur(12px)",
        width,
        height,
      }}
    >
      <div
        style={{
          width: iconSize,
          height: iconSize,
          borderRadius: 12,
          background: "rgba(139, 92, 246, 0.2)",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          flexShrink: 0,
        }}
      >
        <svg width={iconSize * 0.5} height={iconSize * 0.5} viewBox="0 0 24 24" fill="none" stroke="#a78bfa" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d={iconPath} />
        </svg>
      </div>
      <div style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <div style={{ color: "#fff", fontSize: titleSize, fontWeight: 600, fontFamily: "system-ui, sans-serif" }}>
          {title}
        </div>
        <div style={{ color: "#a78bfa", fontSize: subSize, fontWeight: 400, marginTop: 4, fontFamily: "system-ui, sans-serif" }}>
          {subtitle}
        </div>
      </div>
      
      {renderVisual()}

      {/* Micro pattern highlight */}
      <div 
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: "linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 100%)",
          borderRadius: 20,
          pointerEvents: "none",
        }}
      />
    </div>
  );
};
