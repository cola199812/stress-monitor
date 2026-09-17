import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 关闭 Next.js Dev Indicators（开发时右下角/页面顶部的开发提示 UI）
  // 注意：修改后需重启 dev 服务器
  devIndicators: false,
  webpack: (config, { dev }) => {
    // 修复Windows环境下的webpack缓存问题
    if (dev) {
      config.cache = { type: "memory" };
    }
    
    if (process.env.NODE_ENV === "development") {
      config.module.rules.push({
        test: /\.(jsx|tsx)$/,
        exclude: /node_modules/,
        enforce: "pre",
        use: "@dyad-sh/nextjs-webpack-component-tagger",
      });
    }
    return config;
  },
};

export default nextConfig;
