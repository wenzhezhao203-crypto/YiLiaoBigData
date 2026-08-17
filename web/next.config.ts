import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The dashboard is commonly opened as 127.0.0.1 while Next advertises localhost.
  // Permit the loopback origin so development chunks and HMR can load correctly.
  allowedDevOrigins: ["127.0.0.1"],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:5000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
