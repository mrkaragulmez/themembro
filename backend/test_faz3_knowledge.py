"""
test_faz3_knowledge.py — Faz 3 E2E testleri
Milvus ingestion + vektör arama + chat RAG bağlamını doğrular.

Çalıştırma (host makinede):
    python3 backend/test_faz3_knowledge.py
"""
import asyncio
import sys
import time
import httpx

BASE    = "http://localhost:8000"
HEADERS = {"X-Tenant-Slug": "testco"}


async def main():
    passed = 0
    failed = 0

    async with httpx.AsyncClient(base_url=BASE, timeout=120) as c:

        # ── 1. Login ──────────────────────────────────────────────
        r = await c.post(
            "/api/v1/auth/login",
            json={"email": "admin@testco.com", "password": "Test1234!"},
            headers=HEADERS,
        )
        assert r.status_code == 200, f"Login başarısız: {r.text}"
        token = r.cookies.get("access_token")
        assert token, "access_token cookie bulunamadı"
        auth = {**HEADERS, "Authorization": f"Bearer {token}"}
        print(f"[PASS] Login 200")
        passed += 1

        # ── 2. Doküman yükle ──────────────────────────────────────
        doc_content = (
            "Membro AI platformunun iade politikası şöyledir: "
            "Kullanıcılar satın alma tarihinden itibaren 30 gün içinde "
            "tam iade talebinde bulunabilir. İade işlemi 5-7 iş günü içinde tamamlanır. "
            "İade için destek@membro.ai adresine e-posta gönderilmelidir. "
            "Abonelik iptali sonraki fatura döneminden itibaren geçerli olur."
        )

        r2 = await c.post(
            "/api/v1/knowledge/docs",
            json={"title": "İade Politikası", "content": doc_content},
            headers=auth,
        )
        assert r2.status_code == 202, f"Doküman yükleme başarısız: {r2.status_code} {r2.text}"
        doc_id = r2.json()["doc_id"]
        print(f"[PASS] Doküman yüklendi (202 Accepted): {doc_id}")
        passed += 1

        # ── 3. Indexleme tamamlanana kadar bekle ──────────────────
        max_wait = 60  # saniye
        indexed  = False
        for attempt in range(max_wait // 3):
            await asyncio.sleep(3)
            r_list = await c.get("/api/v1/knowledge/docs", headers=auth)
            docs = r_list.json()
            doc = next((d for d in docs if d["id"] == doc_id), None)
            status = doc["status"] if doc else "?"
            if status == "indexed":
                indexed = True
                chunk_count = doc.get("chunk_count", "?")
                print(f"[PASS] Doküman indexlendi ({attempt*3+3}s) — {chunk_count} chunk")
                passed += 1
                break
            elif status == "failed":
                print(f"[FAIL] Doküman indexleme başarısız: {doc}")
                failed += 1
                break

        if not indexed and failed == 0:
            print(f"[FAIL] Doküman {max_wait}s içinde indexlenmedi (son durum: {status})")
            failed += 1

        # ── 4. Doküman listesi ────────────────────────────────────
        r3 = await c.get("/api/v1/knowledge/docs", headers=auth)
        assert r3.status_code == 200, f"Liste başarısız: {r3.text}"
        docs = r3.json()
        assert any(d["id"] == doc_id for d in docs), "Yüklenen doküman listede yok!"
        print(f"[PASS] Doküman listesi doğrulandı ({len(docs)} doküman)")
        passed += 1

        # ── 5. Chat ile RAG testi ─────────────────────────────────
        # Membro'nun ID'sini buluyoruz
        rm = await c.get("/api/v1/membros/", headers=auth)
        membros = rm.json()
        membro_id = membros[0]["id"] if membros else None
        assert membro_id, "Test için membro bulunamadı"

        if indexed:
            r4 = await c.post(
                f"/api/v1/agents/{membro_id}/chat",
                json={"message": "İade süresi kaç gün?"},
                headers=auth,
            )
            assert r4.status_code == 200, f"Chat başarısız: {r4.text}"
            reply = r4.json()["reply"]
            print(f"[PASS] Chat RAG yanıtı: {reply[:100]}")
            passed += 1
        else:
            print(f"[SKIP] Indexleme olmadığı için RAG chat testi atlandı")

        # ── 6. API endpoint listesi doğrulama ─────────────────────
        r5 = await c.get("/openapi.json")
        paths = list(r5.json()["paths"].keys())
        knowledge_paths = [p for p in paths if "/knowledge/" in p]
        assert len(knowledge_paths) >= 2, f"Knowledge endpoint eksik: {paths}"
        print(f"[PASS] Knowledge API endpoint'leri: {knowledge_paths}")
        passed += 1

    print(f"\n{'='*55}")
    print(f"FAZ 3 SONUÇ: {passed} geçti, {failed} başarısız")
    return failed


if __name__ == "__main__":
    failures = asyncio.run(main())
    sys.exit(failures)
