import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.ygoprodeck.com",
        pathname: "/**",
      },
    ],
  },
  // Allow server components to call the AI service directly
  experimental: {
    serverComponentsExternalPackages: ["sharp"],
  },
};

export default nextConfig;
