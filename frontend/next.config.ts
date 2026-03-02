// frontend/next.config.ts
// Faz 1 — Next.js konfigürasyonu

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // API istekleri backend'e yönlendirilir (Docker ağında "backend" hostname)
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? "http://backend:8000"}/api/:path*`,
      },
    ];
  },
  // Güvenli resim domain'leri (ileride genişletilecek)
  images: {
    domains: ["localhost"],
  },
};

export default nextConfig;
