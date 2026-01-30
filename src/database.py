import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from src.config import settings, get_database_url


@contextmanager
def get_db_connection():
    conn = psycopg2.connect(
        host=settings.SUPABASE_DB_HOST,
        port=settings.SUPABASE_DB_PORT,
        database=settings.SUPABASE_DB_NAME,
        user=settings.SUPABASE_DB_USER,
        password=settings.SUPABASE_DB_PASSWORD
    )
    try:
        yield conn
    finally:
        conn.close()


def init_pgvector_extension():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            conn.commit()


def create_vector_table(table_name: str, dimension: int = 1536):
    safe_table_name = table_name.replace("-", "_").replace(" ", "_")
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {safe_table_name} (
                    id SERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector({dimension}),
                    metadata JSONB DEFAULT '{{}}',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS {safe_table_name}_embedding_idx 
                ON {safe_table_name} USING hnsw (embedding vector_cosine_ops);
            """)
            
            conn.commit()
    
    return safe_table_name


def insert_embeddings(table_name: str, documents: list):
    safe_table_name = table_name.replace("-", "_").replace(" ", "_")
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for doc in documents:
                embedding_str = "[" + ",".join(map(str, doc["embedding"])) + "]"
                cur.execute(f"""
                    INSERT INTO {safe_table_name} (content, embedding, metadata)
                    VALUES (%s, %s::vector, %s::jsonb)
                """, (doc["content"], embedding_str, doc.get("metadata", "{}")))
            conn.commit()


def similarity_search(table_name: str, query_embedding: list, top_k: int = 5):
    safe_table_name = table_name.replace("-", "_").replace(" ", "_")
    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f"""
                SELECT 
                    id,
                    content,
                    metadata,
                    1 - (embedding <=> %s::vector) AS similarity
                FROM {safe_table_name}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (embedding_str, embedding_str, top_k))
            
            results = cur.fetchall()
    
    return results


def create_chat_memory_table():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_memory (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS chat_memory_session_idx 
                ON chat_memory(session_id);
            """)
            conn.commit()


def save_chat_message(session_id: str, role: str, content: str):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO chat_memory (session_id, role, content)
                VALUES (%s, %s, %s)
            """, (session_id, role, content))
            conn.commit()


def get_chat_history(session_id: str, limit: int = 10):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT role, content, created_at
                FROM chat_memory
                WHERE session_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (session_id, limit))
            
            results = cur.fetchall()
    
    return list(reversed(results))
