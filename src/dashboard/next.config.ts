import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  // Base path for the dashboard when mounted in FastAPI
  basePath: '/dashboard',
  images: {
    unoptimized: true,
  },
  // Rewrites only work in development (npm run dev)
  // In production expert, API calls should be relative path based
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8080/api/v1/:path*',
      },
    ];
  },
};

export default nextConfig;
