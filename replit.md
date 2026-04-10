# RAG Agent SaaS

## Overview
This project is a Python-based SaaS application that implements a RAG (Retrieval-Augmented Generation) agent. Its core purpose is to analyze and compare construction project schedules provided as PDF documents. It leverages Supabase pgvector for vector storage and Azure AI services for embeddings, language models, and document intelligence. The application offers two main functionalities: comparing two schedules and providing predictive insights into potential delays in a single schedule. The business vision is to provide advanced decision support for project managers by transforming complex schedule data into actionable insights, thereby improving project efficiency and reducing risks.

## User Preferences
I prefer that the agent focuses on critical details and architectural decisions.
I want to be able to understand the core functionality and how different components interact without getting lost in excessive implementation specifics.
I expect the agent to use clear and concise language in its responses and explanations.
I want the agent to prioritize high-level summaries and avoid redundant information.
I want the agent to consolidate similar concepts and eliminate repetition.
The agent should maintain deterministic behavior using fixed LLM settings for reproducibility.
The agent should provide structured and formatted outputs, especially for predictive analysis, to enable direct mapping to UI elements.

## System Architecture
The application is built on FastAPI, providing a robust API for handling schedule uploads and queries. Supabase with the pgvector extension is used as the primary vector store for efficient similarity searches. Azure OpenAI's `text-embedding-3-small` model generates embeddings, while GPT-4.1 (`AZURE_OPENAI_CHAT_DEPLOYMENT` and `AZURE_OPENAI_PREDICTIVE_DEPLOYMENT`) serves as the core LLM for both comparison and predictive analysis. PDF processing is handled by Azure Document Intelligence for OCR and LangChain for text splitting.

The system features two independent agents: a Comparison Agent and a Predictive Agent, each with dedicated endpoints. Database connection pooling is managed via `ThreadedConnectionPool` for optimal performance. Session metadata, including original PDF filenames, is stored to enhance AI responses. Predictive outputs strictly adhere to a JSON schema for deterministic, structured results that can be directly mapped to HTML. Both LLM agents operate with deterministic settings (`temperature=0`, `top_p=0.1`, `seed=42`). The comparison agent uses `max_tokens=65536` to ensure complete table output for large schedules (200+ tasks). The predictive agent uses `max_tokens=32768`. The application is deployed with Gunicorn, configured for LLM-bound workloads.

**UI/UX Decisions (Predictive Agent HTML Theme):**
- Light/white theme with teal accents (`#0d9488`).
- Hero section displays delayed count, priority breakdown (critical/important/monitor dots), progress bar, and root cause count.
- Section cards are color-coded with icons for different insights (e.g., teal for management, red for delays).
- Priority badges use red for "CRITICAL NOW," amber for "IMPORTANT NEXT," and cyan for "MONITOR."
- Task type badges are color-coded (e.g., purple for "Coordination," blue for "Design").
- Severity-colored overdue indicators are used within tables.

**Technical Implementations & Feature Specifications:**
- **Comparison Agent:** Processes two PDF or CSV schedules, creates separate vector store tables for each, and uses dual vector store querying to provide comparison analysis. Output includes a mandatory six-section format: EXECUTIVE_ACTIONS (3-5 recommended actions as decision support), COMPARISON TABLES (with priority tags on delayed/removed tasks), ROOT_CAUSE_ANALYSIS (categorizes why delays exist, manpower assessment), IMPACT_ASSESSMENT (downstream consequences per critical finding), SUMMARY_OF_CHANGES, and PROJECT_HEALTH. The Executive Actions section frames output as "Recommended Actions" (not commands), each with mandatory WHY explanation, PRIORITY (🔴Critical/🟠Important/🟢Low), EFFORT estimate (e.g. "1 hour", "Half day"), ROLE (Project Manager/Planner/Site Manager/Discipline Lead), and RELATED task IDs. This transforms raw data into a decision support engine — the PM knows exactly what to do next and why.
- **Predictive Agent (Nova Insight):** Analyzes a single PDF or CSV schedule to identify delayed activities, perform root cause analysis, prioritize actions, assess resources, and evaluate forcing options.
- **File Processing (Unified Format):** Supports both PDF and CSV inputs. Both are converted to the same compact CSV format at upload time — semicolon-separated values, header row per chunk, 250 rows per chunk, stored as `type="table"` with zero-vector placeholders (fetch-all retrieval, not similarity search). PDFs are processed via Azure Document Intelligence OCR which extracts structured tables, then `_ocr_tables_to_compact_csv_chunks()` in `pdf_processor.py` converts OCR table rows to compact CSV (same format as CSV upload). CSVs are parsed directly (no OCR needed). No embedding API calls for either format. Context sent to LLM is capped at 1.9MB (MAX_CONTEXT_BYTES=1,900,000) to stay safely within the 1,047,576 token model limit after accounting for system prompt and output tokens. Both agents (comparison and predictive) send ALL data to the LLM. Auto-retry on context_length_exceeded reduces context to 85% and strips chat history. The comparison agent's `_retrieve_context` always fetches `type="table"` chunks only — no fallback logic.
- **Reference Date Extraction:** Automatically extracts reference dates from PDF filenames using various formats.
- **Predictive Output Structure:** Generates a comprehensive report with sections: `EXECUTIVE_ACTIONS` (Top 3 priorities), `MANAGEMENT_CONCLUSION`, `SCHEDULE_OVERVIEW`, `DELAYED_ACTIVITIES`, `ROOT_CAUSE_ANALYSIS`, `PRIORITY_ACTIONS`, `RESOURCE_ASSESSMENT`, `FORCING_ASSESSMENT`, and `SUMMARY_BY_AREA`.
- **Executive Actions (Top 3):** Synthesizes all analysis into exactly 3 concrete action items with WHO (responsible party), WHAT (direct instruction), WHEN (real calendar date with day name, e.g. "Torsdag d. 3. april 2026" — based on today's injected date), related task IDs, and a prominent manpower indicator showing whether adding people will help or is useless (with explanation). Deadlines are shown inline with the action text, not as a separate field.
- **Module A Detection Criteria:** Identifies delayed activities based on start date, completion percentage, and reference date.
- **Task Type Classification:** Classifies tasks into categories such as "Coordination," "Design," "Bygherre," "Production," "Procurement," and "Milestone."
- **Priority Levels:** Assigns "CRITICAL NOW," "IMPORTANT NEXT," or "MONITOR" priorities based on impact and urgency.
- **Module F Forcing Assessment:** Evaluates the feasibility of accelerating "CRITICAL NOW" and "IMPORTANT NEXT" tasks, considering constraints, coordination costs, parallelizability, and optimal team size.
- **Adaptive Schedule Format Support:** The agents automatically detect and adapt to various schedule formats (e.g., MS Project Export, Detailtidsplan, unstructured week-based) by fuzzy-matching column names to semantic roles. It gracefully handles missing, extra, or renamed columns and various date/duration formats.

## External Dependencies
- **Supabase:** Used for database services and `pgvector` extension for vector storage.
- **Azure OpenAI:**
    - `text-embedding-3-small`: For generating embeddings.
    - GPT-4.1 (`AZURE_OPENAI_CHAT_DEPLOYMENT`): For the comparison agent.
    - GPT-4.1 (`AZURE_OPENAI_PREDICTIVE_DEPLOYMENT`): For the predictive (Nova Insight) agent.
- **Azure Document Intelligence:** For Optical Character Recognition (OCR) and structured table extraction from PDFs.
- **LangChain:** Utilized for text splitting during PDF processing.