/**
 * frontend/src/app/not-found.tsx
 * Faz 6.5 — 404 sayfası
 */

import Link from "next/link";
import { FileQuestion } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-surface-0 flex items-center justify-center px-6">
      <div className="text-center animate-fade-in">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-surface-100 mb-6">
          <FileQuestion size={28} className="text-text-tertiary" />
        </div>
        <h1 className="text-4xl font-bold text-text-primary mb-2">404</h1>
        <p className="text-base text-text-secondary mb-6 max-w-xs mx-auto">
          Aradığın sayfa bulunamadı. Taşınmış ya da silinmiş olabilir.
        </p>
        <Link
          href="/dashboard"
          className="inline-flex items-center justify-center h-10 px-5 rounded-xl bg-brand-navy text-white text-sm font-medium hover:bg-brand-navy/90 transition-colors"
        >
          Anasayfaya Dön
        </Link>
      </div>
    </div>
  );
}
