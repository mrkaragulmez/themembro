# Membro: Mimari Tasarım Dokümanı (ADD)

**Proje Özeti:** Agentic AI çözümleriyle ziyaretçilere dijital ortamda iş geliştirme arenası sunan, multi-tenant B2B SaaS platformu.

> **Son güncelleme:** 2026-03-02 — Crawl4AI tabanlı araştırma döngüsüyle güçlendirildi.

---


## Temel Teknolojiler (Tech Stack)

| Katman | Teknoloji | Notlar |
|---|---|---|
| **Frontend** | Next.js 16.1 + TypeScript + Tailwind CSS | App Router, RSC |
| **Backend** | FastAPI (Python 3.12+) | Async-first, Pydantic v2 |
| **Veritabanı** | PostgreSQL 16 — Shared DB + Shared Schema + RLS | |
| **Vektör DB** | Milvus 2.6.x | Partition Key stratejisi |
| **Graph DB** | Neo4j | GraphRAG pipeline |
| **Altyapı & Proxy** | Cloudflare DNS + Nginx | Wildcard subdomain |
| **AI Gateway** | Cloudflare AI Gateway | Rate limit, cache, fallback, guardrails |
| **AI Orkestrasyon** | LangGraph | Supervisor + subgraph deseni |
| **Ajan Yetenekleri** | MCP (Model Context Protocol, spec 2025-11-05) | |
| **Ses/Toplantı** | LiveKit + OpenAI Realtime API | WebRTC tabanlı |

---

## Faz 1: SaaS Temelleri ve İzolasyon

### 1. Multi-Tenant Veritabanı Mimarisi

Tüm tenant verileri tek PostgreSQL instance üzerinde tutulur. İzolasyon uygulama katmanında değil, veritabanı katmanında sağlanır.

#### Row-Level Security (RLS) Tasarımı

Her tabloya `tenant_id UUID NOT NULL` kolonu eklenir. RLS politikaları şu şablonla oluşturulur:

```sql
-- Tabloyu RLS'e zorla (bypass'ı engelle)
ALTER TABLE public.MO_Membros ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.MO_Membros FORCE ROW LEVEL SECURITY;

-- SELECT politikası: sadece kendi tenant'ının satırlarını gör
CREATE POLICY tenant_isolation_select ON public.MO_Membros
  FOR SELECT
  USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- INSERT politikası: sadece kendi tenant_id'si ile ekleyebilir
CREATE POLICY tenant_isolation_insert ON public.MO_Membros
  FOR INSERT
  WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

FastAPI middleware'inde her request başında `SET LOCAL app.current_tenant_id = '{tenant_id}'` çalıştırılır. tenant_id asla request body'den alınmaz — JWT claim'den okunur.

#### Kritik Güvenlik Notu

`FORCE ROW LEVEL SECURITY` zorunludur. Bu kural olmadan tablo sahibi olan PostgreSQL kullanıcısı (örn. `superuser`) politikaları bypass edebilir. Uygulama DB kullanıcısı asla `superuser` rolünde çalışmamalıdır.

#### Temel Tablo Şeması (Özet)

Tüm tablolar `MO_` prefix'ini taşır. `MO_Eventlog` hariç tüm tablolara RLS uygulanır.

```
MO_Tenants          → id, name, slug, plan, created_at
MO_Users            → id, tenant_id, email, role, jwt_sub
MO_Membros          → id, tenant_id, name, system_prompt, tools_json
MO_Conversations    → id, tenant_id, membro_id, user_id, started_at
MO_Messages         → id, tenant_id, conversation_id, role, content, created_at
MO_KnowledgeDocs    → id, tenant_id, membro_id, title, content, status
MO_RefreshTokens    → id, tenant_id, user_id, token_hash, expires_at, created_at
MO_Eventlog         → id, tenant_id (nullable), service, level, code, message,
                       stack_trace, request_id, user_id (nullable), created_at
