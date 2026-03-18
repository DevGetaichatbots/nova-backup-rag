# RAG Agent SaaS

## Overview
A Python-based RAG (Retrieval-Augmented Generation) Agent SaaS application that replicates the n8n Azure AI RAG workflow using Supabase pgvector instead of Azure AI Search.

## Architecture
- **Framework**: FastAPI
- **Vector Store**: Supabase with pgvector extension
- **Embeddings**: Azure OpenAI text-embedding-3-small
- **LLM (Comparison)**: Azure OpenAI GPT-5.2 (`AZURE_OPENAI_CHAT_DEPLOYMENT`)
- **LLM (Predictive)**: Azure OpenAI GPT-5.2 (`AZURE_OPENAI_PREDICTIVE_DEPLOYMENT`) — Nova Insight
- **PDF Processing**: Azure Document Intelligence OCR + LangChain text splitters
- **Dual-Agent**: Both agents run in parallel via `asyncio.gather`, single response (~60s), no polling needed
- **DB Connection Pooling**: ThreadedConnectionPool (2-8 connections), batch embedding conversion
- **Session Metadata**: Original PDF filenames stored in `session_metadata` table, used in AI responses instead of generic labels

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
├── agent.py             # RAG agent with dual vector store querying (GPT-5.2)
├── predictive_agent.py  # Nova Insight predictive risk agent (GPT-5.2)
├── html_formatter.py    # Section-grouped HTML converter for comparison responses (separate card per category)
├── predictive_html_formatter.py  # Module-card HTML converter for Nova Insight reports
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

## Query Response (Parallel Dual-Agent)
Both agents run in parallel via `asyncio.gather` — response time = max(comparison, predictive), not sum.
For comparison queries, the `/query` endpoint returns everything in a single response:
- `response` — GPT-5.2 comparison analysis
- `predictive_insights` — GPT-5.2 Nova Insight predictive report
- `predictive_status` — "success" or "error"
- `predictive_model` — model name used for predictions
- Non-comparison queries skip the predictive agent entirely
- Both agents use `reasoning_effort="low"` for optimal speed

### Nova Insight Modules (GPT-5.2, CTCO-optimized prompt)
- **Module A**: Overdue activities (Startdato < reference_date AND % arbejde færdigt = 0 AND Varighed > 0)
- **Module B**: Unrealistic progress reporting (deviation > 25%, over/under-reported sub-types)
- **Module C**: Dependency chain risk — uses REAL dependency graph from Foregående/Efterfølgende opgaver columns (semicolon-separated task IDs), chains > 4 tasks
- **Module D**: Decision bottlenecks (Varighed = 0d + Danish/English decision keywords + BH client tasks + has successors)
- **Module E**: Artificial scheduling clusters (5+ tasks same Startdato per Omr./area, distinguishes coordination milestones from work clusters)
- **Module F**: Long duration risks (Varighed > 90 days elevated, > 120 days critical, excludes summary rows)
- **Module G**: Discipline progress dashboard (grouped by E100.XX prefix + responsible party annotations, health scoring)
- **Schedule Health Overview**: Quick-glance summary of all findings
- **Complexity Score**: Low/Medium/High/Very High (activities + areas + disciplines + chain depth + dependency links)
- **Predictive Delay Engine**: weighted risk score, risk %, delay window, primary risk source
- **Prompt optimizations**: CTCO framework, few-shot examples from real data, reasoning_effort=low, temperature=1, 32K output tokens

### Schedule Format Support
- **MS Project Export** (PRIMARY): `Id | Opgavetilstand | Opgavenavn | Varighed | Startdato | Slutdato | % arbejde færdigt | Foregående opgaver | Efterfølgende opgaver` — match by Id, explicit dependencies
- **Detailtidsplan**: `Id | Entydigt id | Etage | omr. | Ansvarlig | Opgavenavn | ...` — match by Entydigt id
- **Unstructured Week-based**: `Uge: X` format — match by week + work type
- Both agents auto-detect document type from column headers

## Environment Variables Required
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_KEY` - Supabase service role key
- `SUPABASE_DB_HOST` - Database host
- `SUPABASE_DB_PASSWORD` - Database password
- `SUPABASE_POOLER_URL` - Supabase connection pooler URL (port 6543)
- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` - Embedding model deployment name
- `AZURE_OPENAI_CHAT_DEPLOYMENT` - Chat model deployment name (GPT-5.2 comparison)
- `AZURE_OPENAI_PREDICTIVE_DEPLOYMENT` - Predictive model deployment name (GPT-5.2 Nova Insight)
- `AZURE_DOC_INTELLIGENCE_ENDPOINT` - Azure Document Intelligence endpoint
- `AZURE_DOC_INTELLIGENCE_KEY` - Azure Document Intelligence API key

## Running
```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 5000 --reload
```
