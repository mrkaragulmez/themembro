/**
 * frontend/src/components/chat/ChatInput.tsx
 * Faz 6 — Sohbet mesaj giriş kutusu
 * Enter → gönder, Shift+Enter → yeni satır
 */

"use client";

import { useRef, useEffect } from "react";
import { Send, Mic } from "lucide-react";
import { clsx } from "clsx";

interface ChatInputProps {
  value: string;
  onChange: (val: string) => void;
  onSend: () => void;
  disabled?: boolean;
  placeholder?: string;
  onVoice?: () => void;
}

export function ChatInput({
  value,
  onChange,
  onSend,
  disabled,
  placeholder = "Bir şey yaz...",
  onVoice,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Otomatik yükseklik
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [value]);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled) onSend();
    }
  }

  return (
    <div
      className={clsx(
        "flex items-end gap-2 bg-surface-0 border border-border-default",
        "rounded-2xl px-3 py-2 shadow-sm",
        "focus-within:border-brand-periwinkle focus-within:ring-2 focus-within:ring-brand-periwinkle/10",
        "transition-all duration-150"
      )}
    >
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        className={clsx(
          "flex-1 resize-none bg-transparent text-sm text-text-primary",
          "placeholder:text-text-tertiary outline-none scrollbar-thin",
          "max-h-32 py-1.5",
          disabled && "opacity-50"
        )}
      />

      <div className="flex items-center gap-1 shrink-0 pb-0.5">
        {onVoice && (
          <button
            onClick={onVoice}
            className="p-2 rounded-xl text-text-tertiary hover:bg-surface-100 hover:text-brand-periwinkle transition-colors"
            aria-label="Sesli yanlar"
          >
            <Mic size={15} />
          </button>
        )}
        <button
          onClick={onSend}
          disabled={!value.trim() || disabled}
          className={clsx(
            "p-2 rounded-xl transition-colors",
            value.trim() && !disabled
              ? "bg-brand-navy text-white hover:bg-brand-navy/90"
              : "text-text-tertiary bg-surface-100 cursor-not-allowed"
          )}
          aria-label="Gönder"
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  );
}
