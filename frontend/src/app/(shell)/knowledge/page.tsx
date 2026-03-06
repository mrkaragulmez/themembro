/**
 * frontend/src/app/(shell)/knowledge/page.tsx
 * Faz 6.1 — Bilgi Bankası sayfası
 * Doküman listele, yeni ekle (metin veya URL), sil
 */

"use client";

import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, FileText, Link as LinkIcon, BookOpen } from "lucide-react";
import { clsx } from "clsx";

import { knowledgeApi, membroApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Modal } from "@/components/ui/modal";
import { useToast } from "@/components/ui/toast";
import type { KnowledgeDoc } from "@/types";

// ─── Belge satırı ─────────────────────────────────────────────────────────────

function DocRow({
  doc,
  onDelete,
  deleting,
}: {
  doc: KnowledgeDoc;
  onDelete: () => void;
  deleting: boolean;
}) {
  const icon =
    doc.content_type === "url" ? (
      <LinkIcon size={14} className="text-brand-periwinkle shrink-0" />
    ) : (
      <FileText size={14} className="text-text-tertiary shrink-0" />
    );

  return (
    <div className="flex items-start gap-3 p-4 rounded-xl border border-border-default bg-surface-0 group hover:border-border-active transition-colors">
      <span className="mt-0.5">{icon}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-text-primary truncate">
          {doc.title || "Başlıksız"}
        </p>
        <p className="text-xs text-text-tertiary mt-0.5 truncate">
          {new Date(doc.created_at).toLocaleDateString("tr-TR", {
            day: "numeric",
            month: "short",
            year: "numeric",
          })}
        </p>
      </div>
      <button
        onClick={onDelete}
        disabled={deleting}
        className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-text-tertiary hover:text-error hover:bg-error/5 transition-all disabled:opacity-30"
        aria-label="Sil"
      >
        <Trash2 size={14} />
      </button>
    </div>
  );
}

// ─── Yeni Doküman Modalı ──────────────────────────────────────────────────────

type DocType = "text" | "url";

function AddDocModal({
  open,
  onClose,
  membros,
}: {
  open: boolean;
  onClose: () => void;
  membros: { id: string; name: string }[];
}) {
  const qc = useQueryClient();
  const toast = useToast();
  const [type, setType] = useState<DocType>("text");
  const [membroId, setMembroId] = useState(membros[0]?.id ?? "");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      knowledgeApi.create({ membro_id: membroId, content, title: title || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["knowledge"] });
      toast.success("Doküman eklendi.");
      onClose();
      setTitle("");
      setContent("");
    },
    onError: () => toast.error("Eklenemedi, tekrar dene."),
  });

  function handleClose() {
    onClose();
    setTitle("");
    setContent("");
  }

  return (
    <Modal open={open} onClose={handleClose} size="md" closeOnBackdrop>
      <div className="px-6 py-5 border-b border-border-default flex items-center gap-3">
        <span className="p-2 rounded-xl bg-brand-periwinkle/10 text-brand-periwinkle">
          <BookOpen size={16} />
        </span>
        <h2 className="text-base font-semibold text-text-primary">Doküman Ekle</h2>
      </div>

      <div className="px-6 py-5 space-y-4">
        {/* Tür seçimi */}
        <div className="flex gap-2">
          {(["text", "url"] as DocType[]).map((t) => (
            <button
              key={t}
              onClick={() => setType(t)}
              className={clsx(
                "flex-1 py-2 rounded-xl text-sm font-medium border transition-colors",
                type === t
                  ? "bg-brand-navy text-white border-brand-navy"
                  : "border-border-default text-text-secondary hover:border-border-active"
              )}
            >
              {t === "text" ? "Metin" : "URL"}
            </button>
          ))}
        </div>

        {/* Membro seç */}
        <div>
          <p className="text-sm font-medium text-text-primary mb-1.5">Membro</p>
          <select
            value={membroId}
            onChange={(e) => setMembroId(e.target.value)}
            className="w-full h-9 rounded-xl border border-border-default bg-surface-0 px-3 text-sm text-text-primary outline-none focus:ring-2 focus:ring-brand-periwinkle/20 focus:border-brand-periwinkle transition-all"
          >
            {membros.map((m) => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>
        </div>

        <Input
          label="Başlık (opsiyonel)"
          placeholder="Doküman başlığı"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />

        {type === "text" ? (
          <Textarea
            label="İçerik"
            placeholder="Bilgi bankasına eklenecek metni buraya yaz..."
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={5}
          />
        ) : (
          <Input
            label="URL"
            placeholder="https://..."
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
        )}

      </div>

      <div className="px-6 pb-5 flex justify-end gap-3">
        <Button variant="outline" size="md" onClick={handleClose}>İptal</Button>
        <Button
          variant="primary"
          size="md"
          onClick={() => mutation.mutate()}
          loading={mutation.isPending}
          disabled={!content.trim() || !membroId}
        >
          Ekle
        </Button>
      </div>
    </Modal>
  );
}

// ─── Sayfa ────────────────────────────────────────────────────────────────────

export default function KnowledgePage() {
  const [addOpen, setAddOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const qc = useQueryClient();
  const toast = useToast();

  const { data: docs = [], isLoading } = useQuery({
    queryKey: ["knowledge"],
    queryFn: () => knowledgeApi.list(),
  });

  const { data: membros = [] } = useQuery({
    queryKey: ["membros"],
    queryFn: membroApi.list,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => {
      setDeletingId(id);
      return knowledgeApi.delete(id);
    },
    onSuccess: () => {
      toast.success("Doküman silindi.");
      qc.invalidateQueries({ queryKey: ["knowledge"] });
    },
    onError: () => toast.error("Silinemedi, tekrar dene."),
    onSettled: () => setDeletingId(null),
  });

  const activeMembros = membros.filter((m) => m.is_active);

  return (
    <div className="max-w-3xl mx-auto px-6 py-8 animate-fade-in">
      {/* Başlık */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Bilgi Bankası</h1>
          <p className="text-sm text-text-secondary mt-0.5">
            {isLoading ? "Yükleniyor..." : `${docs.length} doküman`}
          </p>
        </div>
        <Button
          variant="primary"
          size="md"
          icon={<Plus size={15} />}
          iconPosition="left"
          onClick={() => setAddOpen(true)}
          disabled={activeMembros.length === 0}
        >
          Doküman Ekle
        </Button>
      </div>

      {/* Liste */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-16 rounded-xl" />
          ))}
        </div>
      ) : docs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <div className="w-14 h-14 rounded-2xl bg-surface-100 flex items-center justify-center mb-4">
            <BookOpen size={24} className="text-text-tertiary" />
          </div>
          <h3 className="text-base font-semibold text-text-primary">Henüz doküman yok</h3>
          <p className="text-sm text-text-secondary mt-1 max-w-xs">
            Membro'larına metin veya URL ekleyerek bilgi bankası oluştur.
          </p>
          {activeMembros.length === 0 && (
            <p className="text-xs text-text-tertiary mt-2">
              Önce bir membro oluşturman gerekiyor.
            </p>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {docs.map((doc) => (
            <DocRow
              key={doc.id}
              doc={doc}
              onDelete={() => deleteMutation.mutate(doc.id)}
              deleting={deletingId === doc.id}
            />
          ))}
        </div>
      )}

      <AddDocModal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        membros={activeMembros}
      />
    </div>
  );
}
