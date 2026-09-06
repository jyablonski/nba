import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  output: "standalone",
  typescript: {
    tsconfigPath: "tsconfig.build.json",
  },
};

export default nextConfig;
