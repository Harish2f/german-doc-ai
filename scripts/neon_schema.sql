-- =============================================================================
-- german-doc-ai: Hybrid Search Schema (PostgreSQL + pgvector)
-- Run this in the Neon SQL Editor before any application code.
-- =============================================================================


-- ---------------------------------------------------------------------------
-- 0. Extensions
-- ---------------------------------------------------------------------------

-- pgvector: stores & queries dense embedding vectors
CREATE EXTENSION IF NOT EXISTS vector;

-- pg_trgm: trigram similarity — optional, but boosts fuzzy keyword matching
-- (also required for GIN indexes on text columns in some Postgres builds)
CREATE EXTENSION IF NOT EXISTS pg_trgm;


-- ---------------------------------------------------------------------------
-- 1. Documents (metadata store — mirrors existing Postgres table)
-- ---------------------------------------------------------------------------

-- This table already exists via SQLAlchemy; shown here for completeness and
-- to add the columns we need for hybrid search without breaking existing rows.

-- Add full document content to the documents table (was missing before).
-- This lets us re-chunk without re-fetching from source.
ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS content TEXT NOT NULL DEFAULT '';

-- Soft-delete / versioning support
ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;


-- ---------------------------------------------------------------------------
-- 2. Document Chunks
-- ---------------------------------------------------------------------------
-- Each row is one chunk produced by the ingestion pipeline.
-- Replaces the OpenSearch "german-docs-chunks" index.

CREATE TABLE IF NOT EXISTS document_chunks (
    -- Identity
    id              TEXT        PRIMARY KEY,          -- UUID generated at ingest time
    doc_id          TEXT        NOT NULL
                                REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index     INTEGER     NOT NULL,             -- 0-based position within document

    -- Content
    chunk_text      TEXT        NOT NULL,             -- raw chunk text (German)

    -- Keyword search (BM25-style via tsvector)
    -- Stored as a GENERATED column so it stays in sync automatically.
    -- 'german' config strips stopwords, applies German stemming (Snowball).
    fts_vector      TSVECTOR    GENERATED ALWAYS AS (
                        to_tsvector('german', chunk_text)
                    ) STORED,

    -- Semantic search (pgvector)
    -- 768 dimensions matches multilingual-e5-base / paraphrase-multilingual-mpnet.
    -- Change to 1536 if you switch to text-embedding-3-small (OpenAI).
    embedding       VECTOR(768) NOT NULL,

    -- Provenance / filter metadata
    doc_type        TEXT        NOT NULL,             -- mirrors DocumentType enum
    source_url      TEXT        NOT NULL DEFAULT '',
    page_number     INTEGER     NOT NULL DEFAULT 0,
    section_ref     TEXT        NOT NULL DEFAULT '',  -- e.g. "§ 25a KWG Abs. 1"

    -- Housekeeping
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enforce stable ordering of chunks within a document
CREATE UNIQUE INDEX IF NOT EXISTS uq_chunk_position
    ON document_chunks (doc_id, chunk_index);


-- ---------------------------------------------------------------------------
-- 3. Indexes
-- ---------------------------------------------------------------------------

-- 3a. GIN index for full-text search (fast @@ queries)
CREATE INDEX IF NOT EXISTS idx_chunks_fts
    ON document_chunks USING GIN (fts_vector);

-- 3b. HNSW index for approximate nearest-neighbour vector search
--     cosine distance (<=>): best for normalised sentence embeddings.
--     m=16, ef_construction=64 are solid defaults; tune after load testing.
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
    ON document_chunks USING HNSW (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 3c. Filter indexes (used in WHERE clauses before vector/fts scan)
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id   ON document_chunks (doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_type ON document_chunks (doc_type);


-- ---------------------------------------------------------------------------
-- 4. RRF (Reciprocal Rank Fusion) Query Template
-- ---------------------------------------------------------------------------
-- Copy-paste this into your retriever.  Replace $1 / $2 / $3 with your
-- query string, query embedding, and result limit k.
--
-- RRF score = 1/(rrf_k + bm25_rank) + 1/(rrf_k + vec_rank)
-- rrf_k = 60 is the standard constant from the original RRF paper.
-- ---------------------------------------------------------------------------

/*

WITH bm25 AS (
    -- Keyword leg: ranked by ts_rank (BM25 approximation)
    SELECT
        id,
        ROW_NUMBER() OVER (ORDER BY ts_rank(fts_vector, query) DESC) AS bm25_rank
    FROM
        document_chunks,
        plainto_tsquery('german', $1) AS query          -- $1 = user query string
    WHERE
        fts_vector @@ query
    LIMIT 100                                            -- candidate pool
),
vec AS (
    -- Semantic leg: ranked by cosine distance (smaller = more similar)
    SELECT
        id,
        ROW_NUMBER() OVER (ORDER BY embedding <=> $2 ASC) AS vec_rank
    FROM
        document_chunks
    ORDER BY embedding <=> $2                            -- $2 = query embedding (vector)
    LIMIT 100
),
rrf AS (
    -- Fuse both legs with RRF
    SELECT
        COALESCE(b.id, v.id) AS id,
        (
            COALESCE(1.0 / (60 + b.bm25_rank), 0) +
            COALESCE(1.0 / (60 + v.vec_rank),  0)
        ) AS rrf_score
    FROM bm25 b
    FULL OUTER JOIN vec v ON b.id = v.id
)
SELECT
    c.id,
    c.doc_id,
    c.chunk_text,
    c.doc_type,
    c.source_url,
    c.page_number,
    c.section_ref,
    r.rrf_score
FROM rrf r
JOIN document_chunks c ON c.id = r.id
ORDER BY r.rrf_score DESC
LIMIT $3;                                                -- $3 = k (e.g. 10)

*/


-- ---------------------------------------------------------------------------
-- 5. Sanity check — run after applying the schema
-- ---------------------------------------------------------------------------

/*

-- Confirm both extensions loaded
SELECT extname, extversion FROM pg_extension
WHERE extname IN ('vector', 'pg_trgm');

-- Confirm tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Confirm indexes
SELECT indexname, indexdef FROM pg_indexes
WHERE tablename = 'document_chunks'
ORDER BY indexname;

-- Confirm generated column is working (insert a test chunk first)
SELECT id, left(chunk_text, 50), fts_vector
FROM document_chunks LIMIT 3;

*/
