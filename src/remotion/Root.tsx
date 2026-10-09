import React from "react";
import { Composition } from "remotion";
import { CombatScene } from "./CombatScene";

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="CombatScene"
        component={CombatScene}
        durationInFrames={180}
        fps={60}
        width={1920}
        height={1080}
      />
    </>
  );
};
