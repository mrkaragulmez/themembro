/**
 * frontend/src/app/(shell)/error.tsx
 * Faz 6.5 — Shell layout için genel hata sınırlayıcı
 */

"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, RotateCcw, Home } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function ShellError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const router = useRouter();

  useEffect(() => {
    console.error("Shell error:", error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center h-full py-24 px-6 text-center animate-fade-in">
      <div className="w-14 h-14 rounded-2xl bg-error/10 flex items-center justify-center mb-5">
        <AlertTriangle size={24} className="text-error" />
      </div>

      <h2 className="text-xl font-bold text-text-primary mb-1">
        Bir şeyler ters gitti
      </h2>
      <p className="text-sm text-text-secondary max-w-sm mb-6">
        Sayfa yüklenirken hata oluştu. Yeniden deneyebilir veya ana sayfaya
        dönebilirsin.
      </p>

      {error.digest && (
        <p className="text-xs text-text-tertiary font-mono mb-6">
          Hata kodu: {error.digest}
        </p>
      )}

      <div className="flex gap-3">
        <Button
          variant="outline"
          size="md"
          icon={<Home size={15} />}
          iconPosition="left"
          onClick={() => router.push("/dashboard")}
        >
          Ana Sayfa
        </Button>
        <Button
          variant="primary"
          size="md"
          icon={<RotateCcw size={15} />}
          iconPosition="left"
          onClick={reset}
        >
          Yeniden Dene
        </Button>
      </div>
    </div>
  );
}
