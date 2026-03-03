# backend/app/services/graph_ingestion.py
# Faz 3 — Neo4j GraphRAG entity extraction + graph yazma / arama
#
# Akış (ingestion):
#   Chunk metni → LLM (gpt-4o-mini, CF AI Gateway, JSON mode)
#     → Entities: [{name, type, description}]
#     → Relationships: [{source, relation, target}]
#     → Neo4j'e Chunk + Entity node'ları yaz
#     → MENTIONS + entity-entity ilişkilerini kur
#
# Akış (arama):
#   Query → keyword token'lara böl
#     → Neo4j'de Entity CONTAINS eşleşmesi
#     → Bağlı Chunk içerikleri + ilişki yolları → graph_facts listesi
#
# Güvenlik: tenant_id her zaman Neo4j filtresinde zorunlu.

from __future__ import annotations

import json
import structlog
import httpx

from app.core.config import settings
from app.core.neo4j_client import get_neo4j_driver

log = structlog.get_logger()

# ─── Sabitler ───────────────────────────────────────────────────────────────

_ENTITY_EXTRACT_SYSTEM = """\
Sen bir entity extraction asistanısın.
Verilen metinden varlıkları (entity) ve aralarındaki ilişkileri JSON formatında çıkar.

Yanıt SADECE şu JSON formatında olmalı:
{
  "entities": [
    {"name": "...", "type": "PERSON|ORG|PRODUCT|CONCEPT|POLICY|OTHER", "description": "..."}
  ],
  "relationships": [
    {"source": "entity_name", "relation": "ILIŞKI_ETIKETI", "target": "entity_name"}
  ]
}

Kurallar:
- Sadece metinde açıkça bahsedilen entity'leri çıkar
- En fazla 10 entity, 10 ilişki
- type alanı yukarıdaki Literal değerlerinden biri olsun (İngilizce, büyük harf)
- Metin Türkçe olabilir; entity isimleri metinde geçtiği gibi kalsın
- İlişki etiketleri BÜYÜK_HARF_SNAKE_CASE (örn: HAS_POLICY, RETURNS_TO)
- Boş liste döndürmek kabul edilir; açıklayıcı metin EKLEME
"""


# ─── Entity Extraction (LLM) ────────────────────────────────────────────────

async def _extract_entities(text: str) -> dict:
    """CF AI Gateway üzerinden gpt-4o-mini ile entity extraction (JSON mode).

    Args:
        text: Ham chunk metni (ilk 1500 karakter kullanılır).

    Returns:
        {"entities": [...], "relationships": [...]}
    """
    gateway_url = (
        f"{settings.cf_ai_gateway_url.rstrip('/')}/openai/v1/chat/completions"
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                gateway_url,
                headers={
                    "Authorization": f"Bearer {settings.cf_aig_token}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model":           "gpt-4o-mini",
                    "temperature":     0,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": _ENTITY_EXTRACT_SYSTEM},
                        {"role": "user",   "content": f"Metin:\n{text[:1500]}"},
                    ],
                },
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
            return json.loads(raw)
    except (httpx.HTTPError, json.JSONDecodeError, KeyError) as exc:
        log.warning("graph_ingestion.extraction_failed", error=str(exc))
        return {"entities": [], "relationships": []}


# ─── Ingestion ──────────────────────────────────────────────────────────────

