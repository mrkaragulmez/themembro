# Faz 4: Realtime Voice (Gerçek Zamanlı Ses) ve Toplantı Altyapısı

> **Son güncelleme:** 2026-03-02 — LiveKit Agents framework ve OpenAI Voice Agents belgeleri taranarak güçlendirildi.

Bu faz, Membro projesinin en iddialı ve gecikmeye (latency) en duyarlı katmanıdır. Ziyaretçilerin veya tenant kullanıcılarının ajanlarla "online toplantı" yapabilmesi için WebRTC tabanlı gerçek zamanlı ses altyapısı kurulacaktır.

---

## 1. WebRTC İletişim Katmanı — LiveKit

### 1.1 Neden LiveKit?

Sıfırdan WebRTC sunucusu yazmak yerine, **LiveKit** managed/open-source altyapısı tercih edilmiştir:
- Python ve Node.js SDK'leri mevcut; ajan kodu doğrudan Python'da yazılır.
- Voice AI quickstart, agent builder ve playground ortamı sunuyor.
- Multimodality: ses, metin transkripsiyonu ve görüntü (vision) aynı framework'te.
- Turn detection, interruption handling, agent handoff — hepsi built-in.
- OpenAI, Google, Azure, AWS, xAI, Groq entegrasyonları ilk yüklemeyle geliyor.

### 1.2 Temel Mimari Akış

```
[Browser — Next.js]
       │  WebRTC (LiveKit SDK)
       ▼
[LiveKit Server / Cloud]
       │  Room üzerinden audio track
       ▼
[Voice Worker — FastAPI + LiveKit Python SDK]
       │  Audio stream
       ▼
[Cloudflare AI Gateway — WebSockets API]
       │  Persistent WebSocket
       ▼
[OpenAI Realtime API / Ses Modeli]
       │  Audio response
       └──────────────────────────────► [Browser]
```

**Bir Voice Worker**, LiveKit Room'a tam bir katılımcı olarak dahil olur. Hem ses alır hem ses üretir. Aynı Room'da birden fazla Worker olabilir (çoklu Membro senaryosu).

### 1.3 Voice Worker Kod Yapısı (Python)

```python
# Faz 4 — LiveKit Voice Worker
# Membro'nun sesli toplantı katılımcısı olarak çalışması

from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import openai, silero

async def entrypoint(ctx: JobContext):
    await ctx.connect()

    session = AgentSession(
        vad=silero.VAD.load(),           # Voice Activity Detection
        stt=openai.STT(),
        llm=openai.realtime.RealtimeModel(
            model="gpt-4o-realtime-preview",
            base_url="https://gateway.ai.cloudflare.com/v1/{account}/{gateway_id}/openai"
        ),
        tts=openai.TTS(),
    )

    await session.start(
        room=ctx.room,
        agent=MembroAgent(tenant_id=ctx.job.metadata["tenant_id"]),
        room_input_options=RoomInputOptions(noise_cancellation=True),
    )
```

---

## 2. Voice-to-Voice AI İşleme Hattı

### 2.1 Geleneksel STT→LLM→TTS Zincirinden Kaçınma

| Yaklaşım | Gecikme | Dezavantaj |
|---|---|---|
| STT → LLM → TTS | 2–4 saniye | Konuşma doğallığı bozuluyor |
| **OpenAI Realtime API (Native Audio)** | **~300ms** | ✅ Membro'nun tercihli yöntemi |

**OpenAI Realtime API**, ses girdisi alıp doğrudan ses çıktısı üretir — STT ve TTS adımları ortadan kalkar. Bu nedenle `gpt-4o-realtime-preview` modeli tercih edilir.

### 2.2 Cloudflare AI Gateway WebSockets Entegrasyonu

Realtime API, kalıcı bir WebSocket bağlantısı üzerinden çalışır. Cloudflare AI Gateway'in **Realtime WebSockets API** (Beta) desteği ile bu bağlantı gateway üzerinden şeffaf biçimde proxylenir:

```
Voice Worker → wss://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/openai/realtime
```

Bu sayede:
- Token kullanımı tenant bazında loglanır
- Rate limiting devreye girer
- Guardrails ses transkriptini kontrol eder

---

## 3. Ses Özellikleri ve Kontrol Mekanizmaları (LiveKit)

### 3.1 Interruption Handling (Araya Girme)

LiveKit, kullanıcı konuştuğunda ajanın sesini **anında keser**:
- **SpeechHandle API**: Ajanın aktif konuşmasını temsil eden handle objesi. `speech.interrupt()` ile anında durdurulabilir.
- **VAD (Voice Activity Detection)**: Silero VAD, kullanıcının ne zaman konuşmaya başladığını ~100ms içinde tespit eder.

```python
speech = session.say("Merhaba, nasıl yardımcı olabilirim?")

# Kullanıcı araya girerse
if user_started_speaking:
    speech.interrupt()
```

