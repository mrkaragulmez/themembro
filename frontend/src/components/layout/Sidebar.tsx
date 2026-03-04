/**
 * frontend/src/components/layout/Sidebar.tsx
 * Faz 6 — Uygulama Sidebar'ı
 * Navigasyon, membro listesi (frekansa göre), collapse/expand
 */

"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { clsx } from "clsx";
import {
  LayoutDashboard,
  Bot,
  BookOpen,
  Video,
  Settings,
  ChevronLeft,
  ChevronRight,
  Plus,
} from "lucide-react";

import { useAppStore } from "@/stores/appStore";
import { membroApi } from "@/lib/api";
import { Avatar } from "@/components/ui/avatar";
import { SidebarMembroSkeleton } from "@/components/ui/skeleton";
import type { Membro } from "@/types";

// ─── Nav items ───────────────────────────────────────────────────────────────

const NAV_ITEMS = [
  { href: "/dashboard",  label: "Dashboard", icon: LayoutDashboard },
  { href: "/membro",     label: "Membro'lar", icon: Bot },
  { href: "/knowledge",  label: "Bilgi Bankası", icon: BookOpen },
  { href: "/meetings",   label: "Toplantılar",  icon: Video },
] as const;

// ─── Nav Item Bileşeni ────────────────────────────────────────────────────────

function NavItem({
  href,
  label,
  icon: Icon,
  collapsed,
  active,
}: {
  href: string;
  label: string;
  icon: React.ElementType;
  collapsed: boolean;
  active: boolean;
}) {
  return (
    <Link
      href={href}
      title={collapsed ? label : undefined}
      className={clsx(
        "flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-all duration-100",
        active
          ? "bg-surface-100 text-text-primary"
          : "text-text-secondary hover:bg-surface-50 hover:text-text-primary",
        collapsed && "justify-center px-2"
      )}
    >
      <Icon size={18} className="shrink-0" aria-hidden="true" />
      {!collapsed && <span className="truncate">{label}</span>}
    </Link>
  );
}

// ─── Membro Item Bileşeni ─────────────────────────────────────────────────────

function MembroItem({
  membro,
  active,
  collapsed,
}: {
  membro: Membro;
  active: boolean;
  collapsed: boolean;
}) {
  return (
    <Link
      href={`/membro/${membro.id}`}
      title={collapsed ? membro.name : undefined}
      className={clsx(
        "flex items-center gap-2.5 rounded-xl px-3 py-1.5 text-sm transition-all duration-100",
        "relative group",
        active
          ? "bg-surface-100 text-text-primary font-medium"
          : "text-text-secondary hover:bg-surface-50 hover:text-text-primary",
        collapsed && "justify-center px-2"
      )}
    >
      {/* Aktif sol çizgi */}
      {active && (
        <span
          className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-full bg-brand-periwinkle"
          aria-hidden="true"
        />
      )}
      <Avatar name={membro.name} color={membro.color} size="xs" />
      {!collapsed && (
        <span className="truncate flex-1 text-sm">{membro.name}</span>
      )}
    </Link>
  );
}