async def graph_ingest_chunks(
    *,
    chunks: list[str],
    doc_id: str,
    tenant_id: str,
) -> int:
    """Her chunk için entity extraction yapar ve Neo4j'e chunk + entity yazar.

    Args:
        chunks:    İçerik parçalarının listesi (ingestion.py'den gelir).
        doc_id:    PostgreSQL MO_KnowledgeDocs.id (UUID string).
        tenant_id: JWT kaynaklı tenant UUID string.

    Returns:
        Toplam yazılan/güncellenen entity sayısı (loglama + PG extra için).
    """
    driver = get_neo4j_driver()
    total_entities = 0

    for idx, chunk_text in enumerate(chunks):
        chunk_id = f"{doc_id}_{idx}"

        # ── 1. Entity extraction ────────────────────────────────
        extracted   = await _extract_entities(chunk_text)
        entities    = extracted.get("entities", []) or []
        relationships = extracted.get("relationships", []) or []

        async with driver.session() as session:

            # ── 2. Chunk node ───────────────────────────────────
            await session.run(
                """
                MERGE (c:Chunk {chunk_id: $chunk_id, tenant_id: $tenant_id})
                SET   c.doc_id  = $doc_id,
                      c.content = $content,
                      c.idx     = $idx
                """,
                chunk_id=chunk_id,
                tenant_id=tenant_id,
                doc_id=doc_id,
                content=chunk_text[:2000],
                idx=idx,
            )

            # ── 3. Entity node'ları + MENTIONS ilişkileri ───────
            for ent in entities:
                name  = (ent.get("name")        or "").strip()
                etype = (ent.get("type")         or "OTHER").upper()
                desc  = (ent.get("description")  or "")[:500]

                if not name:
                    continue

                await session.run(
                    """
                    MERGE (e:Entity {name: $name, tenant_id: $tenant_id})
                    SET   e.type        = $etype,
                          e.description = $desc
                    WITH  e
                    MATCH (c:Chunk {chunk_id: $chunk_id, tenant_id: $tenant_id})
                    MERGE (c)-[:MENTIONS]->(e)
                    """,
                    name=name,
                    tenant_id=tenant_id,
                    etype=etype,
                    desc=desc,
                    chunk_id=chunk_id,
                )
                total_entities += 1

            # ── 4. Entity–Entity ilişkileri ─────────────────────
            for rel in relationships:
                src      = (rel.get("source")   or "").strip()
                tgt      = (rel.get("target")   or "").strip()
                relation = (rel.get("relation") or "RELATED_TO").upper().strip()

                if not src or not tgt:
                    continue

                # Cypher'da ilişki adı parametre olarak verilemez — sanitize
                rel_safe = "".join(
                    c for c in relation.replace(" ", "_")
                    if c.isalnum() or c == "_"
                )[:50] or "RELATED_TO"

                try:
                    await session.run(
                        f"""
                        MATCH (src:Entity {{name: $src, tenant_id: $tenant_id}})
                        MATCH (tgt:Entity {{name: $tgt, tenant_id: $tenant_id}})
                        MERGE (src)-[:`{rel_safe}`]->(tgt)
                        """,
                        src=src,
                        tgt=tgt,
                        tenant_id=tenant_id,
                    )
                except Exception as exc:
                    log.warning(
                        "graph_ingestion.rel_write_failed",
                        src=src, tgt=tgt, rel=rel_safe, error=str(exc),
                    )

        log.info(
            "graph_ingestion.chunk_done",
            chunk_id=chunk_id,
            entity_count=len(entities),
            rel_count=len(relationships),
        )

    log.info(
        "graph_ingestion.doc_done",
        doc_id=doc_id,
        chunk_count=len(chunks),
        total_entities=total_entities,
    )
    return total_entities


# ─── Silme ──────────────────────────────────────────────────────────────────

async def graph_delete_doc(*, doc_id: str, tenant_id: str) -> None:
    """Bir dokümanın Neo4j Chunk node'larını ve orphan Entity'lerini siler.

    Adımlar:
    1. doc_id'ye ait Chunk'ları DETACH DELETE — ilişkiler otomatik silinir.
    2. Hiçbir Chunk'a MENTIONS bağı kalmayan Entity'leri temizle.
    """
    driver = get_neo4j_driver()

    async with driver.session() as session:
        # Chunk'ları ve tüm ilişkilerini sil
        await session.run(
            """
            MATCH (c:Chunk {doc_id: $doc_id, tenant_id: $tenant_id})
            DETACH DELETE c
            """,
            doc_id=doc_id,
            tenant_id=tenant_id,
        )

        # Orphan entity'leri temizle (bu tenant'a özel)
        await session.run(
            """
            MATCH (e:Entity {tenant_id: $tenant_id})
            WHERE NOT ()-[:MENTIONS]->(e)
            DELETE e
            """,
            tenant_id=tenant_id,
        )

    log.info("graph_ingestion.doc_deleted", doc_id=doc_id, tenant_id=tenant_id)


