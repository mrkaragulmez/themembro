/**
 * frontend/src/components/modals/CreateMembroModal.tsx
 * Faz 6 — CreateMembro Modal (yeniden yazıldı)
 * Sol: SYS_Membros şablon kataloğu (12 kart) | Sağ: ekstra prompt + skills
 */

"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { clsx } from "clsx";
import { Lock, Zap, AlertCircle } from "lucide-react";

import { useAppStore } from "@/stores/appStore";
import { membroApi, sysMembroApi } from "@/lib/api";
import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import type { SysMembro, SysSkillWithStatus } from "@/types";

// ─── Tool listesi (backend MCP skills'ten gelecek, şimdilik sabit) ───────────

// (eski AVAILABLE_TOOLS kaldırıldı — skill'ler artık SYS_Skills'ten geliyor)

// ─── Boş form state ───────────────────────────────────────────────────────────



// ─── Sol panel: Membro listesi ────────────────────────────────────────────────

// ─── Sol panel: Şablon Kataloğu ───────────────────────────────────────────────

function TemplateCard({
  template,
  selected,
  onClick,
}: {
  template: SysMembro;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "flex flex-col items-start gap-1 w-full rounded-xl p-3 text-left",
        "border transition-all duration-100",
        selected
          ? "border-brand-periwinkle bg-info/5 shadow-[0_0_0_1px_theme(colors.brand.periwinkle)]"
          : "border-border-default hover:border-border-active hover:bg-surface-50"
      )}
    >
      <p className="text-sm font-semibold text-text-primary leading-tight">{template.name}</p>
      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-surface-100 text-text-tertiary uppercase tracking-wide">
        {template.role}
      </span>
      {template.description && (
        <p className="text-xs text-text-tertiary line-clamp-2 mt-0.5">{template.description}</p>
      )}
    </button>
  );
}

