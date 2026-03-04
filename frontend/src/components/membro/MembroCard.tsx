/**
 * frontend/src/components/membro/MembroCard.tsx
 * Faz 6 — Membro grid kartı
 */

"use client";

import { useRouter } from "next/navigation";
import { MessageSquare, Video, Clock } from "lucide-react";
import { clsx } from "clsx";
import { Avatar } from "@/components/ui/avatar";
import { MembroStatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/stores/appStore";
import type { Membro } from "@/types";

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "—";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 60) return `${mins}d önce`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}s önce`;
  return `${Math.floor(hrs / 24)}g önce`;
}

interface MembroCardProps {
  membro: Membro;
}

export function MembroCard({ membro }: MembroCardProps) {
  const router = useRouter();
  const { openCreateMeeting } = useAppStore();

  return (
    <div
      className={clsx(
        "group bg-surface-0 border border-border-default rounded-2xl p-5",
        "hover:border-brand-periwinkle/40 hover:shadow-md",
        "transition-all duration-200 cursor-pointer"
      )}
      onClick={() => router.push(`/membro/${membro.id}`)}
    >
      {/* Üst: Avatar + İsim + Status */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <Avatar name={membro.name} color={membro.color} size="md" />
          <div>
            <h3 className="text-sm font-semibold text-text-primary leading-tight">
              {membro.name}
            </h3>
            <p className="text-xs text-text-tertiary mt-0.5 line-clamp-1">{membro.persona}</p>
          </div>
        </div>
        <MembroStatusBadge status={membro.status} />
      </div>

      {/* Orta: Prompt önizleme */}
      {membro.system_prompt && (
        <p className="mt-3 text-xs text-text-secondary line-clamp-2 leading-relaxed">
          {membro.system_prompt}
        </p>
      )}

      {/* Alt: Son aktivite + Actions */}
      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs text-text-tertiary">
          <Clock size={11} />
          <span>{timeAgo(membro.last_interaction_at)}</span>
        </div>

        {/* Hover'da gözüken aksiyonlar */}
        <div
          className="flex gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={(e) => e.stopPropagation()}
        >
          <Button
            variant="ghost"
            size="sm"
            icon={<MessageSquare size={13} />}
            onClick={() => router.push(`/membro/${membro.id}`)}
            aria-label="Sohbet"
          />
          <Button
            variant="ghost"
            size="sm"
            icon={<Video size={13} />}
            onClick={() => openCreateMeeting(membro.id)}
            aria-label="Toplantı"
          />
        </div>
      </div>
    </div>
  );
}
