import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          // Prevent clickjacking
          { key: "X-Frame-Options", value: "DENY" },
          // Prevent MIME-type sniffing
          { key: "X-Content-Type-Options", value: "nosniff" },
          // Control referrer information
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          // Restrict browser features
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
          // Force HTTPS for 1 year (only effective when served over HTTPS)
          { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
          // Content Security Policy — tightened by the server-side API proxy (connect-src 'self')
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              // Next.js injects inline hydration scripts; unsafe-eval needed for webpack
              "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
              // React/Framer Motion use inline style attributes
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob:",
              // All browser API calls go through the same-origin /api proxy
              "connect-src 'self'",
              "font-src 'self'",
              "object-src 'none'",
              // PDF preview iframes use blob: URLs created from fetched PDF bytes
              "frame-src blob:",
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self'",
            ].join("; "),
          },
        ],
      },
    ];
  },
};

export default nextConfig;
