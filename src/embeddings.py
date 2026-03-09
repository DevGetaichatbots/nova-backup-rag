import logging
from openai import AzureOpenAI
from src.config import settings

logger = logging.getLogger(__name__)

MAX_EMBEDDING_TOKENS = 8000
MAX_CHARS = MAX_EMBEDDING_TOKENS * 3


def get_azure_openai_client():
    return AzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
    )


def truncate_text(text: str, max_chars: int = MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    logger.warning(f"  Truncating text from {len(text)} to {max_chars} chars for embedding")
    return text[:max_chars]


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    client = get_azure_openai_client()
    
    safe_texts = [truncate_text(t) for t in texts]
    
    embeddings = []
    batch_size = 16
    
    for i in range(0, len(safe_texts), batch_size):
        batch = safe_texts[i:i + batch_size]
        response = client.embeddings.create(
            model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            input=batch
        )
        
        for item in response.data:
            embeddings.append(item.embedding)
    
    return embeddings


def generate_single_embedding(text: str) -> list[float]:
    client = get_azure_openai_client()
    
    safe_text = truncate_text(text)
    
    response = client.embeddings.create(
        model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
        input=safe_text
    )
    
    return response.data[0].embedding