// ─── Ana Sidebar ──────────────────────────────────────────────────────────────

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebar, openCreateMembro } = useAppStore();

  const { data: membros, isLoading } = useQuery({
    queryKey: ["membros"],
    queryFn: membroApi.list,
    staleTime: 60_000,
  });

  // Frekansa göre sıralama: last_interaction_at'e göre (en son en üstte)
  const sortedMembros = membros
    ? [...membros]
        .filter((m) => m.status !== "archived")
        .sort((a, b) => {
          if (!a.last_interaction_at && !b.last_interaction_at) return 0;
          if (!a.last_interaction_at) return 1;
          if (!b.last_interaction_at) return -1;
          return (
            new Date(b.last_interaction_at).getTime() -
            new Date(a.last_interaction_at).getTime()
          );
        })
        .slice(0, 7)
    : [];

  const currentMembroId = pathname.startsWith("/membro/")
    ? pathname.split("/")[2]
    : null;

  return (
    <aside
      className={clsx(
        "flex flex-col h-full bg-surface-0 border-r border-border-default",
        "transition-all duration-200 ease-in-out",
        sidebarCollapsed ? "w-[60px]" : "w-[240px]"
      )}
    >
      {/* Logo */}
      <div
        className={clsx(
          "flex items-center h-14 px-4 border-b border-border-default shrink-0",
          sidebarCollapsed ? "justify-center" : "gap-2"
        )}
      >
        {/* Logo mark */}
        <span
          className="w-7 h-7 rounded-lg bg-brand-navy flex items-center justify-center shrink-0 text-surface-0 text-xs font-black"
          aria-hidden="true"
        >
          M
        </span>
        {!sidebarCollapsed && (
          <span className="font-bold text-base text-text-primary tracking-tight">
            Membro
          </span>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-0.5 scrollbar-thin">
        {/* Ana navigasyon */}
        {NAV_ITEMS.map((item) => (
          <NavItem
            key={item.href}
            href={item.href}
            label={item.label}
            icon={item.icon}
            collapsed={sidebarCollapsed}
            active={pathname === item.href || pathname.startsWith(item.href + "/")}
          />
        ))}

        {/* Membro Listesi */}
        {!sidebarCollapsed && (
          <div className="pt-4">
            <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-widest text-text-tertiary">
              Membro'larım
            </p>
            {isLoading ? (
              <SidebarMembroSkeleton />
            ) : sortedMembros.length > 0 ? (
              <div className="space-y-0.5">
                {sortedMembros.map((m) => (
                  <MembroItem
                    key={m.id}
                    membro={m}
                    active={currentMembroId === m.id}
                    collapsed={false}
                  />
                ))}
              </div>
            ) : null}

            {/* Yeni Membro Ekle */}
            <button
              onClick={openCreateMembro}
              className={clsx(
                "flex items-center gap-2.5 w-full rounded-xl px-3 py-1.5 mt-1",
                "text-sm text-text-tertiary hover:text-brand-periwinkle hover:bg-surface-50",
                "transition-colors duration-100"
              )}
            >
              <Plus size={14} className="shrink-0" />
              <span>Membro Ekle</span>
            </button>
          </div>
        )}

        {/* Collapsed membro listesi — sadece avatarlar */}
        {sidebarCollapsed && sortedMembros.length > 0 && (
          <div className="pt-3 flex flex-col items-center gap-1">
            {sortedMembros.map((m) => (
              <MembroItem
                key={m.id}
                membro={m}
                active={currentMembroId === m.id}
                collapsed
              />
            ))}
            <button
              onClick={openCreateMembro}
              className="p-1.5 rounded-xl text-text-tertiary hover:text-brand-periwinkle hover:bg-surface-50 transition-colors"
              title="Membro Ekle"
              aria-label="Membro Ekle"
            >
              <Plus size={14} />
            </button>
          </div>
        )}
      </nav>

      {/* Alt kısım */}
      <div className="shrink-0 border-t border-border-default p-2 space-y-0.5">
        <NavItem
          href="/settings"
          label="Ayarlar"
          icon={Settings}
          collapsed={sidebarCollapsed}
          active={pathname.startsWith("/settings")}
        />

        {/* Collapse toggle */}
        <button
          onClick={toggleSidebar}
          className={clsx(
            "flex items-center gap-3 w-full rounded-xl px-3 py-2 text-sm",
            "text-text-tertiary hover:bg-surface-50 hover:text-text-primary",
            "transition-colors duration-100",
            sidebarCollapsed && "justify-center px-2"
          )}
          aria-label={sidebarCollapsed ? "Sidebar'ı genişlet" : "Sidebar'ı daralt"}
        >
          {sidebarCollapsed ? (
            <ChevronRight size={16} />
          ) : (
            <>
              <ChevronLeft size={16} />
              <span>Daralt</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
