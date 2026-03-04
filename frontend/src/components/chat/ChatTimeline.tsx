/**
 * frontend/src/components/chat/ChatTimeline.tsx
 * Faz 6 — Mesajlar zaman çizelgesi
 * Streaming desteği: son mesaj animasyonlu imleç
 */

"use client";

import { useEffect, useRef } from "react";
import { clsx } from "clsx";
import { ChatBubble } from "./ChatBubble";
import { Spinner } from "@/components/ui/spinner";
import type { ChatMessage } from "@/types";

interface ChatTimelineProps {
  messages: ChatMessage[];
  isStreaming?: boolean;
  streamingText?: string;
  membroName?: string;
  membroColor?: string;
}

export function ChatTimeline({
  messages,
  isStreaming,
  streamingText,
  membroName,
  membroColor,
}: ChatTimelineProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Yeni mesajlarda aşağı kaydır
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-6">
        <p className="text-sm text-text-secondary">
          Membro ile konuşmaya başla.
        </p>
        <p className="text-xs text-text-tertiary mt-1">
          Soru sor, görev ver veya bilgi al.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {messages.map((msg) => (
        <ChatBubble
          key={msg.id}
          message={msg}
          membroName={membroName}
          membroColor={membroColor}
        />
      ))}

      {/* Streaming balonu */}
      {isStreaming && (
        <div className="flex gap-3 animate-slide-up">
          {/* Membro tarafı */}
          <div className="max-w-[70%] rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed bg-surface-100 border border-border-default text-text-primary">
            {streamingText ? (
              <span className="whitespace-pre-wrap">
                {streamingText}
                <span
                  className={clsx(
                    "inline-block w-0.5 h-3 ml-0.5 bg-text-primary align-middle",
                    "animate-pulse"
                  )}
                />
              </span>
            ) : (
              <Spinner size="sm" />
            )}
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
