# Mimari ve Teknik Kararlar Logu

Her önemli karar tarih ve gerekçesiyle buraya kaydedilir. Bir karar değişirse eski kayıt silinmez; üstüne yeni bir kayıt eklenir.

---

## [2026-03-06] StreamingResponse + DB Persistence: get_db_session ile taze session

**Karar:** `chat_stream` SSE endpoint'inde mesaj kalıcılığı için `Depends(get_db)` kaldırıldı; generator `finally` bloğunda `get_db_session(tenant_id=tenant_id)` ile taze session açılıyor.
**Gerekçe:** FastAPI dependency injection, route fonksiyonu döndüğünde (yani `StreamingResponse()` oluşturulup döndürüldüğünde) bağımlılıkları kapatır. Generator bu noktada henüz çalışmamıştır; `finally` bloğu stream tamamlandıktan sonra çalışır. Bu nedenle enjekte edilen session kapalı olur. `get_db_session` ise `@asynccontextmanager` ile `SET LOCAL app.current_tenant_id` RLS bağlamını da kurar.
**Alternatifler değerlendirildi:** `BackgroundTasks` (reply_content kapanımını gerektirir, lifecycle sorunu önceden çözülmüş — reddedildi), bare `AsyncSessionLocal()` (RLS SET LOCAL eksik, INSERT'ler policy ile engellenir — reddedildi).

---

## [2026-03-06] Message Timestamp Sıralaması: Python explicit datetime + 1ms offset

**Karar:** `_persist_messages` içinde user mesajı `datetime.now(timezone.utc)`, assistant mesajı `now + timedelta(milliseconds=1)` ile INSERT ediliyor.
**Gerekçe:** `server_default=func.now()` PostgreSQL'de aynı transaction içindeki tüm INSERT'lere aynı `now()` değerini atar. User ve assistant mesajı aynı transaction'da eklendiğinden `created_at` eşit olur ve ORDER BY sırası non-deterministik. 1ms offset ile kullanıcı mesajı her zaman asistan mesajından önce sıralanır.
**Alternatifler değerlendirildi:** Serial ID sütunu ekleme (migration gerektirir — ertelendi), flush arasındaki server `now()` farkı (aynı tx içinde PostgreSQL `now()` sabit — geçersiz), UUID v7 (zaman bazlı, implementasyon karmaşıklığı — reddedildi).

---



**Karar:** Frontend `apiFetch` tüm requestlere `X-Tenant-Slug` header'ını ekler; backend `/auth/login` ve `/auth/register` endpointleri `access_token`'ı hem cookie hem response body'e yazar.
**Gerekçe:** Backend `tenant_middleware` tenant'ı `X-Tenant-Slug` header'ından çözüyor. Frontend `http://testco.localhost`'tan `http://localhost:8000`'e istek attığında subdomain bilgisi kayboluyordu. `getTenantSlug()` helper'ı `window.location.hostname`'den slug'ı çıkarıp tüm requestlere ekler. İkinci sorun: backend token'ı sadece cookie'ye yazıyordu ama frontend `tokens.access_token` bekliyordu (localStorage auth flow); body'e de eklendi.
**Alternatifler değerlendirildi:** (1) Backend'e Host header'dan slug çıkarma — cross-origin isteklerde Host değişebilir ve güvensiz. (2) Frontend cookie'den okuma — SameSite=Lax cross-origin cookie bloğu nedeniyle çalışmaz.

---

## [2026-03-04] Faz 6 Frontend Design System Kararları

**Karar:** Tenant frontend uygulaması için kendi design token sistemi (Tailwind CSS custom properties), Framer Motion animasyonlar, Zustand UI state, TanStack Query server state ve SSE-tabanlı chat stream seçildi. shadcn/ui kullanılmıyor.
**Gerekçe:** 2026 UX/UI araştırması (Fuselab, JetBase, Smashing Magazine) dark mode + liquid glass + AI-first conversational UI trendlerini önce sıralıyor. shadcn/ui bileşen kırılganlığından kaçınmak ve design token kontrolünü tam elde tutmak için custom sistem tercih edildi. Spring-based animasyonlar (Framer Motion) liquid glass estetiğiyle uyumlu. SSE, FastAPI'nin native async streaming desteğiyle doğal uyum.
**Alternatifler değerlendirildi:** shadcn/ui (token override maliyeti yüksek — reddedildi), WebSocket chat (SSE'den karmaşık, tek yönlü akış için gereksiz — reddedildi), Redux (Zustand'dan ağır, UI state için fazla — reddedildi).

---

## [2026-03-04] Pytest asyncio Loop Scope: Session

**Karar:** `pyproject.toml`'a `asyncio_default_test_loop_scope = "session"` ve `asyncio_default_fixture_loop_scope = "session"` eklendi.
**Gerekçe:** SQLAlchemy `create_async_engine` modül seviyesinde oluşturuluyor; asyncpg pool'un bağlantıları tek bir event loop'a bağlı. Her test farklı loop kullansaydı "Future attached to different loop" RuntimeError'ı oluşuyordu.
**Alternatifler değerlendirildi:** function-scope (loop karışması — reddedildi), engine'i fixture içinde oluşturma (yüksek refactor maliyeti — reddedildi), session loop (seçildi).

---

## [2026-03-04] Auth Testi Tasarımı: X-Tenant-Slug Olmadan

**Karar:** JWT tip ve auth testlerinde `X-Tenant-Slug` header gönderilmiyor.
**Gerekçe:** Tenant middleware önce çalışıyor ve "tenant-a" test DB'de olmadığı için 404 dönüyor, auth middleware'e ulaşılmıyor. Auth izolasyon testi için tenant çözümlemesi gereksiz bağımlılık.
**Alternatifler değerlendirildi:** Test DB'ye tenant seed (karmaşık setup — reddedildi), X-Tenant-Slug kaldırılması (seçildi — tenant MW slug yoksa atlıyor).

---



**Karar:** Tüm tenant'lar tek veritabanında, row-level security ile izole edilecek.
**Gerekçe:** Operasyonel basitlik. Ayrı DB veya şema mimarilerine göre bakım maliyeti çok daha düşük.
**Alternatifler değerlendirildi:** Ayrı DB (reddedildi: aşırı karmaşık), Ayrı şema (reddedildi: migration yükü yüksek).

---

## [2026-03-02] AI Gateway: Cloudflare AI Gateway

**Karar:** Tüm LLM çağrıları doğrudan değil, Cloudflare AI Gateway üzerinden geçecek.
**Gerekçe:** Maliyet takibi, rate limiting, caching ve fallback tek noktadan yönetilecek.

---

## [2026-03-02] Ajan Orkestrasyonu: LangGraph + Supervisor Deseni

**Karar:** Supervisor agent merkezi koordinatör; alt ajanlar (Membro'lar) ona rapor verir.
**Gerekçe:** Sonsuz döngüleri önler, deterministik ajan seçimi için Structured Outputs kullanılır.

---

## [2026-03-02] Ses/Toplantı Altyapısı: WebRTC (LiveKit/Daily)

**Karar:** Gerçek zamanlı ses için LiveKit veya Daily tercih edilecek; OpenAI Realtime API ses modeli olarak kullanılacak.
**Gerekçe:** Managed WebRTC altyapısı ile operasyonel yük azaltılıyor.

---

## [2026-03-02] Tablo Adlandırma: MO_ Prefix + MO_Eventlog

**Karar:** Tüm PostgreSQL tabloları `MO_` prefix'i taşır (MO_Tenants, MO_Users, MO_Membros, ...). Uygulama geneli exception handling için `MO_Eventlog` tablosu eklendi.
**Gerekçe:** Prefix ile Membro'ya ait tablolar üçüncü parti araç tablolarından veya ilerideki eklentilerden kolayca ayrıştırılır. Merkezi bir event log tablosu; tüm servislerden (FastAPI, Voice Worker, LangGraph, ingestion) gelen hataların tek noktada sorgulanmasını sağlar.
**Alternatifler değerlendirildi:** Prefix'siz (reddedildi: isim çakışma riski), ayrı error schema (reddedildi: operasyonel karmaşıklık), Sentry-only (reddedildi: tenant bazlı sorgu yapılamıyor).
**Özel Not:** MO_Eventlog için RLS tenant_id NULL satırlara (sistem hataları) izin verir; bu satırları yalnızca Super Admin görebilir.

## [2026-03-03] Faz 5 — Rate Limiting: slowapi (Tenant Bazlı Key)

**Karar:** `slowapi` ile FastAPI middleware katmanında rate limiting uygulanır. Key fonksiyonu: `tenant_id` varsa tenant bazlı, yoksa IP.
**Gerekce:** Cloudflare AI Gateway'in kendi rate limiting'i var ama API katmanında da limit gerekli. Tek bir kötü tenant tüm sistemi yavaşlatmamalı.
**Alternatifler değerlendirildi:** Nginx rate limit (reddedildi: tenant bazlı yapamaz), sadece CF limiti (reddedildi: API layer korumsuz kalır).

---

## [2026-03-03] Faz 5 — Token Revocation: Bu Fazda Yok

**Karar:** Redis bloklist tabanlı token revocation bu fazda eklenmedi.
**Gerekce:** JWT tip doğrulama (refresh → access kullanımı engeli) bug sınıfını kapatıyor. Revocation listesi Redis bağımlılığı getiriyor ve Faz 1–5 kapsamı dışında. Faz 6+ için not düşüldü.
**Alternatifler değerlendirildi:** Redis blocklist (ileriye alındı), kısa JWT TTL (mevcut 60dk acceptable).

---

---

## [2026-03-02] Geliştirme Ortamı: Monorepo + Docker Compose

**Karar:** Tek repo (frontend + backend + infra), Docker Compose ile local geliştirme.
**Gerekçe:** Subdomain routing testleri için tüm servislerin aynı anda çalışması gerekiyor. Docker Compose bu koordinasyonu sağlar. Monorepo shared type tanımlamalarını kolaylaştırır.
**Alternatifler değerlendirildi:** Ayrı repolar (reddedildi: cross-repo bağımlılık yönetimi karmaşık), native kurulum (reddedildi: Milvus/Neo4j port çakışmaları).

---

## [2026-03-02] Milvus Multi-Tenancy: Partition Key Stratejisi Onaylandı

**Karar:** Binlerce tenant için Partition Key stratejisi kullanılacak (Database/Collection stratejisi değil).
**Gerekçe:** Database-level maks. 64 tenant limiti var. Collection-level binlerce koleksiyon demek — performans düşer. Partition Key, sınırsız tenant + otomatik routing + tek koleksiyon avantajı sunar.
**Alternatifler değerlendirildi:** Database-level (reddedildi: 64 tenant limiti), Collection-level (reddedildi: ölçekleme sorunu).

---

## [2026-03-02] LiveKit Python SDK Seçimi

**Karar:** Voice Worker'lar LiveKit Python SDK ile yazılacak. Daily.co alternatif olarak değerlendirildi ama seçilmedi.
**Gerekçe:** LiveKit'in Agents Framework'ü; VAD, STT, TTS, Realtime entegrasyonlarını, interruption handling'i ve agent handoff'u tek pakette sunuyor. Ayrıca LangGraph ile doğrudan entegrasyon daha kolay.
**Alternatifler değerlendirildi:** Daily.co (reddedildi: agent framework yetkinliği LiveKit kadar güçlü değil), Sıfırdan WebRTC (reddedildi: operasyonel yük çok yüksek).

---

## [2026-03-02] Faz 2 — MCP Transport: HTTP + SSE (Stateless Remote)

**Karar:** MCP sunucusu FastAPI sub-application olarak `/mcp` prefix'i altında mount edilir; transport HTTP + SSE.
**Gerekçe:** Aynı container'da çalışır, ek port açılmaz, Nginx üzerinden proxy geçişi doğaldır. Spec 2025-11-05 Streamable HTTP transport ile tam uyumlu.
**Alternatifler değerlendirildi:** Bağımsız process (reddedildi: operasyonel karmaşıklık), stdio transport (reddedildi: sadece CLI istemciler için uygun).

---

## [2026-03-02] Faz 2 — LangGraph Checkpointer: Geliştirmede MemorySaver, Üretimde PostgreSQL

**Karar:** `compile_graph()` fonksiyonu opsiyonel `checkpointer` parametresi alır. Geliştirmede `MemorySaver`, üretimde `langgraph-checkpoint-postgres` geçilir.
**Gerekçe:** Sıfır konfigürasyonla geliştirme deneyimi korunurken üretim kalıcılığı mevcut RLS-aware PostgreSQL bağlantısı üzerinden sağlanır; ekstra altyapı gerektirmez.
**Alternatifler değerlendirildi:** Redis checkpoint (reddedildi: ek bağımlılık), her zaman PostgreSQL (reddedildi: lokal geliştirmeye sürtünme ekler).

---

## [2026-03-02] Faz 2 — CF AI Gateway Auth: openai_api_key=cf_aig_token

**Karar:** `ChatOpenAI(openai_api_key=settings.cf_aig_token)` ile LangChain SDK'ya CF token verilir. SDK bu değeri `Authorization: Bearer {token}` header'ı olarak gönderir; CF Gateway bu header'ı kendi auth mekanizması olarak kabul eder ve provider key'i CF Vault'tan alır.
**Gerekçe:** CF Unified Billing kullanılıyor — provider API key'leri uygulama kodunda/env'de olmaz, CF Dashboard'da saklanır. SDK validation'ı bypass etmek için önceden `llm_sdk_placeholder_key="cf-managed"` kullanılıyordu ancak bu gerçek Bearer token yerine `cf-managed` gönderiyordu. Doğrudan `cf_aig_token` vermek hem auth header'ı hem de SDK validasyonunu tek hamlede çözdü.
**Alternatifler değerlendirildi:** `default_headers` ile `cf-aig-authorization` manuel ekle (reddedildi: SDK `Authorization` header'ını ayrıca `cf-managed` key ile gönderiyordu, çakışma oluyordu), provider key'i `.env`'e koy (reddedildi: Unified Billing amacına aykırı).

---

## [2026-03-03] Faz 4 — LiveKit: Self-Hosted (docker-compose) tercih edildi

**Karar:** LiveKit Cloud yerine `livekit/livekit-server:v1.7` imajı docker-compose servis olarak eklendi.
**Gerekçe:** Local geliştirmede dış servise bağımlılık ortadan kalkar; `devkey/devsecret123456` ile zero-config başlatılır. Production'da LiveKit Cloud veya self-hosted Kubernetes'e geçiş sadece `LIVEKIT_URL/API_KEY/API_SECRET` env değişkenleri ile yapılır — kod değişikliği gerekmez.
**Alternatifler değerlendirildi:** LiveKit Cloud (reddedildi: free tier limit, local geliştirme için gereksiz), Daily.co (reddedildi: Python SDK eksik, LiveKit'in LangGraph/MCP entegrasyonu daha güçlü).

---

## [2026-03-03] Faz 4 — Ses Pipeline: OpenAI Realtime API (Native Audio)

**Karar:** STT→LLM→TTS zinciri yerine OpenAI Realtime API (`gpt-4o-realtime-preview`) kullanılır; LiveKit Agents framework RealtimeModel olarak yapılandırılır.
**Gerekçe:** Geleneksel zincir 2–4 saniyelik gecikme yaratır. Realtime API native audio modunda ~300ms TTFS sağlar; konuşma doğallığı korunur. Silero VAD client-side interruption handling için ayrıca eklendi.
**Alternatifler değerlendirildi:** Deepgram STT + Anthropic LLM + ElevenLabs TTS (reddedildi: driver sayısı artıyor, gecikme birikimi), Groq Whisper STT (reddedildi: Realtime API var iken gereksiz ara adım).

---

## [2026-03-03] Faz 4 — Voice Worker Dispatch: Hata Toleranslı Mimari

**Karar:** `POST /meetings/` endpoint'i LiveKit dispatch başarısız olsa bile 201 döner; token ve meeting_id her zaman oluşturulur.
**Gerekçe:** Voice Worker çalışmıyor olsa (geliştirme, restart) toplantı API'si kırılmasın. Worker dispatch ayrı `try/except` bloğuna alındı, log uyarısı bırakır. Test ortamında LiveKit olmadan 10/10 test geçmesi bu kararın doğruluğunu kanıtladı.
**Alternatifler değerlendirildi:** Dispatch başarısız olursa 503 dön (reddedildi: test ve geliştirme deneyimini bozar), worker'ı API içinde doğrudan asyncio task olarak çalıştır (reddedildi: API process'ini kirletir, ayrı servis mimarisine aykırı).
