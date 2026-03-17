import logging
import tiktoken
from openai import AzureOpenAI
from src.config import settings

logger = logging.getLogger(__name__)

MAX_TOKENS = 8000

try:
    _encoder = tiktoken.encoding_for_model("text-embedding-3-small")
except Exception:
    _encoder = tiktoken.get_encoding("cl100k_base")


def get_azure_openai_client():
    return AzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
    )


def count_tokens(text: str) -> int:
    return len(_encoder.encode(text))


def truncate_text(text: str, max_tokens: int = MAX_TOKENS) -> str:
    tokens = _encoder.encode(text)
    if len(tokens) <= max_tokens:
        return text
    logger.warning(f"  Truncating text from {len(tokens)} to {max_tokens} tokens for embedding")
    return _encoder.decode(tokens[:max_tokens])


def split_oversized_text(text: str, max_tokens: int = MAX_TOKENS) -> list[str]:
    tokens = _encoder.encode(text)
    if len(tokens) <= max_tokens:
        return [text]

    lines = text.split("\n")
    parts = []
    current_part = ""
    current_tokens = 0

    for line in lines:
        line_tokens = len(_encoder.encode(line + "\n"))
        if current_tokens + line_tokens > max_tokens and current_part:
            parts.append(current_part.rstrip("\n"))
            current_part = ""
            current_tokens = 0
        current_part += line + "\n"
        current_tokens += line_tokens

    if current_part.strip():
        part_tokens = len(_encoder.encode(current_part))
        if part_tokens <= max_tokens:
            parts.append(current_part.rstrip("\n"))
        else:
            remaining_tokens = _encoder.encode(current_part)
            for i in range(0, len(remaining_tokens), max_tokens):
                parts.append(_encoder.decode(remaining_tokens[i:i + max_tokens]))

    logger.info(f"  Split oversized chunk ({len(tokens)} tokens) into {len(parts)} parts")
    return parts


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    client = get_azure_openai_client()
    
    safe_texts = [truncate_text(t) for t in texts]
    
    embeddings = []
    batch_size = 100
    
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
