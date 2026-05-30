import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",

  // Proxy API requests to the FastAPI backend during development.
  // WebSocket connections are made directly from the browser to the
  // backend URL (NEXT_PUBLIC_WS_URL) so they don't need a rewrite.
  async rewrites() {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
