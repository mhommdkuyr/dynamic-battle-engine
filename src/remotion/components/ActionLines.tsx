import React from "react";
import { AbsoluteFill } from "remotion";

export const ActionLines: React.FC = () => {
  return (
    <AbsoluteFill
      style={{
        backgroundImage:
          "repeating-radial-gradient(circle at 50% 65%, transparent 0, transparent 40px, rgba(255,255,255,0.25) 42px, transparent 44px)",
        pointerEvents: "none",
        mixBlendMode: "screen",
      }}
    />
  );
};
