import React from "react";
import { AbsoluteFill } from "remotion";

interface Props {
  frame: number;
  children: React.ReactNode;
}

export const CameraShake: React.FC<Props> = ({ frame, children }) => {
  // Simple trauma decay shake simulation
  const isClash = frame >= 18 && frame <= 35;
  const shakeX = isClash ? Math.sin(frame * 2.5) * 18 : 0;
  const shakeY = isClash ? Math.cos(frame * 3.1) * 12 : 0;
  const rotate = isClash ? Math.sin(frame * 1.8) * 2.5 : 0;
  const zoom = isClash ? 1.15 : 1.0;

  return (
    <AbsoluteFill
      style={{
        transform: `translate(${shakeX}px, ${shakeY}px) rotate(${rotate}deg) scale(${zoom})`,
        transformOrigin: "center center",
      }}
    >
      {children}
    </AbsoluteFill>
  );
};
