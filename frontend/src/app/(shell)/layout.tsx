/**
 * frontend/src/app/(shell)/layout.tsx
 * Faz 6 — Shell layout: Sidebar + TopBar
 * Tüm (shell) sayfaları bu layout'u kullanır.
 * Mobil: hamburger ile overlay sidebar; masaüstü: sabit sidebar.
 */

import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { MobileSidebarBackdrop } from "@/components/layout/MobileSidebarBackdrop";
import { CreateMembroModal } from "@/components/modals/CreateMembroModal";
import { CreateMeetingModal } from "@/components/modals/CreateMeetingModal";
import { Toaster } from "@/components/ui/toast";

export default function ShellLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-surface-50">
      {/* Mobil backdrop */}
      <MobileSidebarBackdrop />
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
      <CreateMembroModal />
      <CreateMeetingModal />
      <Toaster />
    </div>
  );
}
