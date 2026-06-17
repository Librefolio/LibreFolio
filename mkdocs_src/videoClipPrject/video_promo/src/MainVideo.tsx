import React from "react";
import { Series, Audio, staticFile, AbsoluteFill } from "remotion";
import { Locale } from "./types/i18n";
import { Scene01Hook } from "./scenes/Scene01Hook";
import { Scene02Hero } from "./scenes/Scene02Hero";
import { Scene03MultiAsset } from "./scenes/Scene03MultiAsset";
import { Scene04Import } from "./scenes/Scene04Import";
import { Scene05Mobile } from "./scenes/Scene05Mobile";
import { Scene06OpenSource } from "./scenes/Scene06OpenSource";
import { Scene07CTA } from "./scenes/Scene07CTA";
import { videoPlan } from "./config/videoPlan";

export interface MainVideoProps {
  locale: Locale;
}

export const LibreFolioPromo: React.FC<MainVideoProps> = ({ locale }) => (
  <AbsoluteFill>
    <Audio src={staticFile("ai/audio_track_main_54s_fade.mp3")} />
    <Series>
      <Series.Sequence durationInFrames={videoPlan.scenes.scene01.durationInFrames}>
        <Scene01Hook locale={locale} />
      </Series.Sequence>

      <Series.Sequence durationInFrames={videoPlan.scenes.scene02.durationInFrames}>
        <Scene02Hero locale={locale} />
      </Series.Sequence>

      <Series.Sequence durationInFrames={videoPlan.scenes.scene03.durationInFrames}>
        <Scene03MultiAsset locale={locale} />
      </Series.Sequence>

      <Series.Sequence durationInFrames={videoPlan.scenes.scene04.durationInFrames}>
        <Scene04Import locale={locale} />
      </Series.Sequence>

      <Series.Sequence durationInFrames={videoPlan.scenes.scene05.durationInFrames}>
        <Scene05Mobile locale={locale} />
      </Series.Sequence>

      <Series.Sequence durationInFrames={videoPlan.scenes.scene06.durationInFrames}>
        <Scene06OpenSource locale={locale} />
      </Series.Sequence>

      <Series.Sequence durationInFrames={videoPlan.scenes.scene07.durationInFrames}>
        <Scene07CTA locale={locale} />
      </Series.Sequence>
    </Series>
  </AbsoluteFill>
);
