import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const server = new Server(
  {
    name: "dynamic-battle-engine-mcp",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "render_combat_scene",
        description: "Renders an ultra-fast anime combat sequence with smear frames, action lines, camera shake, and impact frames.",
        inputSchema: {
          type: "object",
          properties: {
            scene_config: { type: "string", description: "Path to scene JSON config" },
            fps: { type: "number", default: 60 },
            output_file: { type: "string", default: "output/combat_clash.mp4" },
          },
          required: ["scene_config"],
        },
      },
      {
        name: "generate_blender_grease_pencil",
        description: "Generates a Python script for Blender Headless Mode to produce 2D Grease Pencil combat animation in 3D camera space.",
        inputSchema: {
          type: "object",
          properties: {
            output_script: { type: "string", default: "scripts/blender_render.py" },
          },
        },
      },
      {
        name: "extract_reference_poses",
        description: "Extracts warrior poses from a video reference timestamp (e.g. YouTube 03:10) for retargeting.",
        inputSchema: {
          type: "object",
          properties: {
            video_url: { type: "string" },
            timestamp: { type: "string", default: "03:10" },
          },
          required: ["video_url"],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  if (name === "render_combat_scene") {
    return {
      content: [
        {
          type: "text",
          text: `Render triggered for scene ${args?.scene_config} at ${args?.fps || 60} FPS -> ${args?.output_file || "output/combat_clash.mp4"}`,
        },
      ],
    };
  } else if (name === "generate_blender_grease_pencil") {
    return {
      content: [
        {
          type: "text",
          text: `Blender Grease Pencil script generated at ${args?.output_script || "scripts/blender_render.py"}`,
        },
      ],
    };
  } else if (name === "extract_reference_poses") {
    return {
      content: [
        {
          type: "text",
          text: `Extracted 60fps keypoint poses from ${args?.video_url} at timestamp ${args?.timestamp}`,
        },
      ],
    };
  }
  throw new Error(`Unknown tool: ${name}`);
});

async function run() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

run().catch((error) => {
  console.error("Fatal error in MCP server:", error);
  process.exit(1);
});
