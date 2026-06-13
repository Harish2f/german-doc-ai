import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text
from src.db.models import DocumentChunk
from src.logger import get_logger

logger = get_logger(__name__)


class ChunkRepository:
    """Data access layer for document chunks in PostgreSQL.
    
    Handles both write (ingestion) and read (retrieval) operations.
    """

    async def insert_chunks(
        self,
        db: AsyncSession,
        chunks: list[dict],
    ) -> int:
        """Insert chunks with embeddings into PostgreSQL.
        
        Args:
            db: Async database session.
            chunks: List of chunk dicts with text, embedding, and metadata.
            
        Returns:
            Number of chunks inserted.
        """
        for chunk in chunks:
            record = DocumentChunk(
                id=str(uuid.uuid4()),
                doc_id=chunk["doc_id"],
                chunk_text=chunk["text"],
                chunk_index=chunk["chunk_index"],
                doc_type=chunk["doc_type"],
                source_url=chunk.get("source_url", ""),
                page_number=chunk.get("page_number", 0),
                section_ref=chunk.get("section_reference", ""),
                embedding=chunk["embedding"],
            )
            db.add(record)

        await db.flush()
        logger.info("chunks_inserted", count=len(chunks))
        return len(chunks)

    async def hybrid_search(
        self,
        db: AsyncSession,
        query_text: str,
        query_embedding: list[float],
        doc_types: list[str] | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        """Hybrid search combining BM25 full-text search and vector similarity.
        
        Uses Reciprocal Rank Fusion to combine results.
        
        Args:
            db: Async database session.
            query_text: User query for BM25 search.
            query_embedding: Query embedding vector for semantic search.
            doc_types: Optional filter by document type.
            top_k: Number of results to return.
            
        Returns:
            List of chunk dicts ranked by RRF score.
        """
        doc_type_filter = ""
        if doc_types:
            types = ", ".join(f"'{t}'" for t in doc_types)
            doc_type_filter = f"AND doc_type IN ({types})"

        sql = text(f"""
            WITH bm25 AS (
                SELECT
                    id,
                    doc_id,
                    chunk_text,
                    chunk_index,
                    doc_type,
                    source_url,
                    page_number,
                    section_ref,
                    ts_rank(fts_vector, plainto_tsquery('english', :query)) AS score,
                    ROW_NUMBER() OVER (ORDER BY ts_rank(fts_vector, plainto_tsquery('english', :query)) DESC) AS rank
                FROM document_chunks
                WHERE fts_vector @@ plainto_tsquery('english', :query)
                {doc_type_filter}
                LIMIT :limit
            ),
            semantic AS (
                SELECT
                    id,
                    doc_id,
                    chunk_text,
                    chunk_index,
                    doc_type,
                    source_url,
                    page_number,
                    section_ref,
                    1 - (embedding <=> :embedding::vector) AS score,
                    ROW_NUMBER() OVER (ORDER BY embedding <=> :embedding::vector) AS rank
                FROM document_chunks
                WHERE embedding IS NOT NULL
                {doc_type_filter}
                LIMIT :limit
            ),
            rrf AS (
                SELECT
                    COALESCE(b.id, s.id) AS id,
                    COALESCE(b.doc_id, s.doc_id) AS doc_id,
                    COALESCE(b.chunk_text, s.chunk_text) AS chunk_text,
                    COALESCE(b.chunk_index, s.chunk_index) AS chunk_index,
                    COALESCE(b.doc_type, s.doc_type) AS doc_type,
                    COALESCE(b.source_url, s.source_url) AS source_url,
                    COALESCE(b.page_number, s.page_number) AS page_number,
                    COALESCE(b.section_ref, s.section_ref) AS section_ref,
                    COALESCE(1.0 / (60 + b.rank), 0) +
                    COALESCE(1.0 / (60 + s.rank), 0) AS rrf_score
                FROM bm25 b
                FULL OUTER JOIN semantic s ON b.id = s.id
            )
            SELECT * FROM rrf
            ORDER BY rrf_score DESC
            LIMIT :top_k
        """)

        result = await db.execute(
            sql,
            {
                "query": query_text,
                "embedding": query_embedding,
                "limit": top_k * 2,
                "top_k": top_k,
            }
        )

        rows = result.fetchall()
        return [
            {
                "doc_id": row.doc_id,
                "text": row.chunk_text,
                "chunk_index": row.chunk_index,
                "doc_type": row.doc_type,
                "source_url": row.source_url,
                "page_number": row.page_number,
                "section_reference": row.section_ref,
                "rrf_score": float(row.rrf_score),
            }
            for row in rows
        ]

    async def delete_by_doc_id(
        self, db: AsyncSession, doc_id: str
    ) -> int:
        """Delete all chunks for a document."""
        result = await db.execute(
            delete(DocumentChunk).where(DocumentChunk.doc_id == doc_id)
        )
        return result.rowcount


chunk_repository = ChunkRepository()
