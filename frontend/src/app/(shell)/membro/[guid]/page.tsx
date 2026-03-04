/**
 * frontend/src/app/(shell)/membro/[guid]/page.tsx
 * Faz 6 — Membro detay + sohbet ekranı
 * Sol sidebar: aktivite özeti | Orta: chat | Sağ: detay paneli
 */

"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { use } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Video,
  Edit2,
  Archive,
  MoreVertical,
  FileText,
} from "lucide-react";
import { clsx } from "clsx";

import { membroApi, chatApi } from "@/lib/api";
import { useAppStore } from "@/stores/appStore";
import { useToast } from "@/components/ui/toast";
import { Avatar } from "@/components/ui/avatar";
import { MembroStatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ChatTimeline } from "@/components/chat/ChatTimeline";
import { ChatInput } from "@/components/chat/ChatInput";
import { MembroActivityPanel } from "@/components/membro/MembroActivityPanel";
import type { ChatMessage } from "@/types";

// ─── Sağ panel: Membro detayları ─────────────────────────────────────────────

function MembroDetailPanel({
  membroId,
  onEdit,
}: {
  membroId: string;
  onEdit: () => void;
}) {
  const { data: membro, isLoading } = useQuery({
    queryKey: ["membro", membroId],
    queryFn: () => membroApi.get(membroId),
  });
  const qc = useQueryClient();
  const { openCreateMeeting } = useAppStore();
  const toast = useToast();

  const archiveMutation = useMutation({
    mutationFn: () => membroApi.update(membroId, { status: "archived" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["membros"] });
      toast.success("Membro arşivlendi.");
    },
    onError: () => toast.error("Arşivlenemedi, tekrar dene."),
  });

  if (isLoading) {
    return (
      <div className="p-4 space-y-3">
        <Skeleton className="h-12 w-12 rounded-full" />
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-3 w-24" />
      </div>
    );
  }

  if (!membro) return null;

  return (
    <div className="flex flex-col h-full">
      {/* Üst */}
      <div className="px-4 py-4 border-b border-border-default">
        <div className="flex items-start gap-3">
          <Avatar name={membro.name} color={membro.color} size="md" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-text-primary leading-tight truncate">
              {membro.name}
            </p>
            <MembroStatusBadge status={membro.status} />
          </div>
        </div>

        {/* Aksiyonlar */}
        <div className="flex gap-1.5 mt-3">
          <Button
            variant="outline"
            size="sm"
            icon={<Video size={13} />}
            onClick={() => openCreateMeeting(membro.id)}
            className="flex-1 justify-center text-xs"
          >
            Toplantı
          </Button>
          <Button
            variant="ghost"
            size="sm"
            icon={<Edit2 size={13} />}
            onClick={onEdit}
            aria-label="Düzenle"
          />
          <Button
            variant="ghost"
            size="sm"
            icon={<Archive size={12} />}
            onClick={() => archiveMutation.mutate()}
            loading={archiveMutation.isPending}
            aria-label="Arşivle"
          />
        </div>
      </div>

      {/* Bilgiler */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 scrollbar-thin text-xs">
        <div>
          <p className="font-semibold text-text-tertiary uppercase tracking-widest mb-1">
            Persona
          </p>
          <p className="text-text-secondary leading-relaxed">{membro.persona || "—"}</p>
        </div>

        <div>
          <p className="font-semibold text-text-tertiary uppercase tracking-widest mb-1">
            Sistem Prompt
          </p>
          <p className="text-text-secondary leading-relaxed whitespace-pre-wrap line-clamp-6">
            {membro.system_prompt || "—"}
          </p>
        </div>

        {membro.tools.length > 0 && (
          <div>
            <p className="font-semibold text-text-tertiary uppercase tracking-widest mb-1">
              Yetenekler
            </p>
            <div className="flex flex-wrap gap-1.5">
              {membro.tools.map((tool) => (
                <span
                  key={tool}
                  className="flex items-center gap-1 px-2 py-0.5 rounded-lg bg-surface-100 text-text-secondary"
                >
                  <FileText size={10} />
                  {tool}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Ana Sayfa ────────────────────────────────────────────────────────────────

type Params = Promise<{ guid: string }>;

export default function MembroDetailPage({ params }: { params: Params }) {
  const { guid } = use(params);
  const { openCreateMembro } = useAppStore();

  const { data: membro, isLoading: membroLoading } = useQuery({
    queryKey: ["membro", guid],
    queryFn: () => membroApi.get(guid),
  });

  const { data: history = [], isLoading: historyLoading } = useQuery({
    queryKey: ["chat-history", guid],
    queryFn: () => chatApi.history(guid),
  });

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [showDetail, setShowDetail] = useState(true);

  // Geçmiş yüklenince state'e tek seferlik aktar
  const historyInitialized = useRef(false);
  useEffect(() => {
    if (!historyInitialized.current && history.length > 0) {
      historyInitialized.current = true;
      setMessages(history);
    }
  }, [history]);

  const handleSend = useCallback(async () => {
    if (!inputValue.trim() || isStreaming) return;

    const userMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      membro_id: guid,
      role: "user",
      content: inputValue.trim(),
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputValue("");
    setIsStreaming(true);
    setStreamingText("");

    try {
      const stream = await chatApi.stream({ membro_id: guid, message: userMsg.content });
      const reader = stream.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        accumulated += decoder.decode(value, { stream: true });
        setStreamingText(accumulated);
      }

      // Streaming bitti → kalıcı mesaj olarak ekle
      const aiMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        membro_id: guid,
        role: "assistant",
        content: accumulated,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch {
      // Hata durumunda sessizce geç
    } finally {
      setIsStreaming(false);
      setStreamingText("");
    }
  }, [guid, inputValue, isStreaming]);

  return (
    <div className="flex h-full animate-fade-in">
      {/* Chat alanı */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* TopBar */}
        <div className="flex items-center gap-3 px-5 py-3 border-b border-border-default bg-surface-0 shrink-0">
          {membroLoading ? (
            <div className="flex gap-3 items-center">
              <Skeleton className="w-8 h-8 rounded-full" />
              <Skeleton className="h-4 w-24" />
            </div>
          ) : membro ? (
            <>
              <Avatar name={membro.name} color={membro.color} size="sm" />
              <span className="text-sm font-semibold text-text-primary">{membro.name}</span>
              <MembroStatusBadge status={membro.status} />
            </>
          ) : null}

          <button
            onClick={() => setShowDetail((v) => !v)}
            className={clsx(
              "ml-auto p-1.5 rounded-lg transition-colors text-text-tertiary hover:text-text-primary hover:bg-surface-100"
            )}
            aria-label="Detay paneli"
          >
            <MoreVertical size={15} />
          </button>
        </div>

        {/* Mesajlar */}
        <div className="flex-1 overflow-y-auto px-5 py-5 scrollbar-thin">
          {historyLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className={clsx("h-10 rounded-2xl", i % 2 === 0 ? "w-1/2 ml-auto" : "w-2/3")} />
              ))}
            </div>
          ) : (
            <ChatTimeline
              messages={messages}
              isStreaming={isStreaming}
              streamingText={streamingText}
              membroName={membro?.name}
              membroColor={membro?.color}
            />
          )}
        </div>

        {/* Input */}
        <div className="px-5 pb-5 shrink-0">
          <ChatInput
            value={inputValue}
            onChange={setInputValue}
            onSend={handleSend}
            disabled={isStreaming || membroLoading}
            placeholder={`${membro?.name ?? "Membro"}'ya yaz...`}
          />
        </div>
      </div>

      {/* Sağ detay paneli */}
      {showDetail && (
        <aside className="w-72 shrink-0 border-l border-border-default bg-surface-0 hidden lg:flex flex-col">
          {/* Üst: Membro profil + hızlı aksiyonlar */}
          <div className="shrink-0 border-b border-border-default">
            <MembroDetailPanel membroId={guid} onEdit={openCreateMembro} />
          </div>
          {/* Alt: Toplantılar + Bilgi Bankası sekmeleri */}
          <div className="flex-1 min-h-0">
            <MembroActivityPanel membroId={guid} />
          </div>
        </aside>
      )}
    </div>
  );
}
