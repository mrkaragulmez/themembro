/**
 * frontend/src/app/(shell)/settings/page.tsx
 * Faz 6.4 — Ayarlar: Hesap bilgileri + çıkış
 */

"use client";

import { useRouter } from "next/navigation";
import { LogOut, User, Building2, Bell, Shield } from "lucide-react";

import { clearTokens } from "@/lib/api";
import { Button } from "@/components/ui/button";

// ─── Bölüm Başlığı ────────────────────────────────────────────────────────────

function SettingsSection({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="py-6 border-b border-border-default last:border-0">
      <div className="mb-4">
        <h2 className="text-sm font-semibold text-text-primary">{title}</h2>
        {description && (
          <p className="text-xs text-text-tertiary mt-0.5">{description}</p>
        )}
      </div>
      {children}
    </div>
  );
}

// ─── Satır ────────────────────────────────────────────────────────────────────

function SettingsRow({
  icon,
  label,
  value,
  badge,
}: {
  icon: React.ReactNode;
  label: string;
  value?: string;
  badge?: string;
}) {
  return (
    <div className="flex items-center gap-3 py-3">
      <span className="p-2 rounded-xl bg-surface-100 text-text-tertiary shrink-0">
        {icon}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-text-tertiary">{label}</p>
        <p className="text-sm font-medium text-text-primary mt-0.5 truncate">
          {value ?? "—"}
        </p>
      </div>
      {badge && (
        <span className="text-xs px-2 py-0.5 rounded-full bg-surface-100 text-text-secondary shrink-0">
          {badge}
        </span>
      )}
    </div>
  );
}

// ─── Sayfa ────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const router = useRouter();

  const email =
    typeof window !== "undefined"
      ? (localStorage.getItem("user_email") ?? "")
      : "";
  const name = email ? email.split("@")[0] : "Kullanıcı";

  function handleLogout() {
    clearTokens();
    router.push("/login");
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-8 animate-fade-in">
      <h1 className="text-2xl font-bold text-text-primary mb-1">Ayarlar</h1>
      <p className="text-sm text-text-secondary mb-8">
        Hesap ve tenant yapılandırması
      </p>

      <div className="bg-surface-0 border border-border-default rounded-2xl px-6 divide-y divide-border-default">
        {/* Hesap */}
        <SettingsSection
          title="Hesap"
          description="Giriş yaptığın kullanıcıya ait bilgiler"
        >
          <SettingsRow
            icon={<User size={15} />}
            label="Kullanıcı Adı"
            value={name}
          />
          <SettingsRow
            icon={<User size={15} />}
            label="E-posta"
            value={email || "—"}
          />
        </SettingsSection>

        {/* Tenant */}
        <SettingsSection
          title="Tenant"
          description="Bu oturumdaki organizasyon bilgileri"
        >
          <SettingsRow
            icon={<Building2 size={15} />}
            label="Tenant"
            value="themembro.com"
            badge="Aktif"
          />
        </SettingsSection>

        {/* Bildirimler (yakında) */}
        <SettingsSection
          title="Bildirimler"
          description="Yakında — toplantı ve membro etkinlik bildirimleri"
        >
          <SettingsRow
            icon={<Bell size={15} />}
            label="E-posta bildirimleri"
            value="Yakında aktifleştirilecek"
          />
        </SettingsSection>

        {/* Güvenlik */}
        <SettingsSection
          title="Güvenlik"
          description="Oturum ve erişim yönetimi"
        >
          <SettingsRow
            icon={<Shield size={15} />}
            label="Kimlik doğrulama"
            value="JWT (Bearer Token)"
            badge="Aktif"
          />
          <div className="pt-2">
            <Button
              variant="outline"
              size="sm"
              icon={<LogOut size={14} />}
              iconPosition="left"
              onClick={handleLogout}
              className="text-error border-error/30 hover:bg-error/5"
            >
              Çıkış Yap
            </Button>
          </div>
        </SettingsSection>
      </div>
    </div>
  );
}

