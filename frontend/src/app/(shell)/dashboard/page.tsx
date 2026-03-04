/**
 * frontend/src/app/(shell)/dashboard/page.tsx
 * Faz 6 — Dashboard ekranı
 * Hızlı aksiyonlar, membro spotlight, aktivite akışı
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Plus, Video, BookOpen, ArrowRight, Zap } from "lucide-react";
import { clsx } from "clsx";

import { useAppStore } from "@/stores/appStore";
import { membroApi, meetingApi, knowledgeApi } from "@/lib/api";
import { Avatar } from "@/components/ui/avatar";
import { MembroStatusBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { Membro, Meeting } from "@/types";

// ─── Hızlı Aksiyon kartı ──────────────────────────────────────────────────────

function QuickActionCard({
  icon,
  label,
  description,
  accent,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  description: string;
  accent: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "text-left flex items-start gap-4 p-5 rounded-2xl border border-border-default",
        "bg-surface-0 hover:shadow-md hover:border-border-active",
        "transition-all duration-200 group w-full"
      )}
    >
      <span
        className={clsx(
          "p-2.5 rounded-xl shrink-0 transition-colors",
          accent
        )}
      >
        {icon}
      </span>
      <div className="min-w-0">
        <p className="text-sm font-semibold text-text-primary">{label}</p>
        <p className="text-xs text-text-secondary mt-0.5">{description}</p>
      </div>
      <ArrowRight
        size={14}
        className="ml-auto mt-1 text-text-tertiary opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
      />
    </button>
  );
}

// ─── Spotlight: Aktif Membro listesi ─────────────────────────────────────────

function MembroSpotlight({ membros }: { membros: Membro[] }) {
  const router = useRouter();
  const { openCreateMeeting } = useAppStore();

  const active = membros
    .filter((m) => m.status !== "archived")
    .sort(
      (a, b) =>
        new Date(b.last_interaction_at ?? 0).getTime() -
        new Date(a.last_interaction_at ?? 0).getTime()
    )
    .slice(0, 5);

  if (active.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center">
        <p className="text-sm text-text-secondary">Henüz membro oluşturmadın.</p>
        <p className="text-xs text-text-tertiary mt-1">
          Hızlı aksiyonlardan ilk membro'nu yarat.
        </p>
      </div>
    );
  }

  return (
    <ul className="divide-y divide-border-default">
      {active.map((m) => (
        <li key={m.id} className="flex items-center gap-3 py-3.5 group">
          <Avatar name={m.name} color={m.color} size="sm" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-text-primary truncate">{m.name}</p>
            <p className="text-xs text-text-tertiary truncate">{m.persona}</p>
          </div>
          <MembroStatusBadge status={m.status} />
          <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={() => router.push(`/membro/${m.id}`)}
              className="p-1.5 rounded-lg hover:bg-surface-100 text-text-tertiary hover:text-text-primary transition-colors"
              aria-label="Sohbet"
            >
              <Zap size={13} />
            </button>
            <button
              onClick={() => openCreateMeeting(m.id)}
              className="p-1.5 rounded-lg hover:bg-surface-100 text-text-tertiary hover:text-text-primary transition-colors"
              aria-label="Toplantı"
            >
              <Video size={13} />
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}

// ─── Dashboard Sayfası ────────────────────────────────────────────────────────

export default function DashboardPage() {
  const router = useRouter();
  const { openCreateMembro, openCreateMeeting } = useAppStore();

  const greeting =
    typeof window !== "undefined"
      ? (() => {
          const email = localStorage.getItem("user_email") ?? "";
          return email ? email.split("@")[0] : null;
        })()
      : null;

  const { data: membros = [], isLoading } = useQuery({
    queryKey: ["membros"],
    queryFn: membroApi.list,
    refetchInterval: 30_000,
  });

  const { data: meetings = [], isLoading: meetingsLoading } = useQuery({
    queryKey: ["meetings"],
    queryFn: meetingApi.list,
    refetchInterval: 30_000,
  });

  const { data: docs = [] } = useQuery({
    queryKey: ["knowledge"],
    queryFn: () => knowledgeApi.list(),
  });

  const activeMembros = membros.filter((m) => m.status === "active").length;
  const activeMeetings = meetings.filter((m) => m.status === "active").length;

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 animate-fade-in">
      {/* Başlık */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-text-primary">
          {greeting ? `İyi günler, ${greeting}!` : "İyi günler!"}
        </h1>
        <p className="text-sm text-text-secondary mt-1">
          Bugün ne yapmak istiyorsun?
        </p>
      </div>

      {/* Hızlı Aksiyonlar */}
      <section className="mb-8">
        {/* İstatistik şeridi */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          {[
            { label: "Aktif Membro", value: isLoading ? "—" : String(activeMembros) },
            { label: "Toplam Toplantı", value: meetingsLoading ? "—" : String(meetings.length) },
            { label: "Bilgi Dosyası", value: String(docs.length) },
          ].map(({ label, value }) => (
            <div
              key={label}
              className="rounded-xl bg-surface-50 border border-border-default px-4 py-3"
            >
              <p className="text-2xl font-bold text-text-primary">{value}</p>
              <p className="text-xs text-text-tertiary mt-0.5">{label}</p>
            </div>
          ))}
        </div>
        <h2 className="text-xs font-semibold uppercase tracking-widest text-text-tertiary mb-3">
          Hızlı Aksiyonlar
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <QuickActionCard
            icon={<Plus size={18} />}
            label="Membro Yarat"
            description="Yeni bir AI asistanı oluştur"
            accent="bg-brand-coral/10 text-brand-coral"
            onClick={openCreateMembro}
          />
          <QuickActionCard
            icon={<Video size={18} />}
            label="Toplantı Başlat"
            description="Membro ile sesli toplantı aç"
            accent="bg-brand-periwinkle/10 text-brand-periwinkle"
            onClick={() => openCreateMeeting()}
          />
          <QuickActionCard
            icon={<BookOpen size={18} />}
            label="Bilgi Bankası"
            description="Doküman ekle ve yönet"
            accent="bg-brand-lime/30 text-brand-navy"
            onClick={() => router.push("/knowledge")}
          />
        </div>
      </section>

      {/* Membro Spotlight */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="bg-surface-0 border border-border-default rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text-primary">Membro'larım</h2>
            <button
              onClick={() => router.push("/membro")}
              className="text-xs text-brand-periwinkle hover:underline"
            >
              Tümü →
            </button>
          </div>

          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-3 py-2">
                  <Skeleton className="w-8 h-8 rounded-full" />
                  <div className="flex-1 space-y-1.5">
                    <Skeleton className="h-3 w-32" />
                    <Skeleton className="h-2.5 w-20" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <MembroSpotlight membros={membros} />
          )}
        </section>

        {/* Aktivite akışı — gerçek toplantı geçmişi */}
        <section className="bg-surface-0 border border-border-default rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text-primary">Son Toplantılar</h2>
            <button
              onClick={() => router.push("/meetings")}
              className="text-xs text-brand-periwinkle hover:underline"
            >
              Tümü →
            </button>
          </div>

          {meetingsLoading ? (
            <div className="space-y-3">
              {[1, 2].map((i) => (
                <div key={i} className="flex items-center gap-3 py-2">
                  <Skeleton className="w-8 h-8 rounded-full" />
                  <div className="flex-1 space-y-1.5">
                    <Skeleton className="h-3 w-40" />
                    <Skeleton className="h-2.5 w-24" />
                  </div>
                </div>
              ))}
            </div>
          ) : meetings.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 text-center">
              <span className="text-3xl mb-3">💻</span>
              <p className="text-sm text-text-secondary">Henüz toplantı yok.</p>
              <button
                onClick={() => openCreateMeeting()}
                className="text-xs text-brand-periwinkle hover:underline mt-1"
              >
                İlk toplantıyı başlat →
              </button>
            </div>
          ) : (
            <ul className="divide-y divide-border-default">
              {meetings
                .slice()
                .sort((a: Meeting, b: Meeting) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())
                .slice(0, 4)
                .map((m: Meeting) => {
                  const isActive = m.status === "active";
                  return (
                    <li key={m.id} className="flex items-center gap-3 py-3 group">
                      <span
                        className={clsx(
                          "w-2 h-2 rounded-full shrink-0",
                          isActive ? "bg-success animate-pulse" : "bg-surface-200"
                        )}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-text-primary">Toplantı</p>
                        <p className="text-xs text-text-tertiary">
                          {new Date(m.started_at).toLocaleDateString("tr-TR", {
                            day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
                          })}
                        </p>
                      </div>
                      {isActive && (
                        <button
                          onClick={() => router.push(`/meeting/${m.room_name}?membroId=${m.membro_id}`)}
                          className="text-xs text-brand-periwinkle hover:underline opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          Katıl →
                        </button>
                      )}
                    </li>
                  );
                })}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
