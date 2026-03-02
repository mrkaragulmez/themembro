# Faz 2: AI İstek Yönetimi ve Ajan Orkestrasyonu

> **Son güncelleme:** 2026-03-02 — Cloudflare AI Gateway ve LangGraph resmi dokümanları taranarak güçlendirildi.

---

## 1. İstek Ağ Geçidi (Cloudflare AI Gateway)

Sistemdeki tüm LLM çağrıları — ister Supervisor ajan, ister bir Membro, ister ses pipeline'ı olsun — Cloudflare AI Gateway üzerinden geçer. Hiçbir bileşen LLM provider'larına doğrudan bağlanmaz.

### 1.1 Desteklenen Provider'lar (Güncel Liste)

Cloudflare AI Gateway, 20'den fazla provider'ı OpenAI uyumlu Unified API veya provider-native formatıyla destekler:

| Kategori | Provider'lar |
|---|---|
| **Ana LLM'ler** | OpenAI, Anthropic, Google AI Studio, Google Vertex AI, Azure OpenAI, Mistral AI, xAI (Grok) |
| **Hızlı Çıkarım** | Groq, Cerebras, DeepSeek |
| **Ses/Müzik** | ElevenLabs, Cartesia, Deepgram |
| **Görüntü Üretimi** | Fal AI, Ideogram, Replicate |
| **Çoklu Model Proxy** | OpenRouter, Parallel |
| **Arama** | Perplexity, HuggingFace |
| **Cloudflare Native** | Workers AI |
| **AWS** | Amazon Bedrock |

**Membro Stack için birincil provider'lar:** OpenAI, Anthropic (Claude), Groq (hızlı çıkarım), Deepgram (STT), ElevenLabs (TTS).

### 1.2 Temel Özellikler

#### Caching (Önbellekleme)
* `cf-aig-cache-ttl` header'ı veya dashboard üzerinden TTL ayarlanır.
* Aynı prompt hash'ine sahip sorgular LLM'e iletilmeden önbellekten döndürülür.
* Membro için kullanım alanı: SSS niteliğindeki bilgi bankası sorguları, değişmeyen sistem promptları.

