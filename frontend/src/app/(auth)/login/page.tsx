/**
 * frontend/src/app/(auth)/login/page.tsx
 * Faz 6 — Giriş ekranı
 * email + password → authApi.login → localStorage token + user_info → /dashboard
 */

"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authApi, setTokens } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const tokens = await authApi.login(email, password);
      setTokens(tokens.access_token, email);
      const next = searchParams.get("next") ?? "/dashboard";
      router.replace(next);
    } catch {
      setError("E-posta veya şifre hatalı. Lütfen tekrar deneyin.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full max-w-sm">
      {/* Logo */}
      <div className="text-center mb-8">
        <span className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-brand-navy text-white font-bold text-xl">
          M
        </span>
        <h1 className="mt-4 text-2xl font-bold text-text-primary">Membro'ya Hoş Geldin</h1>
        <p className="mt-1 text-sm text-text-secondary">Hesabına giriş yap</p>
      </div>

      {/* Kart */}
      <form
        onSubmit={handleSubmit}
        className="bg-surface-0 border border-border-default rounded-2xl p-6 shadow-sm space-y-4"
      >
        <Input
          label="E-posta"
          type="email"
          placeholder="isim@sirket.com"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <Input
          label="Şifre"
          type="password"
          placeholder="••••••••"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        {error && (
          <p className="text-sm text-error bg-error/5 border border-error/20 rounded-xl px-3 py-2">
            {error}
          </p>
        )}

        <Button
          variant="primary"
          size="lg"
          type="submit"
          loading={loading}
          className="w-full"
        >
          Giriş Yap
        </Button>
      </form>


    </div>
  );
}
