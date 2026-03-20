from openai import AsyncAzureOpenAI
from src.config import get_settings
from src.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """
You are a regulatory compliance assistant specializing in German financial regulations.

You answer questions based ONLY on the provided document chunks. 
If the answer is not in the chunks, say "I cannot find this information in the provided documents."

Rules:
- Answer in the same language as the question (German or English)
- Always cite the source document for each claim
- Never invent or assume information not present in the chunks

"""

def get_azure_openai_client()-> AsyncAzureOpenAI :
    """Create async Azure OpenAI client from settings.
    
    Return:
        AsyncAzureOpenAI client configured for our Azure deployment.
    """
    settings = get_settings()
    return AsyncAzureOpenAI(
        api_key=settings.azure_openai_api_key,
        azure_endpoint=settings.azure_openai_endpoint,
        api_version="2024-02-01",
    )

async def generate_answer(
        query: str,
        chunks: list[dict],
) -> dict:
    """Generate an answer from retrieved chunks using Azure Open AI.
    
    Format chunks as context and asks GPT-4o to answer the query
    based only on the provided context.

    Args:
        query: User's question in German or English.
        chunks: list of retrieved chunk dicts with text and metadata.

    Returns:
        Dict with answer, sources and token usage.

    Raises:
        ValueError: If Azure OpenAI ApI call fails.
    
    """
    settings = get_settings()
    client = get_azure_openai_client()

    # Format chnks as context
    context_parts = []
    for i, chunk in enumerate(chunks):
        context_parts.append(
            f"[Source {i+1}] Document: {chunk['doc_id']}"

            f"(Type: {chunk['doc_type']})\n{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    user_message = f"""Context documents:
        
    {context}

    Question: {query}

    Please answer the question based only on the context documents above."""

    logger.info(
            "generating_answer",
            query=query,
            chunk_count=len(chunks),
            context_length = len(context),
        )

    try:
        response = await client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages = [
                {"role":"system", "content":SYSTEM_PROMPT},
                {"role":"user", "content": user_message},
            ],
            temperature =0.0,
            max_tokens=1000,
        )

        answer = response.choices[0].message.content
        usage = response.usage

        logger.info(
            "answer_generated",
            query=query,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )

        sources = list({chunk['doc_id'] for chunk in chunks})

        return {
            "answer": answer,
            "sources":sources,
            "prompt_tokens":usage.prompt_tokens,
            "completion_tokens":usage.completion_tokens,
        }
    except Exception as e:
        logger.error("answer_generation_failed", query=query, error=str(e))
        raise ValueError(f"Failed to generate answer: {str(e)}")