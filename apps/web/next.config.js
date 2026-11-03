// Build-time safety guard: ensure no privileged API keys ('th_live_') or secrets are bundled into client JavaScript
const forbiddenPrefixes = ["th_live_", "sk-", "ghp_"];
for (const [key, val] of Object.entries(process.env)) {
  if (key.startsWith("NEXT_PUBLIC_") && typeof val === "string") {
    for (const prefix of forbiddenPrefixes) {
      if (val.trim().startsWith(prefix)) {
        throw new Error(
          `SECURITY BLOCKED: Privileged credential detected in client-side environment variable '${key}'. ` +
          `Variables prefixed with NEXT_PUBLIC_ are bundled into browser JavaScript. ` +
          `Live keys ('${prefix}...') must never be exposed publicly. ` +
          `Use public demo mode (DEMO_MODE=true on the backend) or a restricted demo key ('th_demo_...').`
        );
      }
    }
  }
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  output: "standalone",
};

module.exports = nextConfig;
