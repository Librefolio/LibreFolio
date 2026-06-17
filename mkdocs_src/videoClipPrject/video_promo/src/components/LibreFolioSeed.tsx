import React from "react";
import { Img, staticFile } from "remotion";

export const LibreFolioSeed: React.FC<{
  scale: number;
  opacity: number;
  glow: number;
  showWordmark?: boolean;
  wordmark?: string;
  wordmarkOpacity?: number;
  layout?: "tile-only" | "horizontal-wordmark";
  tileSize?: number;
  iconSize?: number;
  wordmarkFontSize?: number;
  wordmarkGap?: number;
}> = ({ 
  scale, 
  opacity, 
  glow, 
  showWordmark, 
  wordmark, 
  wordmarkOpacity = 1,
  layout = "tile-only",
  tileSize: customTileSize,
  iconSize: customIconSize,
  wordmarkFontSize: customWordmarkFontSize,
  wordmarkGap: customWordmarkGap,
}) => {
  const isHorizontal = layout === "horizontal-wordmark";
  const tileSize = customTileSize ?? (isHorizontal ? 180 : 140);
  const iconSize = customIconSize ?? (isHorizontal ? 100 : 80);
  const gap = customWordmarkGap ?? (isHorizontal ? 32 : 24);
  const fontSize = customWordmarkFontSize ?? (isHorizontal ? 72 : 48);

  return (
    <div
      style={{
        position: "absolute",
        left: "50%",
        top: "50%",
        transform: `translate(-50%, -50%) scale(${scale})`,
        opacity,
        display: "flex",
        flexDirection: isHorizontal ? "row" : "column",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
        gap,
      }}
    >
      <div
        style={{
          width: tileSize,
          height: tileSize,
          background: "#ffffff",
          borderRadius: isHorizontal ? tileSize * 0.22 : 32,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          boxShadow: `0 0 ${glow * 60}px rgba(255, 255, 255, ${glow * 0.8}), 0 20px 40px rgba(0,0,0,0.4)`,
        }}
      >
        <Img 
          src={staticFile("assets/shared/logo.png")} 
          style={{ width: iconSize, height: iconSize, objectFit: "contain" }} 
        />
      </div>
      
      {showWordmark && wordmark && (
        <div style={{
          fontSize,
          fontWeight: 700,
          color: "white",
          letterSpacing: "-0.02em",
          textShadow: "0 10px 30px rgba(0,0,0,0.5)",
          opacity: wordmarkOpacity,
          fontFamily: "system-ui, -apple-system, sans-serif",
        }}>
          {wordmark}
        </div>
      )}
    </div>
  );
};
