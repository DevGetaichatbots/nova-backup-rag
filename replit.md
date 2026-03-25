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
- **Separated Agents**: Comparison and Predictive agents are fully independent endpoints
- **DB Connection Pooling**: ThreadedConnectionPool (2-8 connections), batch embedding conversion
- **Session Metadata**: Original PDF filenames stored in `session_metadata` table, used in AI responses instead of generic labels
- **Deployment**: Gunicorn with 1 worker (LLM-bound workload), 300s timeout

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
├── agent.py             # RAG comparison agent with dual vector store querying (GPT-5.2)
├── predictive_agent.py  # Nova Insight predictive agent — currently Module A only (delayed activities)
├── html_formatter.py    # Section-grouped HTML converter for comparison responses (separate card per category)
├── predictive_html_formatter.py  # Dark analytics dashboard HTML for Nova Insight delayed activities report
└── main.py              # FastAPI application with separated agent endpoints + reference date extraction
```

## API Endpoints

### POST /upload - Upload two PDF schedules (for comparison agent)
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

### POST /query - Query the comparison AI agent (comparison-only, no predictive)
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

Response fields: `response`, `sources`, `context_chunks`, `format`

### POST /predictive - Nova Insight delayed activities analysis (standalone, accepts single PDF)
```bash
curl -X POST "https://your-domain/predictive" \
  -F "schedule=@2026-03-12Samlettidsplan.pdf" \
  -F "language=da" \
  -F "format=html"
```
| Field | Description |
|-------|-------------|
| schedule | The PDF schedule file to analyze (filename should start with reference date) |
| language | "da" (Danish) or "en" (English) |
| format | "markdown" or "html" (default: "html") |

Response fields: `predictive_insights` (HTML), `predictive_status`, `predictive_model`, `filename`, `reference_date`, `format`, `processing_time_seconds`

Flow: PDF upload → extract reference date from filename → Azure OCR → build context from table/text chunks → GPT-5.2 Module A analysis → HTML formatting → single response. No vector store or embeddings needed.

### Reference Date Extraction from Filename
The reference date is automatically extracted from the uploaded PDF filename. Supported formats:
- `2026-03-12Samlettidsplan.pdf` → 12-03-2026
- `12-03-2026_schedule.pdf` → 12-03-2026
- `2026.03.12_plan.pdf` → 12-03-2026
- `20260312plan.pdf` → 12-03-2026
- `2026_03_12test.pdf` → 12-03-2026
If no date found in filename, the agent uses the date from the schedule data header or today's date.

### GET /health - Health check

## Comparison Agent Flow
1. User uploads PDF files via `/upload` with a `session_id`
2. Each PDF gets its own vector store table (e.g., `vs_{session_id}_{filename}`)
3. Binary PDF is parsed using Azure Document Intelligence OCR (preserves tables/structure)
4. Text is chunked and embedded via Azure OpenAI
5. Embeddings stored in Supabase pgvector
6. User queries via `/query` with vector store table references
7. Agent retrieves from both stores and provides comparison analysis

## Predictive Agent Flow (Standalone — Currently Module A Only)
1. User uploads a single PDF schedule to `/predictive` (filename contains reference date)
2. Reference date extracted from filename (e.g., "2026-03-12..." → March 12, 2026)
3. PDF is OCR'd using Azure Document Intelligence
4. Table chunks are extracted (falls back to text chunks if no tables found)
5. Context is assembled in the format the predictive LLM expects
6. GPT-5.2 runs Module A: Delayed Activities Identification
7. Response is formatted as dark analytics dashboard HTML with delayed activities table
8. Complete results returned in a single response (~30-90s)

## Table Extraction (Construction Schedules)
- Uses Azure Document Intelligence structured table output (analyzeResult.tables)
- Handles merged cells via rowSpan/columnSpan tracking
- Table chunks include: markdown + embedded structured JSON
- Row chunks include: page_number, cells_data with coordinates
- Format: `TABLE {id} (Pages [...])\n{markdown}\n[STRUCTURED: {json}]`

### Nova Insight — Current Active Module
- **Module A (ACTIVE)**: Delayed Activities Identification
  - Criteria: `Startdato < reference_date AND % arbejde færdigt = 0` (NO Varighed filter — 0d tasks included, only grouping headers excluded)
  - Slutdato = "-" does NOT make a row a summary — only named section headers (Omr. X, E100.XX, Globals) with very high durations are excluded
  - Reference date: extracted from uploaded PDF filename
  - Output: sorted table (most overdue first) with ID, Activity Name, Start Date, End Date, Duration, Progress, Days Overdue
  - Summary: count by area/discipline, top 5 critical delays, professional assessment
  - HTML: light/white theme with teal accents (#0d9488), animated hero stats, severity-colored overdue indicators, clean white cards

### Commented Out Modules (Future Iterations)
- Module B: Unrealistic progress reporting
- Module C: Dependency chain risk analysis
- Module D: Decision bottlenecks
- Module E: Artificial scheduling clusters
- Module F: Long duration risks
- Module G: Discipline progress dashboard
- Schedule Complexity Score
- Predictive Delay Engine (weighted risk score, gauge/bar/donut charts)

### Schedule Format Support (Adaptive)
- **MS Project Export**: `Id | Opgavetilstand | Opgavenavn | Varighed | Startdato | Slutdato | % arbejde færdigt | Foregående opgaver | Efterfølgende opgaver` — match by Id, explicit dependencies
- **Detailtidsplan**: `Id | Entydigt id | Etage | omr. | Ansvarlig | Opgavenavn | Varighed | Startdato | Slutdato | % færdigt | bemærkn.` — match by Entydigt id, has dedicated responsible party + area columns
- **Unstructured Week-based**: `Uge: X` format — match by week + work type
- **Hybrid / Custom**: Any column layout — agents auto-detect columns from header row and adapt
- Both agents use adaptive column mapping: fuzzy-match column names to semantic roles (Task ID, Task Name, Duration, Start, End, Progress, Responsible, Area, Predecessors, Successors, Remarks)
- Missing columns trigger graceful degradation (e.g., no dependency columns → infer chains from hierarchy)
- Extra/renamed columns are handled without breaking analysis
- Date format variations handled: "ma 05-01-26", "01-03-2022", "05-01-26"
- Duration format variations handled: "50d", "10 d", "3u", "3 u", "74.38d", "16,24d"

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
