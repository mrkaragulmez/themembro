/**
 * frontend/src/components/chat/ChatBubble.tsx
 * Faz 6 — Tek sohbet baloncuğu
 */

"use client";

import { clsx } from "clsx";
import { Avatar } from "@/components/ui/avatar";
import type { ChatMessage } from "@/types";

interface ChatBubbleProps {
  message: ChatMessage;
  membroName?: string;
  membroColor?: string;
}

export function ChatBubble({ message, membroName, membroColor }: ChatBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={clsx(
        "flex gap-3 animate-slide-up",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      {!isUser && (
        <Avatar
          name={membroName ?? "M"}
          color={membroColor}
          size="sm"
          className="shrink-0 mt-0.5"
        />
      )}

      {/* Balon */}
      <div
        className={clsx(
          "max-w-[70%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-brand-navy text-white rounded-tr-sm"
            : "bg-surface-100 text-text-primary rounded-tl-sm border border-border-default"
        )}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.created_at && (
          <p
            className={clsx(
              "text-[10px] mt-1.5",
              isUser ? "text-white/50 text-right" : "text-text-tertiary"
            )}
          >
            {new Date(message.created_at).toLocaleTimeString("tr-TR", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        )}
      </div>
    </div>
  );
}
