import React from "react";
import { Img } from "remotion";
import { CropRect } from "../config/crops";

export const ScreenCrop: React.FC<{
  src: string;
  crop: CropRect;
  baseWidth?: number;
  baseHeight?: number;
  style?: React.CSSProperties;
}> = ({ src, crop, baseWidth = 1920, baseHeight = 1080, style }) => {
  const innerWidth = baseWidth * crop.w;
  const innerHeight = baseHeight * crop.h;

  return (
    <div
      style={{
        width: innerWidth,
        height: innerHeight,
        overflow: "hidden",
        borderRadius: 16,
        boxShadow: "0 20px 60px rgba(0,0,0,0.6)",
        position: "relative",
        ...style,
      }}
    >
      <Img
        src={src}
        style={{
          position: "absolute",
          width: baseWidth,
          height: baseHeight,
          left: -crop.x * baseWidth,
          top: -crop.y * baseHeight,
          objectFit: "none",
        }}
      />
    </div>
  );
};
