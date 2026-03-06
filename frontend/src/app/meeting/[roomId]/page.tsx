/**
 * frontend/src/app/meeting/[roomId]/page.tsx
 * Faz 6 — Toplantı (sesli) ekranı
 * Shell layout'tan kopuk; topbar/sidebar yok.
 */

"use client";

import { use, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import dynamic from "next/dynamic";
import { useToast } from "@/components/ui/toast";
import { Toaster } from "@/components/ui/toast";

const VoiceRoom = dynamic(
  () => import("@/components/VoiceRoom"),
  { ssr: false }
);

type Params = Promise<{ roomId: string }>;

export default function MeetingPage({ params }: { params: Params }) {
  const { roomId } = use(params);
  const router = useRouter();
  const searchParams = useSearchParams();
  const membroId = searchParams.get("membroId") ?? "";
  const toast = useToast();

  const handleLeave = useCallback(() => {
    toast.success("Toplantı başarıyla bitirildi.");
    setTimeout(() => router.back(), 1500);
  }, [toast, router]);

  return (
    <div className="fixed inset-0 bg-brand-navy flex flex-col">
      {/* Minimal üst bar */}
      <div className="flex items-center gap-3 px-5 py-3 border-b border-white/10">
        <button
          onClick={() => router.back()}
          className="p-1.5 rounded-lg text-white/60 hover:text-white hover:bg-white/10 transition-colors"
          aria-label="Geri"
        >
          <ArrowLeft size={16} />
        </button>
        <span className="text-sm font-medium text-white/80">Toplantı</span>
        <code className="ml-1 text-xs text-white/40 font-mono">{roomId}</code>
      </div>

      {/* VoiceRoom */}
      <div className="flex-1 overflow-hidden">
        {membroId ? (
          <VoiceRoom
            membroId={membroId}
            onLeave={handleLeave}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-white/50 text-sm">
            Membro bilgisi bulunamadı.
          </div>
        )}
      </div>
      <Toaster />
    </div>
  );
}
