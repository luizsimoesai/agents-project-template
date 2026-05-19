import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  devIndicators: false,
  // Stable in Next 16; requires `babel-plugin-react-compiler` (devDependency).
  // Trade-off: enables auto-memoization but Babel adds compile-time cost.
  reactCompiler: true,
  // Stable in Next 16. Type-checks `href` against the live route tree.
  typedRoutes: true,
  experimental: {
    // lucide-react is already auto-optimized in Next 16; listed explicitly to
    // document intent and stay correct if Next changes the default list.
    optimizePackageImports: ["lucide-react"],
  },
}

export default nextConfig