# ─── Arama ──────────────────────────────────────────────────────────────────

async def graph_search(
    *,
    query: str,
    tenant_id: str,
    top_k: int = 5,
) -> list[str]:
    """Query keyword'lerine göre Neo4j'den ilgili graph_facts döndürür.

    Strateji:
    1. Query'yi tokenize et (3+ karakter).
    2. Entity.name CONTAINS token eşleşmesi yap.
    3. Eşleşen entity bilgilerini fact olarak ekle.
    4. Entity → Entity ilişkilerini fact olarak ekle.
    5. İlgili Chunk içeriklerini fact olarak ekle.

    Args:
        query:     Kullanıcı mesajı.
        tenant_id: JWT kaynaklı tenant — Neo4j filtresinde zorunlu.
        top_k:     Maks döndürülecek chunk sayısı.

    Returns:
        graph_facts: LLM system prompt'una eklenecek string listesi.
    """
    driver = get_neo4j_driver()
    facts: list[str] = []

    # ── Token'lar ──────────────────────────────────────────────
    raw_tokens = query.split()
    tokens = [
        w.strip(".,;:!?\"'()")
        for w in raw_tokens
        if len(w.strip(".,;:!?\"'()")) >= 3
    ]

    if not tokens:
        return facts

    async with driver.session() as session:

        # ── 1. Entity eşleşmesi ─────────────────────────────────
        where_parts = " OR ".join(
            [f"toLower(e.name) CONTAINS toLower('{t}')" for t in tokens[:8]]
        )

        entity_result = await session.run(
            f"""
            MATCH (e:Entity {{tenant_id: $tenant_id}})
            WHERE {where_parts}
            RETURN e.name AS name, e.type AS type, e.description AS desc
            LIMIT 10
            """,
            tenant_id=tenant_id,
        )
        entities = [r.data() async for r in entity_result]

        if not entities:
            return facts

        entity_names = [e["name"] for e in entities]

        # ── 2. Entity bilgileri → fact ──────────────────────────
        for ent in entities:
            fact = f"[{ent.get('type', 'ENTITY')}] {ent['name']}"
            if ent.get("desc"):
                fact += f": {ent['desc']}"
            facts.append(fact)

        # ── 3. Entity–Entity ilişkileri ─────────────────────────
        rel_result = await session.run(
            """
            MATCH (src:Entity {tenant_id: $tenant_id})-[r]->(tgt:Entity {tenant_id: $tenant_id})
            WHERE src.name IN $names OR tgt.name IN $names
            RETURN src.name AS src, type(r) AS rel, tgt.name AS tgt
            LIMIT 20
            """,
            tenant_id=tenant_id,
            names=entity_names,
        )
        rels = [r.data() async for r in rel_result]
        for r in rels:
            facts.append(f"{r['src']} --[{r['rel']}]--> {r['tgt']}")

        # ── 4. İlgili Chunk içerikleri ──────────────────────────
        chunk_result = await session.run(
            """
            MATCH (c:Chunk {tenant_id: $tenant_id})-[:MENTIONS]->(e:Entity {tenant_id: $tenant_id})
            WHERE e.name IN $names
            RETURN DISTINCT c.content AS content
            LIMIT $top_k
            """,
            tenant_id=tenant_id,
            names=entity_names,
            top_k=top_k,
        )
        chunk_facts = [r.data()["content"] async for r in chunk_result]
        facts.extend(chunk_facts)

    log.info(
        "graph_search.done",
        tenant_id=tenant_id,
        token_count=len(tokens),
        entity_matches=len(entities),
        fact_count=len(facts),
    )

    # Toplam cap: entity + ilişki + chunk = max top_k * 3
    return facts[: top_k * 3]
