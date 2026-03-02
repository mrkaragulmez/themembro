# Mimari ve Teknik Kararlar Logu

Her önemli karar tarih ve gerekçesiyle buraya kaydedilir. Bir karar değişirse eski kayıt silinmez; üstüne yeni bir kayıt eklenir.

---

## [2026-03-02] Multi-Tenant Strateji: Shared DB + RLS

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

---

_Yeni kararlar bu dosyanın altına eklenir._

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