### 3.2 Instant Connect ve Preemptive Speech Generation

- **Instant Connect**: Kullanıcı Room'a bağlandığı anda ajan karşılama mesajını üretmeye başlar — bağlantı gecikme hissini ortadan kaldırır.
- **Preemptive Speech Generation**: Ajan, kullanıcının cümlesini tamamlamasını beklemeden muhtemel yanıtı önceden hazırlamaya başlayabilir.

### 3.3 Çoklu Ajan Turn-Taking

Aynı Room'da birden fazla Membro varken konuşma sırası şöyle yönetilir:

```
[Kullanıcı konuşuyor]
        │
        ▼
[LangGraph Supervisor — transkripsiyonu dinler]
        │  Pydantic Structured Output ile karar
        ▼
[next_speaker: "membro_sales" | "membro_support"]
        │
        ▼
[Seçilen Membro'nun Voice Worker'ı tetiklenir]
```

Supervisor, Faz 2'deki LangGraph grafiğinin sesli varyantıdır — State üzerinde `current_speaker` ve `transcript_buffer` alanları taşınır.

---

## 4. Toplantı Dinamikleri

### 4.1 Toplantı Yaşam Döngüsü

```
1. Kullanıcı "Toplantı Başlat" butonuna basar
2. Next.js → FastAPI: POST /meetings
3. FastAPI: LiveKit Access Token üretir (tenant_id + user_id ile imzalı)
4. FastAPI: İlgili Membro(lar) için Voice Worker job'ları dispatch eder
5. Browser: LiveKit WebRTC Room'a bağlanır
6. Toplantı boyunca transcript'ler PostgreSQL'e yazılır (tenant_id ile)
7. Toplantı biter → Supervisor: özet + action items oluşturur
8. Özet `MO_KnowledgeDocs` tablosuna eklenir → Faz 3 ingestion pipeline'ı başlar
```

### 4.2 Background Audio ve Ortam

LiveKit Agent Framework, arka plan sesi eklemeyi destekler (toplantı odası ambiyansı, müzik vb.) — Membro için kullanım alanı: bekleme müziği veya "düşünüyorum" sesi.

---

## 5. Desteklenen Model Alternatifleri

Membro'nun Voice Pipeline'ı sadece OpenAI'ye bağlı değildir. LiveKit şu ses modellerini destekler:

| Kategori | Modeller |
|---|---|
| **Realtime (Native Audio)** | OpenAI Realtime API (gpt-4o-realtime) |
| **STT** | OpenAI Whisper, Deepgram, Google STT, Azure STT |
| **TTS** | OpenAI TTS, ElevenLabs, Cartesia, Google TTS |
| **LLM** | OpenAI, Anthropic, Google Gemini, xAI, Groq |

Cloudflare AI Gateway tüm bu provider'ları desteklediği için pipeline değişikliği kod değişikliği gerektirmez — sadece Gateway konfigürasyonu güncellenir.

---

## 6. Performans Hedefleri

| Metrik | Hedef |
|---|---|
| İlk ses yanıt süresi (TTFS) | < 500ms |
| Interruption tepki süresi | < 100ms |
| Aynı anda açık WebRTC bağlantısı | 100+ (Faz 5'te yük testi) |
| Ses kalitesi | 16kHz / Opus codec |



## 2. Voice-to-Voice AI İşleme Hattı (Pipeline)
Toplantı doğallığını sağlamak için geleneksel STT (Sesten Metne) -> LLM -> TTS (Metinden Sese) zinciri kullanılmayacaktır, çünkü bu zincir 2-4 saniye arası gecikme yaratır.
* **Model:** Doğrudan ses alıp ses üretebilen **OpenAI Realtime API** (veya eşdeğeri multimodal modeller) kullanılacaktır.
* **Gateway Bağlantısı:** FastAPI üzerindeki Voice Worker, kullanıcının WebRTC'den gelen ses akışını (audio stream) alır, Cloudflare AI Gateway üzerinden geçirerek (loglama ve token takibi için) kalıcı bir WebSocket bağlantısıyla Realtime API'ye iletir.

## 3. Toplantı Dinamikleri ve Ajan Katılımı
Birden fazla Membro'nun aynı toplantıda yer alması senaryosu:
* **Turn-Taking (Söz Alma):** LangGraph Supervisor'ı, sesli toplantı anında devre dışı kalmaz; arka planda konuşulanları metin (transcript) olarak dinlemeye devam eder. Hangi ajanın cevap vermesi gerektiğine karar verip o ajanın "Voice Worker"ını tetikler.
* **VAD (Voice Activity Detection - Ses Aktivite Denetimi):** İnsan konuşurken ajanın susması (interruption handling) için Silero VAD veya WebRTC'nin dahili VAD algoritmaları uçta (edge/browser) çalıştırılacak, kullanıcı araya girdiğinde ajanın ses akışı anında kesilecektir.