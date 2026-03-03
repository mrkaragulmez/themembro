# backend/app/api/v1/knowledge.py
# Faz 3 — Bilgi Bankası API endpoint'leri
#
# POST /api/v1/knowledge/docs         → Doküman yükle ve index'e ekle
# GET  /api/v1/knowledge/docs         → Tenant dokümanlarını listele
# DELETE /api/v1/knowledge/docs/{id}  → Doküman ve vektörleri sil

from __future__ import annotations

import uuid
import structlog

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import KnowledgeDoc
from app.services.ingestion import ingest_document, delete_doc_vectors
log = structlog.get_logger()

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


# ─── Şemalar ────────────────────────────────────────────────────────────────

class DocUploadRequest(BaseModel):
    title:     str
    content:   str
    membro_id: str | None = None   # Belirli bir Membro'ya bağlama (opsiyonel)


class DocResponse(BaseModel):
    id:         str
    title:      str
    status:     str
    membro_id:  str | None
    chunk_count: int | None = None
    created_at: str


# ─── POST /knowledge/docs ────────────────────────────────────────────────────

@router.post("/docs", status_code=status.HTTP_202_ACCEPTED)
async def upload_doc(
    body:             DocUploadRequest,
    request:          Request,
    background_tasks: BackgroundTasks,
    db:               AsyncSession = Depends(get_db),
):
    """Doküman yükler ve arka planda index'e ekler.

    Yanıt 202 Accepted ile hemen döner; index işlemi background task'ta çalışır.
    Durum `status` alanından izlenebilir: pending → processing → indexed | failed.
    """
    tenant_id: str | None = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id bulunamadı")

    tenant_id_str = str(tenant_id)

    # PG'ye kayıt — status "pending"
    doc = KnowledgeDoc(
        tenant_id=uuid.UUID(tenant_id_str),
        membro_id=uuid.UUID(body.membro_id) if body.membro_id else None,
        title=body.title,
        content=body.content,
        status="pending",
    )
    db.add(doc)
    await db.flush()
    doc_id = str(doc.id)

    log.info("knowledge.upload", tenant_id=tenant_id_str, doc_id=doc_id, title=body.title[:50])

    # Arka planda ingest — HTTP yanıtını bloklamaz
    background_tasks.add_task(
        _run_ingestion,
        doc_id=doc_id,
        tenant_id=tenant_id_str,
        membro_id=body.membro_id or "",
        title=body.title,
        content=body.content,
    )

    await db.commit()

    return {
        "doc_id": doc_id,
        "status": "pending",
        "message": "Doküman alındı, indexleme başlatıldı.",
    }


# ─── GET /knowledge/docs ─────────────────────────────────────────────────────

@router.get("/docs", response_model=list[DocResponse])
async def list_docs(
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    """Tenant'a ait tüm dokümanları listing olarak döndürür."""
    tenant_id: str | None = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id bulunamadı")

    rows = (
        await db.execute(
            select(KnowledgeDoc)
            .where(KnowledgeDoc.tenant_id == uuid.UUID(str(tenant_id)))
            .order_by(KnowledgeDoc.created_at.desc())
            .limit(100)
        )
    ).scalars().all()

    return [
        DocResponse(
            id=str(r.id),
            title=r.title,
            status=r.status,
            membro_id=str(r.membro_id) if r.membro_id else None,
            chunk_count=(r.extra or {}).get("chunk_count") if r.extra else None,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


# ─── DELETE /knowledge/docs/{doc_id} ────────────────────────────────────────

@router.delete("/docs/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doc(
    doc_id:  str,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    """Dokümanı ve tüm Milvus vektörlerini siler."""
    tenant_id: str | None = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id bulunamadı")

    tenant_id_str = str(tenant_id)

    doc = (
        await db.execute(
            select(KnowledgeDoc).where(
                KnowledgeDoc.id == uuid.UUID(doc_id),
                KnowledgeDoc.tenant_id == uuid.UUID(tenant_id_str),
            )
        )
    ).scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Doküman bulunamadı")

    # Milvus vektörlerini sil
    try:
        delete_doc_vectors(doc_id=doc_id, tenant_id=tenant_id_str)
    except Exception as exc:
        log.warning("knowledge.delete_vectors_error", error=str(exc))

    # Neo4j Chunk + orphan Entity'leri sil
    try:
        from app.services.graph_ingestion import graph_delete_doc
        from app.core.neo4j_client import get_neo4j_driver
        get_neo4j_driver()  # bağlı değilse RuntimeError → sessiz atla
        await graph_delete_doc(doc_id=doc_id, tenant_id=tenant_id_str)
    except RuntimeError:
        pass
    except Exception as exc:
        log.warning("knowledge.delete_graph_error", error=str(exc))

    await db.delete(doc)
    await db.commit()

    log.info("knowledge.deleted", doc_id=doc_id, tenant_id=tenant_id_str)


# ─── Arka Plan Yardımcısı ────────────────────────────────────────────────────

async def _run_ingestion(
    *,
    doc_id:    str,
    tenant_id: str,
    membro_id: str,
    title:     str,
    content:   str,
) -> None:
    """Background task: kendi DB session'ı ile ingest_document çalıştırır."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # Status "processing" olarak işaretle
            from sqlalchemy import update
            await db.execute(
                update(KnowledgeDoc)
                .where(KnowledgeDoc.id == uuid.UUID(doc_id))
                .values(status="processing")
            )
            await db.commit()

            await ingest_document(
                doc_id=doc_id,
                tenant_id=tenant_id,
                membro_id=membro_id,
                title=title,
                content=content,
                db=db,
            )
        except Exception as exc:
            log.error("knowledge.ingestion_failed", doc_id=doc_id, error=str(exc))
            from sqlalchemy import update
            await db.execute(
                update(KnowledgeDoc)
                .where(KnowledgeDoc.id == uuid.UUID(doc_id))
                .values(status="failed", extra={"error": str(exc)})
            )
            await db.commit()
