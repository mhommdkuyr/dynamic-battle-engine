// Vercel Serverless Handler for MCP Server
export default async function handler(req: any, res: any) {
  if (req.method === "GET") {
    return res.status(200).json({
      name: "dynamic-battle-engine-mcp",
      status: "ready",
      version: "1.0.0",
      description: "MCP TypeScript Server on Vercel for high-speed combat animation pipeline.",
      tools: [
        "render_combat_scene",
        "generate_blender_grease_pencil",
        "extract_reference_poses"
      ]
    });
  }

  if (req.method === "POST") {
    const { tool, params } = req.body || {};
    return res.status(200).json({
      success: true,
      executed_tool: tool,
      result: `Dispatched ${tool} with params: ${JSON.stringify(params)}`,
      timestamp: new Date().toISOString()
    });
  }

  res.setHeader("Allow", ["GET", "POST"]);
  res.status(405).end(`Method ${req.method} Not Allowed`);
}
