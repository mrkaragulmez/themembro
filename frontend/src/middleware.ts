// frontend/src/middleware.ts
// Faz 1 — Subdomain tenant routing middleware
// Faz 6.1 — JWT guard: korumalı rotalar token yoksa /login'e yönlendirir

import { NextRequest, NextResponse } from "next/server";

/** Subdomain'den tenant slug çıkarır. */
function extractTenantSlug(host: string): string | null {
  const hostname = host.split(":")[0];
  const parts = hostname.split(".");
  if (hostname === "localhost") return null;
  if (parts.length <= 2) return null;
  const subdomain = parts[0];
  if (["www", "app"].includes(subdomain)) return null;
  return subdomain;
}

// Giriş gerektirmeyen rotalar
const PUBLIC_PATHS = ["/login", "/register"];

// Middleware'in çalışmayacağı rotalar (static dosyalar, api, next internals)

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;
  const host = request.headers.get("host") ?? "";
  const tenantSlug = extractTenantSlug(host);

  // ─── JWT Guard ──────────────────────────────────────────────────────────────
  const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p));
  const token = request.cookies.get("access_token")?.value;

  if (!isPublic && !token) {
    // Token yok → login'e yönlendir (geri dönüş URL'ini parametre olarak taşı)
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (isPublic && token && pathname.startsWith("/login")) {
    // Zaten giriş yapmış → dashboard'a yönlendir
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  // ─── Tenant Header ──────────────────────────────────────────────────────────
  const response = NextResponse.next();

  if (tenantSlug) {
    response.headers.set("x-tenant-slug", tenantSlug);
    response.cookies.set("tenant_slug", tenantSlug, {
      httpOnly: false,
      sameSite: "lax",
      path: "/",
    });
  }

  return response;
}

export const config = {
  // Static asset, _next dosyaları ve Next.js API rotalarına matcher uygulanmaz
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|api/|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
