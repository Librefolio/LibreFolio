import React from "react";
import { Img } from "remotion";

export const PhoneMockup: React.FC<{
  src: string;
  style?: React.CSSProperties;
}> = ({ src, style }) => {
  return (
    <div
      style={{
        width: 360,
        height: 720,
        borderRadius: 40,
        backgroundColor: "#000",
        border: "8px solid #333",
        boxShadow: "0 40px 100px rgba(0,0,0,0.8), 0 0 0 2px rgba(255,255,255,0.1)",
        overflow: "hidden",
        position: "relative",
        ...style,
      }}
    >
      {/* Notch */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: "50%",
          transform: "translateX(-50%)",
          width: 120,
          height: 30,
          backgroundColor: "#333",
          borderBottomLeftRadius: 16,
          borderBottomRightRadius: 16,
          zIndex: 10,
        }}
      />
      <Img
        src={src}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
        }}
      />
    </div>
  );
};
