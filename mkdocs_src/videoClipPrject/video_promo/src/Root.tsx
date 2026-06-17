// src/Root.tsx
import React from "react";
import { Composition } from "remotion";
import { LibreFolioPromo } from "./MainVideo";
import { Locale } from "./types/i18n";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="LibreFolioPromo"
    component={LibreFolioPromo}
    durationInFrames={1200}
    fps={30}
    width={1920}
    height={1080}
    defaultProps={{ locale: "en" as Locale }}
  />
);