function TemplateCatalog({
  templates,
  isLoading,
  selectedId,
  onSelect,
}: {
  templates: SysMembro[];
  isLoading: boolean;
  selectedId: string | null;
  onSelect: (t: SysMembro) => void;
}) {
  return (
    <div className="flex flex-col h-full">
      <div className="px-5 py-4 border-b border-border-default shrink-0">
        <p className="text-xs font-semibold uppercase tracking-widest text-text-tertiary">
          Membro Şablonları
        </p>
        <p className="text-xs text-text-tertiary mt-0.5">Bir rol seçerek başla</p>
      </div>

      <div className="flex-1 overflow-y-auto p-3 scrollbar-thin">
        {isLoading ? (
          <div className="grid grid-cols-2 gap-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-20 rounded-xl bg-surface-50 animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-2">
            {templates.map((t) => (
              <TemplateCard
                key={t.id}
                template={t}
                selected={selectedId === t.id}
                onClick={() => onSelect(t)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Sağ panel: Form ──────────────────────────────────────────────────────────

// ─── Sağ panel: Skill satırı + Konfig paneli ─────────────────────────────────

function SkillRow({
  skill,
  active,
  onToggle,
}: {
  skill: SysSkillWithStatus;
  active: boolean;
  onToggle: () => void;
}) {
  const isSelf     = skill.is_self_skill;
  const canToggle  = !isSelf && skill.has_integration;
  const needsInteg = !isSelf && !skill.has_integration;

  return (
    <div
      className={clsx(
        "flex items-center justify-between gap-3 p-3 rounded-xl border",
        "transition-colors duration-100",
        active && !needsInteg
          ? "border-brand-periwinkle bg-info/5"
          : "border-border-default",
        needsInteg && "opacity-60"
      )}
    >
      <div className="flex items-center gap-2.5 min-w-0">
        {isSelf ? (
          <Zap size={15} className="text-brand-periwinkle shrink-0" />
        ) : (
          <div className={clsx("w-3.5 h-3.5 rounded-full border-2 shrink-0",
            active && canToggle ? "bg-brand-periwinkle border-brand-periwinkle" : "border-border-default"
          )} />
        )}
        <div className="min-w-0">
          <p className="text-sm font-medium text-text-primary">{skill.name}</p>
          {skill.description && (
            <p className="text-xs text-text-tertiary truncate">{skill.description}</p>
          )}
        </div>
      </div>

      <div className="shrink-0">
        {isSelf ? (
          <span className="flex items-center gap-1 text-[10px] text-text-tertiary">
            <Lock size={10} />
            Dahili
          </span>
        ) : needsInteg ? (
          <span className="flex items-center gap-1 text-[10px] text-warning">
            <AlertCircle size={10} />
            Entegrasyon yok
          </span>
        ) : (
          <button
            onClick={onToggle}
            className={clsx(
              "relative w-9 h-5 rounded-full transition-colors duration-150",
              active ? "bg-brand-periwinkle" : "bg-surface-100"
            )}
            aria-pressed={active}
            aria-label={`${skill.name} ${active ? "kapat" : "aç"}`}
          >
            <span
              className={clsx(
                "absolute top-0.5 w-4 h-4 bg-white rounded-full shadow",
                "transition-transform duration-150",
                active ? "translate-x-[18px]" : "translate-x-0.5"
              )}
            />
          </button>
        )}
      </div>
    </div>
  );
}

function ConfigPanel({
  template,
  skills,
  skillsLoading,
  extraPrompt,
  onExtraPromptChange,
  activeCaps,
  onToggleCap,
  onSubmit,
  isSubmitting,
}: {
  template: SysMembro;
  skills: SysSkillWithStatus[];
  skillsLoading: boolean;
  extraPrompt: string;
  onExtraPromptChange: (v: string) => void;
  activeCaps: string[];
  onToggleCap: (slug: string) => void;
  onSubmit: () => void;
  isSubmitting: boolean;
}) {
  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b border-border-default shrink-0">
        <h2 className="text-base font-semibold text-text-primary">{template.name}</h2>
        <p className="text-xs text-text-tertiary mt-0.5">{template.role}</p>
        {template.description && (
          <p className="text-sm text-text-secondary mt-2">{template.description}</p>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6 scrollbar-thin">
        <Textarea
          label="Ekstra Talimatlar (opsiyonel)"
          placeholder="Bu membro'ya özgü ek talimatlar... Örn: Her zaman Türkçe yanıt ver."
          value={extraPrompt}
          onChange={(e) => onExtraPromptChange(e.target.value)}
          rows={4}
          hint="Bu metin, membro'nun temel rolüne eklenir. Boş bırakabilirsin."
        />

        <div>
          <p className="text-sm font-medium text-text-primary mb-3">Skills</p>
          {skillsLoading ? (
            <div className="space-y-2">
              {[1, 2].map((i) => (
                <div key={i} className="h-14 rounded-xl bg-surface-50 animate-pulse" />
              ))}
            </div>
          ) : skills.length === 0 ? (
            <p className="text-xs text-text-tertiary">
              Bu şablon için henüz skill tanımlanmamış.
            </p>
          ) : (
            <div className="space-y-2">
              {skills.map((skill) => (
                <SkillRow
                  key={skill.id}
                  skill={skill}
                  active={skill.is_self_skill || activeCaps.includes(skill.slug)}
                  onToggle={() => onToggleCap(skill.slug)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="shrink-0 flex items-center justify-end gap-3 px-6 py-4 border-t border-border-default">
        <Button
          variant="primary"
          size="md"
          onClick={onSubmit}
          loading={isSubmitting}
        >
          Oluştur
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

  const [selectedTemplate, setSelectedTemplate] = useState<SysMembro | null>(null);
  const [extraPrompt, setExtraPrompt]           = useState("");
  const [activeCaps, setActiveCaps]             = useState<string[]>([]);

  // Şablon listesini yükle (public endpoint — auth gerektirmez)
  const { data: templates = [], isLoading: templatesLoading } = useQuery({
    queryKey: ["sys-membros"],
    queryFn:  sysMembroApi.list,
    enabled:  createMembroModalOpen,
  });

  // Seçili şablonun skill'lerini yükle
  const { data: skills = [], isLoading: skillsLoading } = useQuery({
    queryKey: ["sys-membro-skills", selectedTemplate?.id],
    queryFn:  () => sysMembroApi.getSkills(selectedTemplate!.id),
    enabled:  !!selectedTemplate,
  });

  function handleSelectTemplate(t: SysMembro) {
    setSelectedTemplate(t);
    setExtraPrompt("");
    setActiveCaps([]);
  }

  function handleToggleCap(slug: string) {
    setActiveCaps((prev) =>
      prev.includes(slug) ? prev.filter((s) => s !== slug) : [...prev, slug]
    );
  }

  const mutation = useMutation({
    mutationFn: () => {
      if (!selectedTemplate) throw new Error("Şablon seçilmedi.");
      // Self-skill'lerin slug'larını da dahil et
      const selfSlugs = skills
        .filter((s) => s.is_self_skill)
        .map((s) => s.slug);
      return membroApi.create({
        sys_membro_id: selectedTemplate.id,
        extra_prompt:  extraPrompt.trim() || undefined,
        tools_json:    [...selfSlugs, ...activeCaps],
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["membros"] });
      toast.success("Membro oluşturuldu.");
      handleClose();
    },
    onError: () => {
      toast.error("Oluşturulamadı, tekrar dene.");
    },
  });

  function handleClose() {
    closeModals();
    setSelectedTemplate(null);
    setExtraPrompt("");
    setActiveCaps([]);
  }

  return (
    <Modal
      open={createMembroModalOpen}
      onClose={handleClose}
      size="fullscreen"
      closeOnBackdrop
    >
      <div className="flex h-full">
        {/* Sol panel — Şablon Kataloğu */}
        <div className="w-[320px] shrink-0 border-r border-border-default overflow-hidden">
          <TemplateCatalog
            templates={templates}
            isLoading={templatesLoading}
            selectedId={selectedTemplate?.id ?? null}
            onSelect={handleSelectTemplate}
          />
        </div>

        {/* Sağ panel — Konfigürasyon veya boş durum */}
        <div className="flex-1 overflow-hidden">
          {selectedTemplate ? (
            <ConfigPanel
              template={selectedTemplate}
              skills={skills}
              skillsLoading={skillsLoading}
              extraPrompt={extraPrompt}
              onExtraPromptChange={setExtraPrompt}
              activeCaps={activeCaps}
              onToggleCap={handleToggleCap}
              onSubmit={() => mutation.mutate()}
              isSubmitting={mutation.isPending}
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-text-tertiary px-8 text-center">
              <div className="w-12 h-12 rounded-2xl bg-surface-50 flex items-center justify-center">
                <Zap size={22} className="text-text-secondary" />
              </div>
              <p className="text-sm font-medium text-text-secondary">
                Soldan bir şablon seç
              </p>
              <p className="text-xs leading-relaxed max-w-xs">
                Her membro, önceden tanımlanmış bir role (şablona) dayanır.
                İstersen ekstra talimatlar ekleyerek özelleştirebilirsin.
              </p>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
