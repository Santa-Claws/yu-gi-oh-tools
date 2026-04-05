import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
  serverExternalPackages: ["sharp"],
};

export default nextConfig;
