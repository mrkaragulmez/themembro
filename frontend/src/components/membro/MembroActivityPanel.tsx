/**
 * frontend/src/components/membro/MembroActivityPanel.tsx
 * Faz 6.1 — Membro detay sağ panel: geçmiş toplantılar + bilgi bankası dokümanları
 */

"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Video, BookOpen, Plus, Trash2, ExternalLink } from "lucide-react";
import { clsx } from "clsx";

import { meetingApi, knowledgeApi } from "@/lib/api";
import { useAppStore } from "@/stores/appStore";
import { Skeleton } from "@/components/ui/skeleton";
import type { KnowledgeDoc, Meeting } from "@/types";

type Tab = "meetings" | "knowledge";

// ─── Toplantı satırı ──────────────────────────────────────────────────────────

function MeetingRow({ meeting }: { meeting: Meeting }) {
  const router = useRouter();
  const isActive = meeting.status === "active";

  return (
    <button
      onClick={() =>
        isActive
          ? router.push(`/meeting/${meeting.room_name}?membroId=${meeting.membro_id}`)
          : undefined
      }
      disabled={!isActive}
      className={clsx(
        "flex items-start gap-2.5 w-full text-left p-3 rounded-xl border transition-colors",
        isActive
          ? "border-brand-periwinkle/40 bg-info/5 hover:bg-info/10 cursor-pointer"
          : "border-border-default bg-surface-0 cursor-default"
      )}
    >
      <Video size={13} className={clsx("mt-0.5 shrink-0", isActive ? "text-brand-periwinkle" : "text-text-tertiary")} />
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-text-primary truncate">
          {new Date(meeting.started_at).toLocaleDateString("tr-TR", {
            day: "numeric",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
        <p className={clsx("text-[10px] mt-0.5", isActive ? "text-brand-periwinkle" : "text-text-tertiary")}>
          {isActive ? "• Devam ediyor" : "Tamamlandı"}
        </p>
      </div>
      {isActive && <ExternalLink size={11} className="text-brand-periwinkle mt-0.5 shrink-0" />}
    </button>
  );
}

// ─── Bilgi dokümanı satırı ────────────────────────────────────────────────────

function DocRow({ doc, onDelete }: { doc: KnowledgeDoc; onDelete: () => void }) {
  return (
    <div className="flex items-start gap-2.5 p-3 rounded-xl border border-border-default bg-surface-0 group">
      <BookOpen size={13} className="text-text-tertiary mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-text-primary truncate">{doc.title || "Başlıksız"}</p>
        <p className="text-[10px] text-text-tertiary mt-0.5">
          {new Date(doc.created_at).toLocaleDateString("tr-TR", {
            day: "numeric",
            month: "short",
          })}
        </p>
      </div>
      <button
        onClick={onDelete}
        className="opacity-0 group-hover:opacity-100 p-1 rounded-lg text-text-tertiary hover:text-error transition-all"
        aria-label="Sil"
      >
        <Trash2 size={11} />
      </button>
    </div>
  );
}

// ─── Panel ────────────────────────────────────────────────────────────────────

interface MembroActivityPanelProps {
  membroId: string;
}

export function MembroActivityPanel({ membroId }: MembroActivityPanelProps) {
  const [tab, setTab] = useState<Tab>("meetings");
  const qc = useQueryClient();
  const { openCreateMeeting } = useAppStore();

  const { data: meetings = [], isLoading: meetingsLoading } = useQuery({
    queryKey: ["meetings", membroId],
    queryFn: meetingApi.list,
    select: (all) => all.filter((m) => m.membro_id === membroId),
  });

  const { data: docs = [], isLoading: docsLoading } = useQuery({
    queryKey: ["knowledge", membroId],
    queryFn: () => knowledgeApi.list(membroId),
  });

  const deleteMutation = useMutation({
    mutationFn: knowledgeApi.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["knowledge", membroId] }),
  });

  const tabs: { key: Tab; label: string; count: number }[] = [
    { key: "meetings", label: "Toplantılar", count: meetings.length },
    { key: "knowledge", label: "Bilgi", count: docs.length },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div className="flex border-b border-border-default px-3 shrink-0">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={clsx(
              "flex items-center gap-1.5 px-3 py-3 text-xs font-medium border-b-2 transition-colors",
              tab === t.key
                ? "border-brand-navy text-text-primary"
                : "border-transparent text-text-tertiary hover:text-text-secondary"
            )}
          >
            {t.label}
            <span className={clsx(
              "px-1.5 py-0.5 rounded-full text-[10px]",
              tab === t.key ? "bg-brand-navy/10 text-brand-navy" : "bg-surface-100 text-text-tertiary"
            )}>
              {t.count}
            </span>
          </button>
        ))}
      </div>

      {/* İçerik */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2 scrollbar-thin">
        {tab === "meetings" && (
          <>
            {meetingsLoading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-14 rounded-xl" />
              ))
            ) : meetings.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-xs text-text-tertiary">Henüz toplantı yok.</p>
              </div>
            ) : (
              meetings
                .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())
                .map((m) => <MeetingRow key={m.id} meeting={m} />)
            )}
            <button
              onClick={() => openCreateMeeting(membroId)}
              className="flex items-center gap-2 w-full px-3 py-2 rounded-xl text-xs text-text-tertiary hover:bg-surface-100 hover:text-text-secondary transition-colors"
            >
              <Plus size={12} />
              Yeni toplantı
            </button>
          </>
        )}

        {tab === "knowledge" && (
          <>
            {docsLoading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-14 rounded-xl" />
              ))
            ) : docs.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-xs text-text-tertiary">Bilgi bankası boş.</p>
              </div>
            ) : (
              docs.map((d) => (
                <DocRow key={d.id} doc={d} onDelete={() => deleteMutation.mutate(d.id)} />
              ))
            )}
          </>
        )}
      </div>
    </div>
  );
}
