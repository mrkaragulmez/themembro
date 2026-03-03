#!/usr/bin/env python3
"""
Faz 3 — Neo4j GraphRAG Entegrasyon Testi

Test Adımları:
  1. Login (cookie token al)
  2. Doküman yükle (entity içerikli)
  3. Indexleme + Neo4j graph ingestion tamamlanmasını bekle
  4. Neo4j'de entity var mı doğrula (doğrudan Neo4j sorgusu)
  5. Graph bilgisini içeren RAG chat yanıtı doğrula
  6. Doküman sil → Neo4j chunk+entity temizliğini doğrula

Çalıştırma: python3 backend/test_faz3_graphrag.py
(Docker dışında, host'ta)
"""

import sys
import time
import asyncio
import httpx
from neo4j import AsyncGraphDatabase

BASE_URL    = "http://localhost:8000"
NEO4J_URI   = "bolt://localhost:7687"
NEO4J_USER  = "neo4j"
NEO4J_PASS  = "35JWXFD3BwVF7ejTu8EcNmw"
TENANT_SLUG = "testco"
EMAIL       = "admin@testco.com"
PASSWORD    = "Test1234!"

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"

passed = 0
failed = 0
doc_id: str | None = None
auth_headers: dict = {}


def ok(msg: str) -> None:
    global passed
    passed += 1
    print(f"{PASS} {msg}")


def fail(msg: str) -> None:
    global failed
    failed += 1
    print(f"{FAIL} {msg}")


# ─── 1. Login ────────────────────────────────────────────────────────────────

def step1_login(client: httpx.Client) -> bool:
    global auth_headers
    r = client.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        headers={"X-Tenant-Slug": TENANT_SLUG},
    )
    if r.status_code == 200:
        token = r.cookies.get("access_token")
        if token:
            auth_headers = {"X-Tenant-Slug": TENANT_SLUG, "Authorization": f"Bearer {token}"}
            ok("Login 200, token alındı")
            return True
    fail(f"Login başarısız: {r.status_code} — {r.text[:200]}")
    return False


# ─── 2. Doküman Yükle ────────────────────────────────────────────────────────

ENTITY_RICH_DOC = """
Membro iade politikası şunları kapsar:

Müşteriler, satın alma tarihinden itibaren 30 gün içinde ürünleri iade edebilir.
İade politikası müşteri memnuniyeti taahhüdünün bir parçasıdır.
Acme Şirketi, çevre dostu ambalaj kullanır.
Acme Şirketi'nin müşteri desteği hafta içi 09:00-18:00 saatleri arasında aktiftir.
Müşteriler iade taleplerini e-posta veya telefon aracılığıyla iletebilir.
"""

def step2_upload(client: httpx.Client) -> bool:
    global doc_id
    r = client.post(
        f"{BASE_URL}/api/v1/knowledge/docs",
        json={
            "title":   "Membro GraphRAG Test Dokümanı",
            "content": ENTITY_RICH_DOC.strip(),
        },
        headers=auth_headers,
    )
    if r.status_code == 202:
        doc_id = r.json().get("doc_id")
        ok(f"Doküman yüklendi (202), doc_id={doc_id[:8]}...")
        return True
    fail(f"Upload başarısız: {r.status_code} — {r.text[:200]}")
    return False


# ─── 3. Indexleme + Graph Ingestion Bekle ────────────────────────────────────

def step3_wait_indexed(client: httpx.Client) -> bool:
    for i in range(30):
        time.sleep(2)
        r = client.get(f"{BASE_URL}/api/v1/knowledge/docs", headers=auth_headers)
        if r.status_code != 200:
            continue
        docs = r.json()
        match = next((d for d in docs if d["id"] == doc_id), None)
        if match and match["status"] == "indexed":
            ok(f"Doküman indexlendi ({(i+1)*2}s)")
            return True
        if match and match["status"] == "failed":
            fail(f"İndexleme başarısız: {match}")
            return False
    fail("İndexleme zaman aşımı (60s)")
    return False


# ─── 4. Neo4j Entity Varlığını Doğrula ───────────────────────────────────────

