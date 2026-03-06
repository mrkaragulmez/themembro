/**
 * frontend/src/app/(shell)/membro/page.tsx
 * Faz 6 — Membro listeleme ekranı
 * Grid görünümü, boş state, yeni membro CTA
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { Plus, Bot } from "lucide-react";
import { useAppStore } from "@/stores/appStore";
import { membroApi } from "@/lib/api";
import { MembroCard } from "@/components/membro/MembroCard";
import { MembroCardSkeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

export default function MembroListPage() {
  const { openCreateMembro } = useAppStore();

  const { data: membros = [], isLoading } = useQuery({
    queryKey: ["membros"],
    queryFn: membroApi.list,
  });

  const visible = membros.filter((m) => m.is_active);

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 animate-fade-in">
      {/* Başlık */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Membro'larım</h1>
          <p className="text-sm text-text-secondary mt-0.5">
            {isLoading ? "Yükleniyor..." : `${visible.length} membro`}
          </p>
        </div>
        <Button
          variant="primary"
          size="md"
          icon={<Plus size={15} />}
          iconPosition="left"
          onClick={openCreateMembro}
        >
          Yeni Membro
        </Button>
      </div>

      {/* Skeleton */}
      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <MembroCardSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Boş state */}
      {!isLoading && visible.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <div className="w-16 h-16 rounded-2xl bg-surface-100 flex items-center justify-center mb-4">
            <Bot size={28} className="text-text-tertiary" />
          </div>
          <h3 className="text-base font-semibold text-text-primary">
            Henüz membro yok
          </h3>
          <p className="text-sm text-text-secondary mt-1 max-w-xs">
            İlk AI asistanını oluşturarak başla.
          </p>
          <Button
            variant="primary"
            size="md"
            className="mt-5"
            icon={<Plus size={15} />}
            iconPosition="left"
            onClick={openCreateMembro}
          >
            İlk Membro'yu Yarat
          </Button>
        </div>
      )}

      {/* Grid */}
      {!isLoading && visible.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {visible.map((m) => (
            <MembroCard key={m.id} membro={m} />
          ))}
        </div>
      )}
    </div>
  );
}
