/**
 * frontend/src/components/layout/TopBar.tsx
 * Faz 6 — Uygulama üst çubuğu
 * Logo, tenant adı, bildirimler, kullanıcı avatar menüsü
 */

"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bell, LogOut, Settings, ChevronDown } from "lucide-react";
import { clsx } from "clsx";

import { clearTokens } from "@/lib/api";
import { Avatar } from "@/components/ui/avatar";

// Kullanıcı bilgisini localStorage'dan okur (login sırasında setTokens ile yazılır)
function useUserInfo() {
  if (typeof window === "undefined") return { name: "Kullanıcı", email: "" };
  const email = localStorage.getItem("user_email") ?? "";
  const name = email ? email.split("@")[0] : "Kullanıcı";
  return { name, email };
}

export function TopBar() {
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const user = useUserInfo();

  function handleLogout() {
    clearTokens();
    router.push("/login");
  }

  return (
    <header className="h-14 flex items-center justify-between px-5 border-b border-border-default bg-surface-0 shrink-0">
      {/* Sol: boşluk (sidebar logosu ayrı) */}
      <div />

      {/* Sağ: aksiyonlar */}
      <div className="flex items-center gap-2">
        {/* Bildirimler (ilerleyen fazlarda aktif) */}
        <button
          className="p-2 rounded-xl text-text-tertiary hover:text-text-primary hover:bg-surface-50 transition-colors"
          aria-label="Bildirimler"
          disabled
        >
          <Bell size={18} />
        </button>

        {/* Kullanıcı menüsü */}
        <div className="relative">
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className={clsx(
              "flex items-center gap-2 pl-1 pr-2 py-1 rounded-xl",
              "hover:bg-surface-50 transition-colors",
              menuOpen && "bg-surface-50"
            )}
            aria-expanded={menuOpen}
            aria-haspopup="true"
          >
            <Avatar name={user.name} color="#655F9C" size="sm" />
            <span className="text-sm font-medium text-text-primary max-w-[120px] truncate hidden sm:block">
              {user.name}
            </span>
            <ChevronDown
              size={14}
              className={clsx(
                "text-text-tertiary transition-transform duration-150",
                menuOpen && "rotate-180"
              )}
            />
          </button>

          {/* Dropdown menü */}
          {menuOpen && (
            <>
              {/* Backdrop */}
              <div
                className="fixed inset-0 z-10"
                onClick={() => setMenuOpen(false)}
                aria-hidden="true"
              />
              <div className="absolute right-0 top-[calc(100%+6px)] z-20 w-52 bg-surface-0 border border-border-default rounded-xl shadow-[0_4px_16px_rgba(24,9,66,0.12)] overflow-hidden animate-slide-up">
                {/* Kullanıcı bilgisi */}
                <div className="px-4 py-3 border-b border-border-default">
                  <p className="text-sm font-semibold text-text-primary truncate">{user.name}</p>
                  {user.email && (
                    <p className="text-xs text-text-tertiary truncate mt-0.5">{user.email}</p>
                  )}
                </div>

                <div className="p-1">
                  <Link
                    href="/settings"
                    onClick={() => setMenuOpen(false)}
                    className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-text-secondary hover:bg-surface-50 hover:text-text-primary transition-colors"
                  >
                    <Settings size={15} />
                    Ayarlar
                  </Link>

                  <div className="border-t border-border-default my-1" />

                  <button
                    onClick={handleLogout}
                    className="flex items-center gap-2.5 w-full px-3 py-2 rounded-lg text-sm text-error hover:bg-error/8 transition-colors"
                  >
                    <LogOut size={15} />
                    Çıkış Yap
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
