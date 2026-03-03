/**
 * frontend/src/app/components/VoiceRoom.tsx
 * Faz 4 — WebRTC Sesli Toplantı Bileşeni
 *
 * Membro API'sine istek atarak LiveKit token alır ve
 * WebRTC Room'a bağlanır. Mikrofon durumu + transcript görüntülenir.
 */

"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useRoomContext,
  useLocalParticipant,
  useTracks,
  AudioTrack,
} from "@livekit/components-react";
import "@livekit/components-styles";
import { Track } from "livekit-client";

// ─── Tipler ─────────────────────────────────────────────────────────────────

interface TranscriptLine {
  id: string;
  speaker: "user" | string;
  text: string;
  ts: string;
}

interface MeetingSession {
  meetingId: string;
  roomName: string;
  livekitUrl: string;
  token: string;
}

// ─── API Yardımcı ────────────────────────────────────────────────────────────

async function createMeeting(
  membroId: string,
  apiBase: string
): Promise<MeetingSession> {
  const res = await fetch(`${apiBase}/api/v1/meetings/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      // JWT token cookie'den veya localStorage'dan alınmalı;
      // gerçek auth entegrasyonu Faz 5'te tamamlanır
      Authorization: `Bearer ${localStorage.getItem("access_token") ?? ""}`,
    },
    body: JSON.stringify({ membro_id: membroId }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }

  const data = await res.json();
  return {
    meetingId: data.meeting_id,
    roomName: data.room_name,
    livekitUrl: data.livekit_url,
    token: data.token,
  };
}

async function endMeeting(meetingId: string, apiBase: string): Promise<void> {
  await fetch(`${apiBase}/api/v1/meetings/${meetingId}/end`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${localStorage.getItem("access_token") ?? ""}`,
    },
  });
}

// ─── İç bileşen: Room içinde transcript takibi ──────────────────────────────

function VoiceControls({
  onTranscript,
}: {
  onTranscript: (line: TranscriptLine) => void;
}) {
  const { localParticipant } = useLocalParticipant();
  const [micEnabled, setMicEnabled] = useState(false);

  const toggleMic = useCallback(async () => {
    await localParticipant.setMicrophoneEnabled(!micEnabled);
    setMicEnabled((v) => !v);
  }, [localParticipant, micEnabled]);

  // Ses track'lerini render et (ajan sesini browser'da çalmak için)
  const audioTracks = useTracks([Track.Source.Microphone], {
    onlySubscribed: true,
  });

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Ajan ses output'u */}
      <RoomAudioRenderer />
      {audioTracks.map((track) => (
        <AudioTrack key={track.publication.trackSid} trackRef={track} />
      ))}

      {/* Mikrofon butonu */}
      <button
        onClick={toggleMic}
        className={`w-20 h-20 rounded-full text-white text-xl font-bold transition-all shadow-lg ${
          micEnabled
            ? "bg-red-500 hover:bg-red-600 animate-pulse"
            : "bg-green-500 hover:bg-green-600"
        }`}
        aria-label={micEnabled ? "Mikrofonu Kapat" : "Mikrofonu Aç"}
      >
        {micEnabled ? "🔴" : "🎤"}
      </button>
      <p className="text-sm text-gray-500">
        {micEnabled ? "Dinleniyor..." : "Konuşmak için tıkla"}
      </p>
    </div>
  );
}

// ─── ANA BİLEŞEN ────────────────────────────────────────────────────────────

export interface VoiceRoomProps {
  /** Hangi Membro ile toplantı yapılacak */
  membroId: string;
  /** Backend API base URL (default: http://localhost:8000) */
  apiBase?: string;
  /** Toplantıdan çıkıldığında çağrılır */
  onLeave?: () => void;
}

type Phase = "idle" | "connecting" | "connected" | "error" | "ended";

export default function VoiceRoom({
  membroId,
  apiBase = "http://localhost:8000",
  onLeave,
}: VoiceRoomProps) {
  const [phase, setPhase]       = useState<Phase>("idle");
  const [error, setError]       = useState<string | null>(null);
  const [session, setSession]   = useState<MeetingSession | null>(null);
  const [transcripts, setTranscripts] = useState<TranscriptLine[]>([]);
  const transcriptRef           = useRef<HTMLDivElement>(null);

  // Transcript listesi güncellendikçe aşağı kaydır
  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [transcripts]);

  const handleStart = async () => {
    setPhase("connecting");
    setError(null);
    try {
      const s = await createMeeting(membroId, apiBase);
      setSession(s);
      setPhase("connected");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Bağlantı hatası");
      setPhase("error");
    }
  };

  const handleLeave = async () => {
    if (session) {
      await endMeeting(session.meetingId, apiBase).catch(() => {});
    }
    setSession(null);
    setPhase("ended");
    onLeave?.();
  };

  const addTranscript = useCallback((line: TranscriptLine) => {
    setTranscripts((prev) => [...prev.slice(-99), line]);
  }, []);

  // ─── RENDER ────────────────────────────────────────────────────────────────

  if (phase === "idle" || phase === "error" || phase === "ended") {
    return (
      <div className="flex flex-col items-center justify-center gap-4 p-8">
        {phase === "error" && (
          <p className="text-red-500 text-sm">{error}</p>
        )}
        {phase === "ended" && (
          <p className="text-gray-500 text-sm">Toplantı sonlandırıldı.</p>
        )}
        <button
          onClick={handleStart}
          className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 font-semibold shadow"
        >
          {phase === "ended" ? "Yeni Toplantı Başlat" : "Toplantı Başlat"}
        </button>
      </div>
    );
  }

  if (phase === "connecting") {
    return (
      <div className="flex items-center justify-center p-8">
        <p className="text-gray-500 animate-pulse">Bağlanıyor...</p>
      </div>
    );
  }

  // phase === "connected"
  return (
    <div className="flex flex-col gap-4 p-4 max-w-lg mx-auto">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-800">Sesli Toplantı</h2>
        <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">
          Canlı
        </span>
      </div>

      {/* LiveKit Room bağlantısı */}
      <LiveKitRoom
        serverUrl={session!.livekitUrl}
        token={session!.token}
        connect={true}
        audio={true}
        video={false}
        onDisconnected={handleLeave}
      >
        <VoiceControls onTranscript={addTranscript} />
      </LiveKitRoom>

      {/* Transcript */}
      <div
        ref={transcriptRef}
        className="h-48 overflow-y-auto border border-gray-200 rounded-lg p-3 bg-gray-50 text-sm space-y-1"
      >
        {transcripts.length === 0 ? (
          <p className="text-gray-400 italic">Transcript bekleniyor...</p>
        ) : (
          transcripts.map((t) => (
            <div key={t.id} className="flex gap-2">
              <span className={`font-semibold shrink-0 ${t.speaker === "user" ? "text-blue-600" : "text-purple-600"}`}>
                {t.speaker === "user" ? "Sen" : "Membro"}:
              </span>
              <span className="text-gray-700">{t.text}</span>
            </div>
          ))
        )}
      </div>

      {/* Toplantıyı Bitir */}
      <button
        onClick={handleLeave}
        className="w-full py-2 bg-red-100 text-red-600 rounded-lg hover:bg-red-200 font-medium"
      >
        Toplantıyı Bitir
      </button>
    </div>
  );
}
