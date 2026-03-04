/**
 * frontend/src/app/(shell)/meetings/page.tsx
 * Faz 6.4 — Toplantılar geçmişi
 * Tüm toplantıları listeler; aktif olanlar için "Katıl" aksiyonu sunar.
 */

"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Video, Calendar, Clock, ChevronRight } from "lucide-react";
import { clsx } from "clsx";

import { meetingApi, membroApi } from "@/lib/api";
import { useAppStore } from "@/stores/appStore";
import { Avatar } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import type { Meeting, Membro } from "@/types";

// ─── Yardımcılar ──────────────────────────────────────────────────────────────

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(startIso: string, endIso: string | null) {
  if (!endIso) return "Devam ediyor";
  const diffMs = new Date(endIso).getTime() - new Date(startIso).getTime();
  const totalSeconds = Math.round(diffMs / 1000);
  if (totalSeconds < 60) return `${totalSeconds}sn`;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes < 60) return `${minutes}dk ${seconds > 0 ? `${seconds}sn` : ""}`.trim();
  const hours = Math.floor(minutes / 60);
  const remainMin = minutes % 60;
  return `${hours}sa ${remainMin > 0 ? `${remainMin}dk` : ""}`.trim();
}

// ─── Toplantı Kartı ───────────────────────────────────────────────────────────

function MeetingCard({
  meeting,
  membro,
  onJoin,
  onEnd,
  isEnding,
}: {
  meeting: Meeting;
  membro: Membro | undefined;
  onJoin: () => void;
  onEnd: () => void;
  isEnding: boolean;
}) {
  const isActive = meeting.status === "active";

  return (
    <div
      className={clsx(
        "flex items-center gap-4 p-4 rounded-2xl border bg-surface-0 transition-colors",
        isActive
          ? "border-brand-periwinkle/40 bg-info/3"
          : "border-border-default hover:border-border-active"
      )}
    >
      {/* Avatar */}
      <div className="shrink-0">
        {membro ? (
          <Avatar name={membro.name} color={membro.color} size="md" />
        ) : (
          <div className="w-10 h-10 rounded-full bg-surface-100 flex items-center justify-center">
            <Video size={16} className="text-text-tertiary" />
          </div>
        )}
      </div>

      {/* Bilgiler */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-semibold text-text-primary truncate">
            {membro?.name ?? "Membro"} ile Toplantı
          </p>
          {isActive && (
            <span className="shrink-0 flex items-center gap-1 px-2 py-0.5 rounded-full bg-success/15 text-success text-xs font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
              Canlı
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 mt-1 text-xs text-text-tertiary">
          <span className="flex items-center gap-1">
            <Calendar size={11} />
            {formatDate(meeting.started_at)}
          </span>
          <span className="flex items-center gap-1">
            <Clock size={11} />
            {formatDuration(meeting.started_at, meeting.ended_at)}
          </span>
        </div>
      </div>

      {/* Aksiyon */}
      <div className="shrink-0 flex items-center gap-2">
        {isActive ? (
          <>
            <Button
              variant="primary"
              size="sm"
              icon={<ChevronRight size={14} />}
              onClick={onJoin}
            >
              Katıl
            </Button>
            <Button
              variant="outline"
              size="sm"
              loading={isEnding}
              onClick={onEnd}
            >
              Bitir
            </Button>
          </>
        ) : (
          <span className="text-xs text-text-tertiary px-2 py-1 rounded-lg bg-surface-100">
            Tamamlandı
          </span>
        )}
      </div>
    </div>
  );
}

// ─── Sayfa ────────────────────────────────────────────────────────────────────

export default function MeetingsPage() {
  const router = useRouter();
  const { openCreateMeeting } = useAppStore();
  const toast = useToast();
  const qc = useQueryClient();

  const { data: meetings = [], isLoading: meetingsLoading } = useQuery({
    queryKey: ["meetings"],
    queryFn: meetingApi.list,
    refetchInterval: 30_000, // Aktif toplantı varsa canlı kalınsın
  });

  const { data: membros = [] } = useQuery({
    queryKey: ["membros"],
    queryFn: membroApi.list,
  });

  const endMutation = useMutation({
    mutationFn: (id: string) => meetingApi.end(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["meetings"] });
      toast.success("Toplantı bitirildi.");
    },
    onError: () => toast.error("Toplantı bitirilemedi."),
  });

  const [endingId, setEndingId] = useState<string | null>(null);

  function handleEnd(meeting: Meeting) {
    setEndingId(meeting.id);
    endMutation.mutate(meeting.id, { onSettled: () => setEndingId(null) });
  }

  const membroMap = new Map(membros.map((m) => [m.id, m]));

  // Aktif üstte, sonra başlangıç tarihine göre tersine sırala
  const sorted = [...meetings].sort((a, b) => {
    if (a.status === "active" && b.status !== "active") return -1;
    if (b.status === "active" && a.status !== "active") return 1;
    return new Date(b.started_at).getTime() - new Date(a.started_at).getTime();
  });

  return (
    <div className="max-w-3xl mx-auto px-6 py-8 animate-fade-in">
      {/* Başlık */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Toplantılar</h1>
          <p className="text-sm text-text-secondary mt-0.5">
            {meetingsLoading
              ? "Yükleniyor..."
              : `${meetings.length} toplantı · ${meetings.filter((m) => m.status === "active").length} aktif`}
          </p>
        </div>
        <Button
          variant="primary"
          size="md"
          icon={<Video size={15} />}
          iconPosition="left"
          onClick={() => openCreateMeeting()}
        >
          Toplantı Başlat
        </Button>
      </div>

      {/* Liste */}
      {meetingsLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-2xl" />
          ))}
        </div>
      ) : sorted.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <div className="w-14 h-14 rounded-2xl bg-surface-100 flex items-center justify-center mb-4">
            <Video size={24} className="text-text-tertiary" />
          </div>
          <h3 className="text-base font-semibold text-text-primary">Henüz toplantı yok</h3>
          <p className="text-sm text-text-secondary mt-1 max-w-xs">
            Bir membro ile sesli toplantı başlatmak için yukarıdaki butonu kullan.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {sorted.map((meeting) => (
            <MeetingCard
              key={meeting.id}
              meeting={meeting}
              membro={membroMap.get(meeting.membro_id)}
              onJoin={() =>
                router.push(`/meeting/${meeting.room_name}?membroId=${meeting.membro_id}`)
              }
              onEnd={() => handleEnd(meeting)}
              isEnding={endingId === meeting.id}
            />
          ))}
        </div>
      )}
    </div>
  );
}


