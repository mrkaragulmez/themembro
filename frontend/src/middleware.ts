// frontend/src/middleware.ts
// Faz 1 — Subdomain tenant routing middleware
//
// acme.localhost:3000 → X-Tenant-Slug: acme header eklenir
// app.themembro.com'daki acme.themembro.com trafik için aynı mantık

import { NextRequest, NextResponse } from "next/server";

/** Subdomain'den tenant slug çıkarır.
 *  acme.localhost → "acme"
 *  acme.themembro.com → "acme"
 *  www. veya app. ön ekleri tenant slug sayılmaz.
 */
function extractTenantSlug(host: string): string | null {
  const hostname = host.split(":")[0]; // portu ayır
  const parts = hostname.split(".");

  // localhost → tenant yok
  if (hostname === "localhost") return null;

  // iki parçalı alan (themembro.com, localhost) → tenant yok
  if (parts.length <= 2) return null;

  const subdomain = parts[0];

  // www veya app gerçek tenant değil
  if (["www", "app"].includes(subdomain)) return null;

  return subdomain;
}

export function middleware(request: NextRequest): NextResponse {
  const host = request.headers.get("host") ?? "";
  const tenantSlug = extractTenantSlug(host);

  const response = NextResponse.next();

  if (tenantSlug) {
    // Backend'e giden isteklerde taşınan header
    response.headers.set("x-tenant-slug", tenantSlug);
    // Client component'lerin erişebilmesi için cookie de set edilebilir (opsiyonel)
    response.cookies.set("tenant_slug", tenantSlug, {
      httpOnly: false,
      sameSite: "lax",
      path: "/",
    });
  }

  return response;
}

export const config = {
  // Static asset ve _next dosyalarına matcher uygulanmaz
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
