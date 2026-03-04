/**
 * frontend/src/stores/appStore.ts
 * Faz 6 — Zustand UI State Store
 * Sidebar collapse, modal açma/kapama ve aktif membro takibi
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Membro } from "@/types";

interface AppStore {
  // Sidebar
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (v: boolean) => void;

  // Active membro (detay sayfasında geçerli)
  activeMembro: Membro | null;
  setActiveMembro: (m: Membro | null) => void;

  // Modals
  createMembroModalOpen: boolean;
  createMeetingModalOpen: boolean;
  createMeetingPrefilledMembroId: string | undefined;

  openCreateMembro: () => void;
  openCreateMeeting: (prefilledMembroId?: string) => void;
  closeModals: () => void;
}

export const useAppStore = create<AppStore>()(
  persist(
    (set) => ({
      // Sidebar — masaüstü varsayılan açık
      sidebarCollapsed: false,
      toggleSidebar: () =>
        set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),

      // Active membro
      activeMembro: null,
      setActiveMembro: (m) => set({ activeMembro: m }),

      // Modals
      createMembroModalOpen: false,
      createMeetingModalOpen: false,
      createMeetingPrefilledMembroId: undefined,

      openCreateMembro: () =>
        set({
          createMembroModalOpen: true,
          createMeetingModalOpen: false,
        }),

      openCreateMeeting: (prefilledMembroId) =>
        set({
          createMeetingModalOpen: true,
          createMembroModalOpen: false,
          createMeetingPrefilledMembroId: prefilledMembroId,
        }),

      closeModals: () =>
        set({
          createMembroModalOpen: false,
          createMeetingModalOpen: false,
          createMeetingPrefilledMembroId: undefined,
        }),
    }),
    {
      name: "membro-app-store",
      // Sadece sidebar state'i persist et; modal state uçucu
      partialize: (s) => ({ sidebarCollapsed: s.sidebarCollapsed }),
    }
  )
);
