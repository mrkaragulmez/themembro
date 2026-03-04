/**
 * frontend/src/components/modals/CreateMembroModal.tsx
 * Faz 6 — CreateMembro Modal
 * Sol: scrollable membro listesi | Sağ: form
 * Faz 6.3 kapsamında tam API entegrasyonu yapılacak.
 */

"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { clsx } from "clsx";
import { Plus } from "lucide-react";

import { useAppStore } from "@/stores/appStore";
import { membroApi } from "@/lib/api";
import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Avatar } from "@/components/ui/avatar";
import { MembroStatusBadge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/toast";
import { MEMBRO_COLORS } from "@/types";
import type { Membro, CreateMembroPayload } from "@/types";

// ─── Tool listesi (backend MCP skills'ten gelecek, şimdilik sabit) ───────────

const AVAILABLE_TOOLS = [
  { id: "knowledge_search", label: "Bilgi Arama" },
  { id: "send_email",       label: "E-posta Gönder" },
  { id: "calendar",         label: "Takvim",  disabled: true },
];

// ─── Boş form state ───────────────────────────────────────────────────────────

const EMPTY_FORM: CreateMembroPayload = {
  name: "",
  persona: "",
  system_prompt: "",
  tools: ["knowledge_search"],
  color: MEMBRO_COLORS[0],
};

// ─── Sol panel: Membro listesi ────────────────────────────────────────────────

function MembroList({
  membros,
  selectedId,
  onSelect,
  onNewMembro,
}: {
  membros: Membro[];
  selectedId: string | null;
  onSelect: (m: Membro) => void;
  onNewMembro: () => void;
}) {
  return (
    <div className="flex flex-col h-full">
      <div className="px-5 py-4 border-b border-border-default shrink-0">
        <p className="text-xs font-semibold uppercase tracking-widest text-text-tertiary">
          Membro'larım
        </p>
      </div>

      <div className="flex-1 overflow-y-auto py-2 px-2 scrollbar-thin space-y-0.5">
        {membros.map((m) => (
          <button
            key={m.id}
            onClick={() => onSelect(m)}
            className={clsx(
              "flex items-center gap-3 w-full rounded-xl px-3 py-2.5 text-left",
              "transition-colors duration-100 relative",
              selectedId === m.id
                ? "bg-surface-100 text-text-primary"
                : "hover:bg-surface-50 text-text-secondary hover:text-text-primary"
            )}
          >
            {selectedId === m.id && (
              <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-6 rounded-full bg-brand-periwinkle" />
            )}
            <Avatar name={m.name} color={m.color} size="sm" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{m.name}</p>
              <MembroStatusBadge status={m.status} />
            </div>
          </button>
        ))}
      </div>

      <div className="p-2 border-t border-border-default shrink-0">
        <button
          onClick={onNewMembro}
          className={clsx(
            "flex items-center gap-2 w-full rounded-xl px-3 py-2 text-sm",
            selectedId === null
              ? "bg-surface-100 text-text-primary font-medium"
              : "text-text-secondary hover:bg-surface-50 hover:text-text-primary",
            "transition-colors duration-100"
          )}
        >
          <Plus size={15} />
          <span>Yeni Membro</span>
        </button>
      </div>
    </div>
  );
}

// ─── Sağ panel: Form ──────────────────────────────────────────────────────────

function MembroForm({
  initialData,
  onSave,
  isSaving,
}: {
  initialData: CreateMembroPayload;
  onSave: (data: CreateMembroPayload) => void;
  isSaving: boolean;
}) {
  const [form, setForm] = useState<CreateMembroPayload>(initialData);

  function update<K extends keyof CreateMembroPayload>(key: K, value: CreateMembroPayload[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function toggleTool(toolId: string) {
    setForm((prev) => ({
      ...prev,
      tools: prev.tools.includes(toolId)
        ? prev.tools.filter((t) => t !== toolId)
        : [...prev.tools, toolId],
    }));
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5 scrollbar-thin">
        {/* İsim */}
        <Input
          label="İsim"
          placeholder="Örn: Satış Asistanı"
          value={form.name}
          onChange={(e) => update("name", e.target.value)}
          maxLength={80}
        />

        {/* Persona */}
        <Input
          label="Persona Özeti"
          placeholder="Örn: Müşteri sorularını cevaplar"
          value={form.persona}
          onChange={(e) => update("persona", e.target.value)}
          maxLength={120}
          hint={`${form.persona.length}/120`}
        />

        {/* Sistem Prompt */}
        <Textarea
          label="Sistem Prompt"
          placeholder="Sen bir satış asistanısın. Müşteri sorularına nazik ve doğru şekilde cevap ver..."
          value={form.system_prompt}
          onChange={(e) => update("system_prompt", e.target.value)}
          rows={5}
          hint="Bu metin, membro'nun her konuşmada referans alacağı kimliği tanımlar."
        />

        {/* Renk seçimi */}
        <div>
          <p className="text-sm font-medium text-text-primary mb-2">Avatar Rengi</p>
          <div className="flex gap-2 flex-wrap">
            {MEMBRO_COLORS.map((color) => (
              <button
                key={color}
                onClick={() => update("color", color)}
                className={clsx(
                  "w-7 h-7 rounded-full transition-all",
                  form.color === color
                    ? "ring-2 ring-offset-2 ring-brand-periwinkle scale-110"
                    : "hover:scale-105"
                )}
                style={{ backgroundColor: color }}
                aria-label={`Renk: ${color}`}
              />
            ))}
          </div>
        </div>

        {/* Yetenekler */}
        <div>
          <p className="text-sm font-medium text-text-primary mb-2">Yetenekler (Tools)</p>
          <div className="space-y-2">
            {AVAILABLE_TOOLS.map((tool) => (
              <label
                key={tool.id}
                className={clsx(
                  "flex items-center gap-3 p-3 rounded-xl border cursor-pointer",
                  "transition-colors duration-100",
                  tool.disabled && "opacity-40 cursor-not-allowed",
                  form.tools.includes(tool.id)
                    ? "border-brand-periwinkle bg-info/5"
                    : "border-border-default hover:border-border-active"
                )}
              >
                <input
                  type="checkbox"
                  checked={form.tools.includes(tool.id)}
                  onChange={() => !tool.disabled && toggleTool(tool.id)}
                  disabled={tool.disabled}
                  className="accent-brand-periwinkle"
                />
                <span className="text-sm text-text-primary">{tool.label}</span>
                {tool.disabled && (
                  <span className="ml-auto text-xs text-text-tertiary">Yakında</span>
                )}
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="shrink-0 flex items-center justify-end gap-3 px-6 py-4 border-t border-border-default">
        <Button
          variant="primary"
          size="md"
          onClick={() => onSave(form)}
          loading={isSaving}
          disabled={!form.name.trim()}
        >
          Kaydet
        </Button>
      </div>
    </div>
  );
}

// ─── Ana Modal ────────────────────────────────────────────────────────────────

export function CreateMembroModal() {
  const { createMembroModalOpen, closeModals } = useAppStore();
  const queryClient = useQueryClient();
  const toast = useToast();

  const { data: membros = [] } = useQuery({
    queryKey: ["membros"],
    queryFn: membroApi.list,
    enabled: createMembroModalOpen,
  });

  const [selectedMembro, setSelectedMembro] = useState<Membro | null>(null);

  // Yeni membro seçilince null; var olanda Membro objesi
  const formInitial: CreateMembroPayload = selectedMembro
    ? {
        name:          selectedMembro.name,
        persona:       selectedMembro.persona,
        system_prompt: selectedMembro.system_prompt,
        tools:         selectedMembro.tools,
        color:         selectedMembro.color,
      }
    : EMPTY_FORM;

  const mutation = useMutation({
    mutationFn: (data: CreateMembroPayload) =>
      selectedMembro
        ? membroApi.update(selectedMembro.id, data)
        : membroApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["membros"] });
      toast.success(selectedMembro ? "Membro güncellendi." : "Membro oluşturuldu.");
      closeModals();
      setSelectedMembro(null);
    },
    onError: () => {
      toast.error("Kaydedilemedi, tekrar dene.");
    },
  });

  function handleClose() {
    closeModals();
    setSelectedMembro(null);
  }

  return (
    <Modal
      open={createMembroModalOpen}
      onClose={handleClose}
      size="fullscreen"
      closeOnBackdrop
    >
      <div className="flex h-full">
        {/* Sol panel */}
        <div className="w-[280px] shrink-0 border-r border-border-default overflow-hidden">
          <MembroList
            membros={membros}
            selectedId={selectedMembro?.id ?? null}
            onSelect={(m) => setSelectedMembro(m)}
            onNewMembro={() => setSelectedMembro(null)}
          />
        </div>

        {/* Sağ panel */}
        <div className="flex-1 overflow-hidden">
          <div className="px-6 py-4 border-b border-border-default">
            <h2 className="text-base font-semibold text-text-primary">
              {selectedMembro ? `${selectedMembro.name} — Düzenle` : "Yeni Membro Oluştur"}
            </h2>
          </div>
          <MembroForm
            key={selectedMembro?.id ?? "__new__"}
            initialData={formInitial}
            onSave={(data) => mutation.mutate(data)}
            isSaving={mutation.isPending}
          />
        </div>
      </div>
    </Modal>
  );
}
