// src/MainVideo.tsx
// Orchestrates all 6 scenes using <Series>.
// Total: 1200 frames @ 30fps = 40 seconds.
//
// Scene timing:
//   Scene01 Hook        150f  (5s)
//   Scene02 Hero        210f  (7s)
//   Scene03 MultiAsset  240f  (8s)
//   Scene04 Mobile      240f  (8s)
//   Scene05 OpenSource  210f  (7s)
//   Scene06 CTA         150f  (5s)

import React from "react";
import { Series, Audio, staticFile, AbsoluteFill } from "remotion";
import { Locale } from "./types/i18n";
import { Scene01Hook } from "./scenes/Scene01Hook";
import { Scene02Hero } from "./scenes/Scene02Hero";
import { Scene03MultiAsset } from "./scenes/Scene03MultiAsset";
import { Scene04Mobile } from "./scenes/Scene04Mobile";
import { Scene05OpenSource } from "./scenes/Scene05OpenSource";
import { Scene06CTA } from "./scenes/Scene06CTA";

export interface MainVideoProps {
  locale: Locale;
}

export const LibreFolioPromo: React.FC<MainVideoProps> = ({ locale }) => (
  <AbsoluteFill>
    <Audio src={staticFile("ai/audio_track.mp3")} />
    <Series>
      <Series.Sequence durationInFrames={150}>
        <Scene01Hook locale={locale} />
      </Series.Sequence>

      <Series.Sequence durationInFrames={210}>
        <Scene02Hero locale={locale} />
      </Series.Sequence>

      <Series.Sequence durationInFrames={240}>
        <Scene03MultiAsset locale={locale} />
      </Series.Sequence>

      <Series.Sequence durationInFrames={240}>
        <Scene04Mobile locale={locale} />
      </Series.Sequence>

      <Series.Sequence durationInFrames={210}>
        <Scene05OpenSource locale={locale} />
      </Series.Sequence>

      <Series.Sequence durationInFrames={150}>
        <Scene06CTA locale={locale} />
      </Series.Sequence>
    </Series>
  </AbsoluteFill>
);
