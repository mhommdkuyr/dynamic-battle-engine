import React from "react";
import { AbsoluteFill } from "remotion";

export const ImpactFrame: React.FC = () => {
  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#ffffff",
        filter: "invert(100%)",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        style={{
          width: "400px",
          height: "400px",
          border: "8px solid #ffffff",
          borderRadius: "50%",
          boxShadow: "0 0 50px #ffffff",
        }}
      />
    </AbsoluteFill>
  );
};
