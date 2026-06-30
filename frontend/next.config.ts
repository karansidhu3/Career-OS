import type { NextConfig } from "next";

// Clerk publishable keys are "pk_test_" or "pk_live_" followed by base64 of
// "<frontend-api-domain>$". Decoding it (rather than hardcoding a domain) means
// the CSP automatically tracks whichever Clerk instance (dev or prod) is configured.
function clerkFrontendApiDomain(): string | null {
  const key = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  if (!key) return null;
  const encoded = key.replace(/^pk_(test|live)_/, "");
  try {
    return Buffer.from(encoded, "base64").toString("utf-8").replace(/\$$/, "");
  } catch {
    return null;
  }
}

const nextConfig: NextConfig = {
  async headers() {
    const clerkDomain = clerkFrontendApiDomain();
    const clerkOrigin = clerkDomain ? `https://${clerkDomain}` : "";

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
          // Content Security Policy — tightened by the server-side API proxy (connect-src 'self').
          // Clerk needs its frontend API origin in script-src/connect-src (loads clerk.browser.js
          // and makes auth calls from the browser) and challenges.cloudflare.com for bot protection.
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              // Next.js injects inline hydration scripts; unsafe-eval needed for webpack.
              // Clerk's SDK is loaded from its own frontend API origin, not bundled.
              `script-src 'self' 'unsafe-inline' 'unsafe-eval' ${clerkOrigin} https://challenges.cloudflare.com`,
              // React/Framer Motion use inline style attributes; Clerk uses runtime CSS-in-JS
              "style-src 'self' 'unsafe-inline'",
              `img-src 'self' data: blob: https://img.clerk.com`,
              // App API calls go through the same-origin /api proxy; Clerk's own SDK calls its FAPI directly
              `connect-src 'self' ${clerkOrigin}`,
              "font-src 'self'",
              "object-src 'none'",
              // PDF preview iframes use blob: URLs; Cloudflare bot-protection challenge needs its own frame
              "frame-src blob: https://challenges.cloudflare.com",
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self'",
              "worker-src 'self' blob:",
            ].join("; "),
          },
        ],
      },
    ];
  },
};

export default nextConfig;
