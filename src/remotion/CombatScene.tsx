import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { ActionLines } from "./components/ActionLines";
import { ImpactFrame } from "./components/ImpactFrame";
import { CameraShake } from "./components/CameraShake";

export const CombatScene: React.FC = () => {
  const frame = useCurrentFrame();

  // Impact trigger at frame 18 and 60
  const isImpact = (frame >= 18 && frame <= 20) || (frame >= 60 && frame <= 62);

  return (
    <AbsoluteFill style={{ backgroundColor: "#121218" }}>
      <CameraShake frame={frame}>
        {/* Arena Floor */}
        <div
          style={{
            position: "absolute",
            top: "810px",
            left: 0,
            right: 0,
            height: "4px",
            backgroundColor: "#2d2d3c",
          }}
        />

        {/* Speed Action Lines during rushes */}
        {((frame >= 0 && frame < 18) || (frame >= 24 && frame < 48)) && (
          <ActionLines />
        )}

        {/* Impact Flash Frames */}
        {isImpact && <ImpactFrame />}
      </CameraShake>
    </AbsoluteFill>
  );
};