#### Rate Limiting
* Gateway (tüm tenant'lar) ve tenant bazında ayrı ayrı limitler tanımlanabilir.
* Aşım durumunda 429 döner; FastAPI katmanında bunu yakalayan bir retry + exponential backoff mekanizması kurulur.

#### Dynamic Routing (Beta)
* Birden fazla provider arasında kural tabanlı yönlendirme: "önce Groq dene, 500ms içinde cevap gelmezse OpenAI'ye falla back et."
* JSON konfigürasyonuyla tanımlanır — kod değişikliği gerekmez.
* Membro için kullanım alanı: düşük gecikme gerektiren ses pipeline'larında önce Groq, fallback olarak OpenAI.

#### Guardrails (Beta)
* Gateway katmanında LLM input/output'larını content policy açısından filtreler.
* Desteklenen model tipleri: text generation, chat completions.
* Membro için kullanım alanı: prompt injection, zararlı içerik, PII sızıntısı tespiti. Faz 2'de temel kural seti devreye alınır.

#### Data Loss Prevention (DLP) (Beta)
* Çıkan yanıtlarda kredi kartı numaraları, TC kimlik numaraları gibi hassas veri pattern'lerini tespit eder ve maskeler veya bloklar.
* Membro için kullanım alanı: müşteri verilerinin yanlışlıkla modelden sızmasını önleme.

#### WebSockets API (Beta)
* OpenAI Realtime API gibi persistent WebSocket bağlantısı gerektiren ses modelleri için özel destek.
* `Realtime WebSockets API` ve `Non-realtime WebSockets API` olarak iki mod mevcuttur.
* **Kritik:** Faz 4'te LiveKit Voice Worker, ses akışını OpenAI Realtime'a iletirken bu endpoint üzerinden geçecek — loglama ve token takibi için zorunlu.

#### BYOK — Bring Your Own Key (Beta)
* Provider API anahtarları Cloudflare'ın kendi secret store'unda şifrelenerek saklanabilir.
* Membro'nun uygulama kodunda hiçbir zaman `OPENAI_API_KEY` gibi bir değer bulunmaz.

#### Unified Billing
* Tüm provider'lara yapılan harcamalar tek bir Cloudflare dashboard'undan izlenir.
* Tenant bazlı etiketleme (`cf-aig-metadata` header'ı) ile şirket başına maliyet analizi yapılabilir.

### 1.3 Entegrasyon Mimarisi

```
[FastAPI / Voice Worker]
         │
         ▼
  Cloudflare AI Gateway
  ┌──────────────────────────┐
  │ • Rate Limiting           │
  │ • Guardrails (input)      │
  │ • DLP (output)            │
  │ • Caching                 │
  │ • Dynamic Routing         │
  │ • Logging & Metrics       │
  └──────────────────────────┘
         │
    ┌────┴──────────────────┐
    ▼                       ▼
  OpenAI               Anthropic / Groq / ...
```

HTTP header'ları ile tenant ve membro metadata'sı gönderilir:
```
cf-aig-metadata: {"tenant_id": "...", "membro_id": "...", "conversation_id": "..."}
```

---

## 2. Ajan Orkestrasyonu (LangGraph Mimarisi)

### 2.1 Genel Felsefe

LangGraph, ajan akışını bir **state machine (durum makinesi)** olarak modelleyen bir orkestrasyon framework'üdür. Her düğüm (node) bir işlev; her kenar (edge) bir karar. Bu yapı sayesinde:
- Sonsuz döngüler `recursion_limit` ile önlenir
- Her adımın durumu **checkpoint** olarak kalıcı hale getirilir
- Hata durumunda grafiğin herhangi bir noktasından **resume** edilir (Durable Execution)
- Geçmiş state'lere dönülüp farklı bir path denenebilir (Time Travel)

### 2.2 Supervisor + Subgraph Deseni

```
Kullanıcı Mesajı
      │
      ▼
┌─────────────┐
│  Supervisor  │  ← "State" objesini yönetir
│    Agent    │    messages, next_agent, metadata
└──────┬──────┘
       │  Pydantic Structured Output ile ajan seçimi
  ┌────┼─────────────┐
  ▼    ▼             ▼
[Membro A]  [Membro B]  [Membro C]
(Sales)    (Support)  (Research)
  │
  ▼
[Knowledge Subgraph]  ← Milvus + Neo4j RAG
```

**Supervisor** asla doğrudan LLM çıktısı üretmez; görevi Pydantic modeli ile tanımlı bir `{next_agent: "membro_a" | "membro_b" | "__end__"}` kararıdır.

### 2.3 State Tasarımı

```python
from typing import Annotated, Literal
from langgraph.graph.message import add_messages
from pydantic import BaseModel

class MembroState(BaseModel):
    messages: Annotated[list, add_messages]
    tenant_id: str
    membro_id: str
    conversation_id: str
    next_agent: Literal["membro_a", "membro_b", "__end__"] | None = None
    retrieval_context: str = ""
    turn_count: int = 0
```

### 2.4 Güvenlik ve Kontrol Mekanizmaları

| Mekanizma | Değer | Açıklama |
|---|---|---|
| `recursion_limit` | 15 | Supervisor-ajan paslaşma maksimumu |
| `interrupt_before` | `["tool_call"]` | Araç çağrısı öncesi insan onayı (opsiyonel) |
| Checkpoint Store | PostgreSQL (`langgraph-checkpoint-postgres`) | State kalıcılığı ve resume |
| Timeout | 30s per node | Hung ajan önleme |

### 2.5 LangGraph Yetenekleri (Kullanılacak Özellikler)

- **Persistence:** Her konuşma adımı checkpoint olarak PostgreSQL'e yazılır. Sunucu yeniden başlasa da konuşma devam eder.
- **Streaming:** Supervisor kararları ve ajan çıktıları SSE (Server-Sent Events) ile frontend'e token token iletilir.
- **Interrupts:** Tenant Admin onayı gerektiren yüksek riskli tool çağrıları (örn. CRM'e yazma) `interrupt_before` ile durdurulur.
- **Subgraphs:** Bilgi bankası retrieval'ı ayrı bir subgraph olarak modülerize edilir — ana grafikten bağımsız test edilebilir.
- **LangSmith Observability:** Her run otomatik olarak LangSmith'e trace edilir (Faz 5'te detaylandırılır).

---

## 3. Skill ve Tool Yönetimi (MCP)

### 3.1 MCP Nedir?

Model Context Protocol (MCP, spec: 2025-11-05), AI uygulamalarını dış sistemlere bağlamak için Anthropic tarafından önerilen ve artık endüstri standardı haline gelen açık kaynaklı bir protokoldür. "AI için USB-C" olarak tanımlanır: her AI agent aynı standartta araçlara, veri kaynaklarına ve workflow'lara bağlanabilir.

### 3.2 MCP Mimarisi

```
[Membro AI Agent]  ←→  [MCP Client]  ←→  [MCP Server]  ←→  [Dış Sistem]
                                                              (CRM, DB, API...)
```

- **MCP Server:** Araçları (tools), kaynakları (resources) ve prompt şablonlarını açığa çıkaran servis.
- **MCP Client:** Agent içinde çalışan; server'ı keşfeden ve çağıran bileşen.
- **Remote MCP Server:** HTTP + SSE veya WebSocket üzerinden erişilen sunucu (spec 2025-11-05 ile resmileşti).

### 3.3 Membro'da MCP Kullanımı

Her Membro'nun yetenekleri veritabanında JSON olarak saklanır:

```json
{
  "membro_id": "uuid",
  "tools": [
    { "name": "search_knowledge_base", "server": "internal://kb-server" },
    { "name": "create_crm_contact",    "server": "https://crm.themembro.com/mcp" },
    { "name": "send_email",            "server": "https://email.themembro.com/mcp" }
  ]
}
```

Çalışma anında bu JSON, Cloudflare AI Gateway üzerinden System Prompt'a dinamik olarak enjekte edilir.

### 3.4 Güvenlik

- Her MCP server çağrısı `tenant_id` içeren bir JWT ile kimlik doğrulamasından geçer.
- Tool sonuçları Guardrails katmanından geçirilir (PII sızıntısı kontrolü).
- MCP server'lar tenant-agnostic'tir; izolasyon JWT + tool-level RBAC ile sağlanır.