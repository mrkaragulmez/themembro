/**
 * frontend/src/components/modals/CreateMeetingModal.tsx
 * Faz 6 — Toplantı oluşturma modalı
 * Membro seç → başlık gir → POST /api/v1/meetings/ → /meeting/[roomId]
 */

"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Video } from "lucide-react";

import { useAppStore } from "@/stores/appStore";
import { membroApi, meetingApi } from "@/lib/api";
import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar } from "@/components/ui/avatar";
import { useToast } from "@/components/ui/toast";
import { clsx } from "clsx";

export function CreateMeetingModal() {
  const router = useRouter();
  const { createMeetingModalOpen, createMeetingPrefilledMembroId, closeModals } = useAppStore();

  const [title, setTitle] = useState("");
  const [selectedMembroId, setSelectedMembroId] = useState<string>("");
  const toast = useToast();

  // Modal açıldığında pre-fill'i uygula
  useEffect(() => {
    if (createMeetingModalOpen && createMeetingPrefilledMembroId) {
      setSelectedMembroId(createMeetingPrefilledMembroId);
    }
  }, [createMeetingModalOpen, createMeetingPrefilledMembroId]);

  const { data: membros = [], isLoading } = useQuery({
    queryKey: ["membros"],
    queryFn: membroApi.list,
    enabled: createMeetingModalOpen,
  });

  const mutation = useMutation({
    mutationFn: () =>
      meetingApi.create(selectedMembroId, title.trim() || undefined),
    onSuccess: (meeting) => {
      closeModals();
      router.push(`/meeting/${meeting.room_name}?membroId=${selectedMembroId}`);
    },
    onError: () => {
      toast.error("Toplantı başlatılamadı. Tekrar dene.");
    },
  });

  function handleClose() {
    closeModals();
    setTitle("");
    setSelectedMembroId("");
  }

  const activeMembros = membros.filter((m) => m.is_active);

  return (
    <Modal open={createMeetingModalOpen} onClose={handleClose} size="sm" closeOnBackdrop>
      <div className="px-6 py-5 border-b border-border-default">
        <div className="flex items-center gap-3">
          <span className="p-2 rounded-xl bg-brand-navy/5 text-brand-navy">
            <Video size={18} />
          </span>
          <h2 className="text-base font-semibold text-text-primary">Toplantı Başlat</h2>
        </div>
      </div>

      <div className="px-6 py-5 space-y-4">
        {/* Membro Seç */}
        <div>
          <p className="text-sm font-medium text-text-primary mb-2">Membro Seç</p>
          {isLoading ? (
            <div className="space-y-2">
              {[1, 2].map((i) => (
                <div key={i} className="h-10 rounded-xl bg-surface-100 animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="space-y-1 max-h-48 overflow-y-auto scrollbar-thin">
              {activeMembros.length === 0 ? (
                <p className="text-sm text-text-tertiary py-2">
                  Aktif membro bulunamadı.
                </p>
              ) : (
                activeMembros.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => setSelectedMembroId(m.id)}
                    className={clsx(
                      "flex items-center gap-3 w-full rounded-xl px-3 py-2 text-left text-sm",
                      "border transition-colors duration-100",
                      selectedMembroId === m.id
                        ? "border-brand-periwinkle bg-info/5 text-text-primary"
                        : "border-transparent hover:bg-surface-50 text-text-secondary hover:text-text-primary"
                    )}
                  >
                    <Avatar name={m.name} size="xs" />
                    <span className="font-medium">{m.name}</span>
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        {/* Başlık (opsiyonel) */}
        <Input
          label="Toplantı Başlığı (opsiyonel)"
          placeholder="Örn: Haftalık senkronizasyon"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={100}
        />

      </div>

      <div className="px-6 pb-5 flex gap-3 justify-end">
        <Button variant="outline" size="md" onClick={handleClose}>
          İptal
        </Button>
        <Button
          variant="primary"
          size="md"
          onClick={() => mutation.mutate()}
          loading={mutation.isPending}
          disabled={!selectedMembroId}
        >
          Başlat
        </Button>
      </div>
    </Modal>
  );
}
