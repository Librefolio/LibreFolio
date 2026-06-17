import React from "react";
import { Composition } from "remotion";
import { LibreFolioPromo } from "./MainVideo";
import { videoPlan } from "./config/videoPlan";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Build EN */}
      <Composition
        id="LibreFolioPromo-EN"
        component={LibreFolioPromo}
        durationInFrames={videoPlan.durationInFrames}
        fps={videoPlan.fps}
        width={1920}
        height={1080}
        defaultProps={{ locale: "en" as const }}
      />
      {/* Build IT */}
      <Composition
        id="LibreFolioPromo-IT"
        component={LibreFolioPromo}
        durationInFrames={videoPlan.durationInFrames}
        fps={videoPlan.fps}
        width={1920}
        height={1080}
        defaultProps={{ locale: "it" as const }}
      />
      {/* Build ES */}
      <Composition
        id="LibreFolioPromo-ES"
        component={LibreFolioPromo}
        durationInFrames={videoPlan.durationInFrames}
        fps={videoPlan.fps}
        width={1920}
        height={1080}
        defaultProps={{ locale: "es" as const }}
      />
      {/* Build FR */}
      <Composition
        id="LibreFolioPromo-FR"
        component={LibreFolioPromo}
        durationInFrames={videoPlan.durationInFrames}
        fps={videoPlan.fps}
        width={1920}
        height={1080}
        defaultProps={{ locale: "fr" as const }}
      />
    </>
  );
};
