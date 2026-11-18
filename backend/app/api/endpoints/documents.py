from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.document import DocumentQueryRequest, DocumentQueryResponse, DocumentChunkResult
from app.repositories.vector_repo import VectorRepository
from app.services.llm_service import llm_service

router = APIRouter()


@router.post("/query", response_model=DocumentQueryResponse)
async def query_documents(request: DocumentQueryRequest, db: Session = Depends(get_db)):
    """Search vectorized documents and generate grounded answer with citations."""
    try:
        vector_repo = VectorRepository(db)
        chunk_results = vector_repo.search_similar_chunks(
            query=request.query,
            file_ids=request.file_ids,
            top_k=request.top_k
        )

        if not chunk_results:
            return DocumentQueryResponse(
                answer="No relevant evidence was found in the indexed documents to support an answer to this query.",
                sources=[],
                grounded=False
            )

        context_str = "\n".join(
            f"[E{i}] {c['filename']} ({c.get('source_ref') or 'source'}): {c['text']}"
            for i, c in enumerate(chunk_results, start=1)
        )
        prompt = f"Based on the provided excerpts, answer the question accurately:\n\nQuestion: {request.query}"

        answer = await llm_service.generate_response(prompt=prompt, context=context_str)

        sources = [
            DocumentChunkResult(
                chunk_id=c["chunk_id"],
                file_id=c["file_id"],
                filename=c["filename"],
                page_number=c.get("page_number"),
                text=c["text"],
                score=c["score"]
            )
            for c in chunk_results
        ]

        return DocumentQueryResponse(
            answer=answer,
            sources=sources,
            grounded=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
