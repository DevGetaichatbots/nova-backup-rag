# RAG Agent SaaS

## Overview
A Python-based RAG (Retrieval-Augmented Generation) Agent SaaS application that replicates the n8n Azure AI RAG workflow using Supabase pgvector instead of Azure AI Search.

## Architecture
- **Framework**: FastAPI
- **Vector Store**: Supabase with pgvector extension
- **Embeddings**: Azure OpenAI text-embedding-3-small
- **LLM (Comparison)**: Azure OpenAI GPT-4.1 (`AZURE_OPENAI_CHAT_DEPLOYMENT`)
- **LLM (Predictive)**: Azure OpenAI GPT-5.1 (`AZURE_OPENAI_PREDICTIVE_DEPLOYMENT`) — Nova Insight
- **PDF Processing**: Azure Document Intelligence OCR + LangChain text splitters
- **Multi-LLM**: Both models run in parallel on comparison queries via `asyncio.gather`

## Project Structure
```
src/
├── __init__.py          # Package init
├── config.py            # Configuration and settings
├── database.py          # Supabase/PostgreSQL database operations with SQL injection protection
├── embeddings.py        # Azure OpenAI embedding generation
├── azure_ocr.py         # Azure Document Intelligence OCR for PDF table extraction
├── pdf_processor.py     # PDF processing with Azure Document Intelligence OCR
├── vector_store.py      # Vector store management
├── agent.py             # RAG agent with dual vector store querying (GPT-4.1)
├── predictive_agent.py  # Nova Insight predictive risk agent (GPT-5.1)
└── main.py              # FastAPI application with parallel agent execution
```

## API Endpoints

### POST /upload - Upload two PDF schedules
```bash
curl -X POST "https://your-domain/upload" \
  -F "session_id=session_abc123" \
  -F "old_session_id=table_old_xyz789" \
  -F "old_schedule=@old_schedule.pdf" \
  -F "new_session_id=table_new_xyz123" \
  -F "new_schedule=@new_schedule.pdf"
```
| Field | Description |
|-------|-------------|
| session_id | Main chat session ID |
| old_session_id | Vector store table name for old file |
| old_schedule | The old PDF file |
| new_session_id | Vector store table name for new file |
| new_schedule | The new PDF file |

### POST /query - Query the AI agent
```bash
curl -X POST "https://your-domain/query" \
  -F "query=Compare the two schedules" \
  -F "vs_table=session_abc123" \
  -F "language=da" \
  -F "old_session_id=table_old_xyz789" \
  -F "new_session_id=table_new_xyz123" \
  -F "format=html"
```
| Field | Description |
|-------|-------------|
| query | User's question |
| vs_table | Main session ID (for chat history) |
| language | "da" (Danish) or "en" (English) |
| old_session_id | Reference to old file's vector store |
| new_session_id | Reference to new file's vector store |
| format | "markdown" (default) or "html" (premium styled) |

### GET /health - Health check

## Flow
1. User uploads PDF files via `/upload` with a `session_id`
2. Each PDF gets its own vector store table (e.g., `vs_{session_id}_{filename}`)
3. Binary PDF is parsed using Azure Document Intelligence OCR (preserves tables/structure)
4. Text is chunked and embedded via Azure OpenAI
5. Embeddings stored in Supabase pgvector
6. User queries via `/query` with list of vector store tables
7. Agent retrieves from both stores and provides comparison analysis

## Table Extraction (Construction Schedules)
- Uses Azure Document Intelligence structured table output (analyzeResult.tables)
- Handles merged cells via rowSpan/columnSpan tracking
- Table chunks include: markdown + embedded structured JSON
- Row chunks include: page_number, cells_data with coordinates
- Format: `TABLE {id} (Pages [...])\n{markdown}\n[STRUCTURED: {json}]`

## Query Response (Multi-LLM)
For comparison queries, the `/query` endpoint returns:
- `response` — GPT-4.1 comparison analysis (existing field)
- `predictive_insights` — GPT-5.1 Nova Insight predictive report (new field)
- `predictive_model` — model name used for predictions
- Non-comparison queries skip the predictive agent entirely

### Nova Insight Modules (GPT-5.1)
- **Module A**: Overdue activities (Startdato past, % færdigt = 0)
- **Module B**: Unrealistic progress reporting (|Expected - Reported| > 25%)
- **Module C**: Dependency chain risk (inferred from floor/date sequencing, best-effort)
- **Module D**: Decision bottlenecks (Varighed = 0, approval keywords)
- **Module E**: Artificial scheduling clusters (5+ tasks same Startdato)
- **Module F**: Long duration risks (Varighed > 90 days)
- **Module G**: Discipline progress dashboard (grouped by Ansvarlig)
- **Complexity Score**: Low/Medium/High/Very High
- **Predictive Delay Engine**: risk %, delay window, primary risk source

## Environment Variables Required
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_KEY` - Supabase service role key
- `SUPABASE_DB_HOST` - Database host
- `SUPABASE_DB_PASSWORD` - Database password
- `SUPABASE_POOLER_URL` - Supabase connection pooler URL (port 6543)
- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` - Embedding model deployment name
- `AZURE_OPENAI_CHAT_DEPLOYMENT` - Chat model deployment name (GPT-4.1 comparison)
- `AZURE_OPENAI_PREDICTIVE_DEPLOYMENT` - Predictive model deployment name (GPT-5.1 Nova Insight)
- `AZURE_DOC_INTELLIGENCE_ENDPOINT` - Azure Document Intelligence endpoint
- `AZURE_DOC_INTELLIGENCE_KEY` - Azure Document Intelligence API key

## Running
```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 5000 --reload
```
