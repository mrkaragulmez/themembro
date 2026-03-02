# Faz 3: Bilgi Bankası (Knowledge Base), Hafıza Yönetimi ve GraphRAG

> **Son güncelleme:** 2026-03-02 — Milvus 2.6.x resmi multi-tenancy dokümantasyonu taranarak güçlendirildi.

Bu faz, ajanların (Membro'ların) şirket kurallarını, geçmiş deneyimlerini ve operasyonel verileri sadece metinsel benzerlik (vektör) üzerinden değil, anlamsal ilişkiler (graf) üzerinden hatırlamasını sağlar.

---

## 1. Temel Veritabanı Altyapısı

| Sistem | Rol | Teknoloji |
|---|---|---|
| **Vektör DB** | Embedding benzerlik araması | Milvus 2.6.x |
| **Graf DB** | Varlık ilişki ağı (Knowledge Graph) | Neo4j 5.x |
| **İlişkisel DB** | Doküman metadata, erişim kontrolü | PostgreSQL (RLS ile korumalı) |

---

## 2. Milvus Multi-Tenancy Stratejisi

Milvus 2.6.x, 4 farklı multi-tenancy düzeyini destekler. Her birinin trade-off'larını anlayıp **Membro için doğru stratejiyi seçmek kritiktir.**

### Strateji Karşılaştırması

| Strateji | İzolasyon | Ölçeklenebilirlik | Esneklik | Membro Uygunluğu |
|---|---|---|---|---|
| **Database-level** | ⭐⭐⭐⭐ en güçlü | Maks. 64 tenant | Her tenant farklı şema | ❌ (tenant limiti yetersiz) |
| **Collection-level** | ⭐⭐⭐⭐ güçlü | Yüzlerce tenant | Ayrı koleksiyon | ⚠️ (binlerce tenant için ağır) |
| **Partition-level** | ⭐⭐⭐ orta | Binlerce partition | Manuel yönetim | ⚠️ (yönetim kompleks) |
| **Partition Key** | ⭐⭐ mantıksal | **Sınırsız tenant** | Tek koleksiyon, otomatik routing | ✅ **SEÇİLEN STRATEJI** |

### Karar: Partition Key Stratejisi

Membro potansiyel olarak binlerce B2B tenant barındıracağı için **Partition Key** stratejisi seçilmiştir.

```python
from pymilvus import MilvusClient, DataType

client = MilvusClient(uri="http://localhost:19530")

schema = client.create_schema()
schema.add_field("id",          DataType.INT64,    is_primary=True, auto_id=True)
schema.add_field("tenant_id",   DataType.VARCHAR,  max_length=64, is_partition_key=True)
schema.add_field("membro_id",   DataType.VARCHAR,  max_length=64)
schema.add_field("content",     DataType.VARCHAR,  max_length=8192)
schema.add_field("embedding",   DataType.FLOAT_VECTOR, dim=1536)

client.create_collection(
    collection_name="knowledge_base",
    schema=schema,
    num_partitions=64  # tenant'lar otomatik hash ile dağıtılır
)
```

**Güvenlik zorunluluğu:** Tüm aramalar `filter="tenant_id == '{tenant_id}'"` ile yapılmalıdır. Bu filtre olmayan hiçbir sorgu üretim ortamında çalıştırılamaz.

```python
results = client.search(
    collection_name="knowledge_base",
    data=[query_embedding],
    filter=f"tenant_id == '{tenant_id}'",  # ZORUNLU
    limit=5,
    output_fields=["content", "membro_id"]
)
```

---

## 3. Veri Yutma ve İşleme Hattı (Ingestion Pipeline)

Yeni bir doküman yüklendiğinde veya bir toplantı/görev tamamlandığında sistem şu akıştan geçer:

```
[Ham Doküman / Toplantı Transkripti]
         │
         ▼
  1. Chunking (Parçalama)
     LangChain RecursiveCharacterTextSplitter
     chunk_size=512, overlap=64
         │
         ▼
  2. Entity Extraction (Varlık Çıkarımı)
     Cloudflare AI Gateway → Claude 3.5 Sonnet
     Output: {nodes: [...], edges: [...]}
         │
         ├──────────────────────────────────┐
         ▼                                  ▼
  3a. Embedding Üretimi               3b. Graf Kaydı
      OpenAI text-embedding-3-small        Neo4j
      via Cloudflare AI Gateway            Düğümler ve ilişkiler
         │                                 tenant_id property eklenerek
         ▼
  4. Milvus'a Yazma
     partition_key = tenant_id
```

### Entity Extraction Prompt Şablonu

```
Aşağıdaki metindeki varlıkları ve ilişkileri JSON formatında çıkar.
Metin: {chunk}

Çıktı formatı:
{
  "nodes": [
    {"id": "...", "type": "Person|Company|Project|Product", "name": "..."}
  ],
  "edges": [
    {"from": "...", "to": "...", "relation": "MANAGES|DEVELOPS|DEPENDS_ON|..."}
  ]
}
```

---

## 4. Multi-Tenant Veri İzolasyonu (Kritik Güvenlik)

### Milvus İzolasyonu

* **Partition Key = tenant_id** → Milvus, aynı hash grubundaki tenant'ları aynı fiziksel partition'a yazar; ancak sorgular daima `filter` ile sınırlandırılır.
* Unit test zorunluluğu: A tenant'ının embedding'lerini B tenant'ının `tenant_id` filter'ı ile aramanın sıfır sonuç döndürdüğü test edilir.

### Neo4j İzolasyonu

Her düğüm ve ilişkiye `tenant_id` property zorunlu olarak eklenir:

```cypher
// Doğru — tenant_id ile yazma
CREATE (p:Person {name: $name, tenant_id: $tenant_id})

// Zorunlu constraint
CREATE CONSTRAINT person_tenant_id
  IF NOT EXISTS FOR (p:Person) REQUIRE p.tenant_id IS NOT NULL;
```

Tüm sorgular `WHERE n.tenant_id = $tenant_id` ile başlar.

---

## 5. Hafıza Hiyerarşisi

| Düzey | Kapsam | Etiket | Erişim |
|---|---|---|---|
| **Şirket Geneli (Global)** | Ürün dokümanları, şirket politikaları | `membro_id: "global"` | Tüm ajanlar |
| **Ajan Özel (Local)** | Toplantı özetleri, çalışanın öğrendikleri | `membro_id: "{agent_id}"` | Sadece o ajan + Supervisor |
| **Geçici (Ephemeral)** | Aktif konuşma bağlamı | LangGraph State | Sadece o konuşma |

LangGraph'ın **Memory** özelliği (`add-memory`) ile konuşmalar arası ajan hafızası state'e bağlanır.

---

## 6. Retrieval ve Çıkarım Akışı (RAG Pipeline)

```
Ajan sorusu: "Acme Şirketi'nde kim proje müdürü?"
         │
         ▼
1. Embedding oluştur (OpenAI text-embedding-3-small)
         │
         ▼
2. Milvus Araması (tenant_id filtreli)
   → Top-K: ["Ali Yılmaz — proje müdürü", "Q4 Roadmap.pdf", ...]
         │
         ▼
3. Neo4j Genişletme
   MATCH (p:Person {tenant_id: $tid})-[r]->(n)
   WHERE p.name IN $found_entities
   RETURN p, r, n LIMIT 20
         │
         ▼
4. Bağlam Birleştirme
   [Vektör Metinleri] + [Graf İlişkileri] → Zengin Context String
         │
         ▼
5. LLM Çağrısı (Cloudflare AI Gateway üzerinden)
   System Prompt + Zengin Context + Kullanıcı Sorusu
         │
         ▼
Yanıt: "Acme'de proje müdürü Ali Yılmaz. Q4'te Omega projesini yönetiyor."
```

---

## 7. LangGraph Memory Entegrasyonu

LangGraph'ın `langgraph-checkpoint-postgres` paketi kullanılarak konuşmalar kalıcı hale getirilir:

```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:pass@localhost/membro_db"
)

graph = workflow.compile(checkpointer=checkpointer)

# Her konuşma kendi thread_id'si ile izole edilir
config = {"configurable": {"thread_id": conversation_id, "tenant_id": tenant_id}}
result = graph.invoke({"messages": [HumanMessage(content=user_msg)]}, config)
```