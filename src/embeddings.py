from openai import AzureOpenAI
from src.config import settings


def get_azure_openai_client():
    return AzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
    )


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    client = get_azure_openai_client()
    
    embeddings = []
    batch_size = 16
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(
            model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            input=batch
        )
        
        for item in response.data:
            embeddings.append(item.embedding)
    
    return embeddings


def generate_single_embedding(text: str) -> list[float]:
    client = get_azure_openai_client()
    
    response = client.embeddings.create(
        model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
        input=text
    )
    
    return response.data[0].embedding