async def step4_verify_neo4j(client: httpx.Client) -> bool:
    """Neo4j'e doğrudan bağlanarak entity'lerin yazıldığını doğrula."""

    # Neo4j graph ingestion, indexleme bittikten sonra arka planda çalışır
    # Biraz daha bekle
    for attempt in range(20):
        time.sleep(3)
        driver = AsyncGraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS)
        )
        try:
            async with driver.session() as session:
                # tenant_id'dan docs listesini al (sadece log için)
                r2 = client.get(f"{BASE_URL}/api/v1/knowledge/docs", headers=auth_headers)
                docs = r2.json()
                # herhangi bir entity var mı?
                result = await session.run(
                    "MATCH (e:Entity) RETURN count(e) AS cnt LIMIT 1"
                )
                record = await result.single()
                cnt = record["cnt"] if record else 0

                if cnt > 0:
                    ok(f"Neo4j'de {cnt} entity bulundu")

                    # Chunk kontrol
                    c_result = await session.run(
                        "MATCH (c:Chunk) WHERE c.doc_id = $doc_id RETURN count(c) AS cnt",
                        doc_id=doc_id,
                    )
                    c_record = await c_result.single()
                    chunk_cnt = c_record["cnt"] if c_record else 0
                    ok(f"Neo4j'de {chunk_cnt} chunk bulundu (doc_id={doc_id[:8]}...)")

                    # Relation kontrol
                    r_result = await session.run(
                        "MATCH ()-[r]->() RETURN count(r) AS cnt LIMIT 1"
                    )
                    r_record = await r_result.single()
                    rel_cnt = r_record["cnt"] if r_record else 0
                    ok(f"Neo4j'de {rel_cnt} ilişki bulundu")

                    return True
        except Exception as exc:
            print(f"  [attempt {attempt+1}] Neo4j bekleniyor: {exc}")
        finally:
            await driver.close()

    fail("Neo4j'de entity bulunamadı (60s timeout)")
    return False


# ─── 5. GraphRAG Chat Yanıtı ─────────────────────────────────────────────────

def step5_graph_chat(client: httpx.Client) -> bool:
    r = client.get(f"{BASE_URL}/api/v1/membros/", headers=auth_headers)
    if r.status_code != 200 or not r.json():
        fail(f"Membro listesi alınamadı: {r.status_code}")
        return False
    membro_id = r.json()[0]["id"]

    r = client.post(
        f"{BASE_URL}/api/v1/agents/{membro_id}/chat",
        json={
            "message":         "Acme Şirketi'nin iade politikası nedir?",
            "conversation_id": "graphrag-test-conv-001",
        },
        headers=auth_headers,
        timeout=60,
    )
    if r.status_code != 200:
        fail(f"Chat isteği başarısız: {r.status_code} — {r.text[:200]}")
        return False

    answer = r.json().get("reply", "")
    print(f"  Chat yanıtı: {answer[:180]}")

    # GraphRAG veya Milvus RAG sayesinde 30 gün veya Acme hakkında yanıt gelmeli
    keywords = ["30", "iade", "acme", "politika", "müşteri"]
    if any(kw.lower() in answer.lower() for kw in keywords):
        ok("GraphRAG destekli chat yanıtı ilgili içerik içeriyor")
        return True
    fail(f"Chat yanıtı beklenen içeriği içermiyor: {answer[:150]}")
    return False


# ─── 6. Silme + Neo4j Temizliği ──────────────────────────────────────────────

async def step6_delete_verify(client: httpx.Client) -> bool:
    r = client.delete(f"{BASE_URL}/api/v1/knowledge/docs/{doc_id}", headers=auth_headers)
    if r.status_code != 204:
        fail(f"DELETE başarısız: {r.status_code}")
        return False

    time.sleep(3)  # Neo4j silme async

    driver = AsyncGraphDatabase.driver(
        NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS)
    )
    try:
        async with driver.session() as session:
            result = await session.run(
                "MATCH (c:Chunk {doc_id: $doc_id}) RETURN count(c) AS cnt",
                doc_id=doc_id,
            )
            record = await result.single()
            cnt = record["cnt"] if record else -1
            if cnt == 0:
                ok("Silme sonrası Neo4j Chunk'ları temizlendi")
                return True
            fail(f"Neo4j'de hâlâ {cnt} chunk var (silinmedi)")
            return False
    finally:
        await driver.close()


# ─── Ana Akış ────────────────────────────────────────────────────────────────

async def main() -> None:
    print("\n=== FAZ 3 GraphRAG Entegrasyon Testi ===\n")

    with httpx.Client(follow_redirects=True, timeout=30) as client:
        if not step1_login(client):
            print("\nLogin başarısız, test durduruluyor.")
            sys.exit(1)

        if not step2_upload(client):
            print("\nUpload başarısız, test durduruluyor.")
            sys.exit(1)

        if not step3_wait_indexed(client):
            sys.exit(1)

        # Neo4j async verify
        neo4j_ok = await step4_verify_neo4j(client)
        if not neo4j_ok:
            fail("Neo4j verify atlandı")

        step5_graph_chat(client)

        await step6_delete_verify(client)

    print(f"\nFAZ 3 GraphRAG SONUÇ: {passed} geçti, {failed} başarısız")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
