// frontend/next.config.ts
// Faz 1 — Next.js konfigürasyonu

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // API istekleri backend'e yönlendirilir
  // BACKEND_URL: Docker içi Next.js → backend iç ağ adresi (browser'a açılmaz)
  // NEXT_PUBLIC_API_URL olmadığında browser göreceli /api/... kullanır → Nginx proxy eder
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_URL ?? "http://backend:8000"}/api/:path*`,
      },
    ];
  },
  // Güvenli resim domain'leri (ileride genişletilecek)
  images: {
    domains: ["localhost"],
  },
};

export default nextConfig;
