from opensearchpy import OpenSearch
from opensearchpy._async.client import AsyncOpenSearch
from src.config import get_settings
from src.logger import get_logger

logger = get_logger(__name__)

INDEX_NAME ="german-docs-chunks"

INDEX_MAPPING={
    "mappings":{
        "properties": {
            "doc_id":{"type":"keyword"},
            "text":{"type": "text", "analyzer": "standard"},
            "page_number": {"type": "integer"},
            "section_reference": {"type": "keyword"},
            "chunk_index": {"type":"integer"},
            "doc_type":{"type":"keyword"},
            "source_url":{"type":"keyword"},
            "embedding":{
                "type":"knn_vector",
                "dimension":768,
            },
        }
    },

    "settings":{
        "index":{
            "knn": True,
            "knn.algo_param.ef_search":100,
        }
    },
}


def get_opensearch_client() -> OpenSearch:
    """Create synchronous OpenSearch client
    
    Used for index setup and admin operations at startup.
    For Request-time operations use get_async_OpenSearch_client().
    """
    settings = get_settings()
    return OpenSearch(
        hosts=[{
            "host":settings.opensearch_host,
            "port":settings.opensearch_port
        }],
        use_ssl=False,
        verify_certs=False,
    )

def get_async_opensearch_client()-> AsyncOpenSearch:
    """Create async OpenSearch client for use in FastAPI endpoints.
    
    Returns an async client that supports await - required for
    non-blocking search and index operations during requests.
    """
    settings=get_settings()
    return AsyncOpenSearch(
        hosts=[{
            "host":settings.opensearch_host,
            "port":settings.opensearch_port
        }],
        use_ssl=False,
        verify_certs=False,
    )


async def init_opensearch():
    """Create the chunks index if it does not exist.
    
    Called once at application startup. Sets up the knn_vector
    mapping required for semantic search.
    Safe to call multiple times - skips creation if index exists.
    """
    client = get_opensearch_client()

    if not client.indices.exists(index=INDEX_NAME):
        client.indices.create(index=INDEX_NAME, body=INDEX_MAPPING)
        logger.info("opensearch_index_created", index=INDEX_NAME)
    else:
        logger.info("opensearch_index_exists", index=INDEX_NAME)

    client.close()


async def get_opensearch():
    """FastAPI dependency that provides an async OpenSearch client.
    
    Yields client and closes connection when request_ends.
    Use with Depends(get_opensearch) in endpoint functions.
    """
    client= get_async_opensearch_client()
    try:
        yield client
    finally:
        await client.close()