import boto3
from opensearchpy import OpenSearch, AsyncOpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from src.config import get_settings
from src.logger import get_logger

logger = get_logger(__name__)

INDEX_NAME = "german-docs-chunks"

INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "doc_id": {"type": "keyword"},
            "text": {"type": "text", "analyzer": "standard"},
            "chunk_index": {"type": "integer"},
            "doc_type": {"type": "keyword"},
            "source_url": {"type": "keyword"},
            "page_number": {"type": "integer"},
            "section_reference": {"type": "keyword"},
            "embedding": {
                "type": "knn_vector",
                "dimension": 768,
            },
        }
    },
    "settings": {
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 100,
        }
    },
}


def _get_aws_auth():
    """Create AWS4Auth for OpenSearch Serverless."""
    credentials = boto3.Session().get_credentials()
    settings = get_settings()
    return AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        settings.opensearch_aws_region,
        "aoss",
        session_token=credentials.token,
    )


def get_opensearch_client() -> OpenSearch:
    """Create synchronous OpenSearch client."""
    settings = get_settings()

    if settings.opensearch_use_aws:
        return OpenSearch(
            hosts=[{"host": settings.opensearch_host, "port": 443}],
            http_auth=_get_aws_auth(),
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            pool_maxsize=20,
        )

    return OpenSearch(
        hosts=[{"host": settings.opensearch_host, "port": settings.opensearch_port}],
        use_ssl=False,
        verify_certs=False,
    )


def get_async_opensearch_client():
    """Create async OpenSearch client."""
    settings = get_settings()

    if settings.opensearch_use_aws:
        # AWS Serverless does not support async client natively
        # Use sync client wrapped — acceptable for portfolio
        return get_opensearch_client()

    from opensearchpy._async.client import AsyncOpenSearch
    return AsyncOpenSearch(
        hosts=[{"host": settings.opensearch_host, "port": settings.opensearch_port}],
        use_ssl=False,
        verify_certs=False,
    )


async def init_opensearch():
    """Create the chunks index if it does not exist."""
    client = get_opensearch_client()

    if not client.indices.exists(index=INDEX_NAME):
        client.indices.create(index=INDEX_NAME, body=INDEX_MAPPING)
        logger.info("opensearch_index_created", index=INDEX_NAME)
    else:
        logger.info("opensearch_index_exists", index=INDEX_NAME)

    client.close()


async def get_opensearch():
    """FastAPI dependency that provides an OpenSearch client."""
    client = get_async_opensearch_client()
    try:
        yield client
    finally:
        try:
            if hasattr(client, 'aclose'):
                await client.aclose()
            elif hasattr(client, 'close'):
                result = client.close()
                if hasattr(result, '__await__'):
                    await result
        except Exception:
            pass