```

> `MO_Eventlog` tenant_id'sini opsiyonel tutar çünkü sistem seviyesi hatalar tenant bağlamı kurulmadan önce fırlatılabilir.

---

### 2. Yönlendirme ve Subdomain Yönetimi (`*.themembro.com`)

#### DNS Katmanı

* Cloudflare üzerinden `*.themembro.com` için **"DNS Only" (Gri Bulut)** wildcard A kaydı oluşturulur.
* Cloudflare Proxy (turuncu bulut) aktif edilmez — Nginx TLS termination yapacağı için Cloudflare'ın TLS'i araya girmemelidir.

#### SSL/TLS: Wildcard Sertifika

Certbot DNS-01 challenge ile wildcard sertifika alınır (HTTP-01 challenge `*.themembro.com` için çalışmaz):

```bash
certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials /etc/cloudflare/credentials.ini \
  -d "*.themembro.com" -d "themembro.com"
```

Sertifika yenileme cron veya systemd timer ile otomatikleştirilir.

#### Nginx Konfigürasyonu

```nginx
server {
    listen 443 ssl;
    server_name ~^(?P<tenant>[^.]+)\.themembro\.com$;

    ssl_certificate     /etc/letsencrypt/live/themembro.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/themembro.com/privkey.pem;

    location / {
        proxy_pass         http://fastapi_backend;
        proxy_set_header   X-Tenant-Slug $tenant;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
    }
}
```

FastAPI middleware `X-Tenant-Slug` header'ını okuyarak `MO_Tenants` tablosundan `tenant_id`'yi resolve eder ve `app.current_tenant_id` session değişkenini set eder.

---

### 3. Kimlik Doğrulama (Auth) ve Roller

#### JWT Yapısı

```json
{
  "sub": "user-uuid",
  "tenant_id": "tenant-uuid",
  "tenant_slug": "acme",
  "role": "tenant_admin",
  "exp": 1740000000
}
```

* Çerezler `Domain=.themembro.com; Secure; HttpOnly; SameSite=Lax` ile set edilir.
* Bu yapı tüm subdomain'lerde (`acme.themembro.com`, `beta.themembro.com`) geçerli olmasını sağlar.
* `tenant_id` **her zaman JWT'den okunur** — URL parametresi, request body veya header'dan alınmaz.
* Token yenileme (refresh token) ayrı bir `MO_RefreshTokens` tablosunda tenant_id ile saklanır, RLS ile korunur.

#### Rol Matrisi

| Yetki | Super Admin (Membro Ops) | Tenant Admin | Tenant User |
|---|---|---|---|
| Yeni tenant oluşturma | ✅ | ❌ | ❌ |
| Membro yaratma/silme | ✅ | ✅ | ❌ |
| Tool/skill atama | ✅ | ✅ | ❌ |
| Bilgi bankası yönetimi | ✅ | ✅ | ❌ |
| Ajan ile konuşma | ✅ | ✅ | ✅ |
| Toplantı başlatma | ✅ | ✅ | ✅ |
| Fatura/plan görüntüleme | ✅ | ✅ | ❌ |

---

### 4. Uygulama Geneli Exception Handling (MO_Eventlog)

Tüm servisler (FastAPI, Voice Worker, LangGraph node'ları) yakaladıkları exception'ları doğrudan `MO_Eventlog` tablosuna yazar. Bu sayede hata yönetimi merkezi, tenant izole ve sorgulanabilir hale gelir.

#### Tablo Şeması

```sql
CREATE TABLE public.MO_Eventlog (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID REFERENCES public.MO_Tenants(id) ON DELETE SET NULL,  -- nullable
    user_id      UUID REFERENCES public.MO_Users(id) ON DELETE SET NULL,    -- nullable
    service      VARCHAR(64)  NOT NULL,  -- 'api', 'voice_worker', 'langgraph', 'ingestion'
    level        VARCHAR(16)  NOT NULL,  -- 'ERROR', 'WARNING', 'CRITICAL', 'INFO'
    code         VARCHAR(64),            -- 'RLS_VIOLATION', 'LLM_TIMEOUT', 'MCP_CALL_FAILED', ...
    message      TEXT         NOT NULL,
    stack_trace  TEXT,
    request_id   UUID,                   -- FastAPI request context'i
    metadata     JSONB,                  -- ek bağlam: model adı, token sayısı vb.
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Performans için index'ler
CREATE INDEX idx_eventlog_tenant   ON public.MO_Eventlog (tenant_id, created_at DESC);
CREATE INDEX idx_eventlog_level    ON public.MO_Eventlog (level, created_at DESC);
CREATE INDEX idx_eventlog_service  ON public.MO_Eventlog (service, created_at DESC);
CREATE INDEX idx_eventlog_code     ON public.MO_Eventlog (code) WHERE code IS NOT NULL;
```

#### RLS Politikası (MO_Eventlog'a Özel)

`MO_Eventlog` diğer tablulardan farklı bir RLS stratejisi izler:
- `tenant_id` dolu satırlar → sadece ilgili tenant görür
- `tenant_id` NULL satırlar (sistem hataları) → sadece Super Admin görür

```sql
ALTER TABLE public.MO_Eventlog ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.MO_Eventlog FORCE ROW LEVEL SECURITY;

-- Tenant kendi loglarını görür; sistem loglarını (tenant_id IS NULL) göremez
CREATE POLICY eventlog_tenant_read ON public.MO_Eventlog
  FOR SELECT
  USING (
    tenant_id = current_setting('app.current_tenant_id')::uuid
  );

-- Yazma: uygulama her zaman yazabilir (service account rolü ile)
CREATE POLICY eventlog_service_write ON public.MO_Eventlog
  FOR INSERT
  WITH CHECK (true);  -- service account bu policy'yi kullanır
```

#### FastAPI Global Exception Handler

```python
# backend/app/core/exception_handler.py
# Faz 1 — Uygulama geneli exception handler; tüm yakalanmamış hataları MO_Eventlog'a yazar

from fastapi import Request
from fastapi.responses import JSONResponse
from app.db import get_db_session
import traceback, uuid

async def global_exception_handler(request: Request, exc: Exception):
    tenant_id  = getattr(request.state, "tenant_id",  None)
    user_id    = getattr(request.state, "user_id",    None)
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    async with get_db_session() as db:
        # RLS bypass: service account kullanılarak yazılır
        await db.execute(
            """
            INSERT INTO public.MO_Eventlog
                (tenant_id, user_id, service, level, code, message, stack_trace, request_id, metadata)
            VALUES
                (:tenant_id, :user_id, 'api', 'ERROR', :code, :message, :stack, :req_id, :meta)
            """,
            {
                "tenant_id":  tenant_id,
                "user_id":    user_id,
                "code":       type(exc).__name__,
                "message":    str(exc),
                "stack":      traceback.format_exc(),
                "req_id":     request_id,
                "meta":       {"path": str(request.url), "method": request.method},
            }
        )

    return JSONResponse(status_code=500, content={"error": "internal_server_error", "request_id": request_id})
```

App bağlama ekleme:
```python
# backend/app/main.py
app.add_exception_handler(Exception, global_exception_handler)
```

#### Standart Hata Kodları (`code` alanı)

| Kod | Kaynak | Açıklama |
|---|---|---|
| `RLS_VIOLATION` | FastAPI middleware | Tenant izolasyonu ihlal girişimi |
| `JWT_INVALID` | Auth middleware | Geçersiz / süresi dolmuş token |
| `LLM_TIMEOUT` | LangGraph node | LLM çağrısı zaman aşımı |
| `LLM_RATE_LIMITED` | AI Gateway | Rate limit aşımı |
| `MCP_CALL_FAILED` | MCP client | Tool/skill çağrısı başarısız |
| `MILVUS_FILTER_MISSING` | Bilgi bankası | tenant_id filtresi eksik sorgu |
| `VOICE_WORKER_CRASH` | LiveKit worker | Voice session beklenmedik kapanma |
| `INGESTION_FAILED` | Faz 3 pipeline | Doküman işleme hatası |

---

### 5. Geliştirme Ortamı

**Karar:** Monorepo + Docker Compose.

```
membro/
├── frontend/        # Next.js 16.1
├── backend/         # FastAPI
├── infra/           # Nginx config, Dockerfiles
├── docker-compose.yml
├── docs/            # Mimari dokümanlar
└── memory/          # Memory yönetimi (00, 01, 02, 03)
```

`docker-compose.yml` servisleri: `postgres`, `milvus`, `neo4j`, `backend`, `frontend`, `nginx`.

Local'de `*.localhost` veya `/etc/hosts` ile subdomain simülasyonu yapılır (`acme.localhost` → Nginx → FastAPI).