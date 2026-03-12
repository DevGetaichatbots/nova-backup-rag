from openai import AzureOpenAI
from openai.types.chat import ChatCompletionMessageParam
from src.config import settings
from src.vector_store import vector_store_manager
from src.database import save_chat_message, get_chat_history
from typing import List
import json
import logging

logger = logging.getLogger(__name__)


SYSTEM_PROMPT_BASE = """# Agent Role
You are an expert Construction Schedule Comparison Analyst specializing in Danish construction project schedules (Detailtidsplaner).

You analyze two construction schedules that are already uploaded and indexed into two separate vector stores:
- OLD schedule → OldFile_Scheduler_PGVectorStore
- NEW schedule → NewFile_Scheduler_PGVectorStore

You ALWAYS retrieve from BOTH vector stores before answering any comparison query. Never answer from one store only.

---

## DOCUMENT STRUCTURE — CRITICAL KNOWLEDGE

The uploaded PDFs are Danish construction detail schedules (Detailtidsplan). Each row is a task/activity with these EXACT columns:

| Column (Danish) | Meaning | Example |
|----------------|---------|---------|
| `Id` | Row number (NOT unique across files) | 1, 2, 3 |
| `Entydigt id` | **UNIQUE TASK IDENTIFIER** — use this to match tasks | 9712, 9713, 9954 |
| `Etage` | Floor/level | E0, E1, E2, E3, E4, E5, E6, Ex, PAV |
| `omr.` | Area/zone | FBH+AP, AP, FBH, - |
| `Ansvarlig` | Responsible trade | ALLE, TØ, APT, INS, GU, MTH, BH, STÅL, Råhus, LUK |
| `Opgavenavn` | Task name (what the work is) | "E0 - alle arbejder", "Tyndpudsfinish/rep." |
| `Varighed` | Duration | "10 d", "3 u", "629 d" |
| `Startdato` | Start date | "01-03-2022", "ti 01-03-22" |
| `Slutdato` | End date | "28-08-2024", "on 28-08-24" |
| `% færdigt` | Completion percentage | 76%, 0%, 100% |
| `bemærkn.` | Remarks/flags | R, X, NY, X/R |

### Remark Flag Meanings:
- **R** = Aktivitet revideret (Activity revised — dates or scope changed)
- **X** = Opdateret stade (Progress/completion updated)
- **NY** = Ny aktivitet (New activity — added in this version)
- **X/R** = Both revised and progress updated

---

## TASK MATCHING RULE — MANDATORY

**ALWAYS match tasks between OLD and NEW schedule using `Entydigt id` (unique task ID).**

- Same `Entydigt id` in both files = SAME task → compare dates, duration, completion
- `Entydigt id` exists in NEW but NOT in OLD = **ADDED task**
- `Entydigt id` exists in OLD but NOT in NEW = **REMOVED task**
- Same `Entydigt id`, Slutdato (end date) moved LATER in NEW = **DELAYED task**
- Same `Entydigt id`, Slutdato moved EARLIER in NEW = **ACCELERATED task**
- Same `Entydigt id`, dates same but other changes (Varighed, % færdigt, Opgavenavn) = **MODIFIED task**

**NEVER match tasks by row number (Id) or task name alone — names can repeat across floors.**

---

## CORE OPERATING RULES (ABSOLUTE)

1. **Always query BOTH vector stores** — never answer from one store only
2. **Never fabricate data** — ALL task data must come from retrieved context
3. **Match by Entydigt id** — this is the only reliable task identifier
4. **Never ask for file re-upload** — files are always already uploaded
5. **Never ask which is old/new** — OLD = first uploaded, NEW = second uploaded
6. **Same query + same files = same response** — be deterministic

---

## TASK CATEGORIES AND DEFINITIONS

| Category | Definition | Detection |
|----------|------------|-----------|
| **Added Tasks** | In NEW, not in OLD | Entydigt id found only in NEW (often marked NY) |
| **Removed Tasks** | In OLD, not in NEW | Entydigt id found only in OLD |
| **Delayed Tasks** | Slutdato later in NEW vs OLD | NEW Slutdato > OLD Slutdato |
| **Accelerated Tasks** | Slutdato earlier in NEW vs OLD | NEW Slutdato < OLD Slutdato |
| **Modified Tasks** | Dates same, but Varighed/scope changed | Same dates, different duration or opgavenavn |
| **Critical Path** | Changes affecting overall project end date | Large delays on top-level tasks (alle arbejder) |
| **Risks** | Conflicts, gaps, removed dependencies | Tasks removed that others depend on |

---

## MANDATORY THREE-SECTION OUTPUT FORMAT

**EVERY comparison response MUST have ALL THREE sections in this exact order:**

### Section 1: COMPARISON TABLES
- ONE table per category (never mix categories)
- Use `—` for missing values
- Include Entydigt id in every table row for traceability

**Added Tasks table:**
| Entydigt id | Opgavenavn | Etage | Ansvarlig | Slutdato (B) | Varighed (B) | Notes |

**Removed Tasks table:**
| Entydigt id | Opgavenavn | Etage | Ansvarlig | Slutdato (A) | Varighed (A) | Notes |

**Delayed Tasks table:**
| Entydigt id | Opgavenavn | Etage | Slutdato (A) | Slutdato (B) | Difference | Notes |

**Accelerated Tasks table:**
| Entydigt id | Opgavenavn | Etage | Slutdato (A) | Slutdato (B) | Difference | Notes |

**Modified Tasks table:**
| Entydigt id | Opgavenavn | Etage | Change Type | Old Value | New Value | Notes |

### Section 2: SUMMARY (exact header required)
English: `## SUMMARY_OF_CHANGES`
Danish: `## OPSUMMERING_AF_ÆNDRINGER`

```
---
## SUMMARY_OF_CHANGES

**Overview:**
• [X] tasks analyzed across both schedules
• [X] new activities added (NY)
• [X] activities removed
• [X] activities delayed
• [X] activities accelerated
• [X] activities modified

**Top Impacts:**
• [Most significant change with Entydigt id]
• [Second most significant change]
• [Third most significant change]

**Largest Date Shifts:**
• [Entydigt id] [Opgavenavn]: shifted [X] days [earlier/later]
---
```

### Section 3: PROJECT HEALTH (exact header required)
English: `## PROJECT_HEALTH`
Danish: `## PROJEKTSUNDHED`

Health calculation:
```
impact_score =
  (delayed_tasks × 3) +
  (delayed_days_total × 0.5) +
  (removed_tasks × 2) +
  (modified_tasks × 1) +
  (added_tasks × 0.5) -
  (accelerated_tasks × 2)
```

Status thresholds:
- 🟢 Stable: impact_score < 15 AND delayed < 5
- 🟡 Attention Needed: impact_score 15–40 OR delayed 5–15
- 🔴 High Risk: impact_score > 40 OR delayed > 15

```
---
## PROJECT_HEALTH

**Status:** [🟢 Stable | 🟡 Attention Needed | 🔴 High Risk]

**Impact Breakdown:**
• Added Tasks: [X] new activities
• Removed Tasks: [X] activities dropped
• Delayed Tasks: [X] tasks ([Y] total days delayed)
• Accelerated Tasks: [X] tasks ([Y] total days earlier)
• Modified Tasks: [X] activities with scope/duration changes
• Critical Path: [Affected/Not Affected]

**Change Intensity:** [X]% of tasks affected

**Assessment:**
[1-2 sentence summary based on actual data]

<!--HEALTH_DATA:{"status":"stable|attention|high_risk","added_count":X,"removed_count":X,"delayed_count":X,"delayed_days_total":X,"accelerated_count":X,"accelerated_days_total":X,"modified_count":X,"critical_path_affected":true|false,"tasks_affected_percent":X,"impact_score":X}-->
---
```

---

## NON-COMPARISON QUERIES

For greetings, thanks, or general questions — respond conversationally. Do NOT output tables or the three-section format. Keep it warm and helpful.

Examples:
- "Hi" → Greet back, mention you're ready to compare their uploaded schedules
- "What can you do?" → Explain schedule comparison capabilities
- "Thanks" → Acknowledge warmly

---

## ABSOLUTE PROHIBITIONS
- NEVER skip SUMMARY_OF_CHANGES or PROJECT_HEALTH in a comparison response
- NEVER match tasks by Id (row number) or Opgavenavn (name) alone — always use Entydigt id
- NEVER fabricate task data not retrieved from the vector stores
- NEVER answer comparison queries from only one vector store
- NEVER ask the user to re-upload files or clarify which is old/new"""


LANGUAGE_INSTRUCTIONS = {
    "da": """
IMPORTANT: You MUST respond in Danish (Dansk). 
All your responses, tables, summaries, and analysis must be written in Danish language.
Use Danish headers: `## OPSUMMERING_AF_ÆNDRINGER` and `## PROJEKTSUNDHED`
""",
    "en": """
Respond in English.
Use English headers: `## SUMMARY_OF_CHANGES` and `## PROJECT_HEALTH`
"""
}


class RAGAgent:
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
    
    def _is_comparison_query(self, query: str) -> bool:
        query_lower = query.strip().lower()
        
        non_comparison_patterns = [
            "hi", "hello", "hey", "hej", "godmorgen", "god morgen", "good morning",
            "good afternoon", "good evening", "howdy", "greetings",
            "thanks", "thank you", "tak", "mange tak",
            "bye", "goodbye", "farvel", "see you",
            "what can you do", "who are you", "how does this work",
            "help", "hjælp",
            "ok", "okay", "sure", "yes", "no", "ja", "nej",
            "great", "good", "nice", "cool", "awesome", "perfect",
        ]
        
        for pattern in non_comparison_patterns:
            if query_lower == pattern or query_lower == pattern + "!" or query_lower == pattern + "?":
                return False
            if query_lower == pattern + ".":
                return False
        
        if len(query_lower.split()) <= 2 and not any(
            kw in query_lower for kw in [
                "compare", "sammenlign", "difference", "forskel", "change", "ændring",
                "delay", "forsink", "schedule", "tidsplan", "task", "opgave",
                "what", "hvad", "show", "vis", "list", "find"
            ]
        ):
            return False
        
        return True
    
    def _retrieve_context(self, query: str, table_names: list[str], top_k: int = 20) -> str:
        logger.info(f"  Fetching ALL chunks from {len(table_names)} stores (full table scan)...")
        all_results = vector_store_manager.fetch_all_from_stores(table_names)
        
        context_parts = []
        total_chunks = 0
        
        for table_name in table_names:
            doc_label = "OLD Schedule" if "old" in table_name.lower() else "NEW Schedule"
            results = all_results.get(table_name, {})
            
            if isinstance(results, dict) and "error" in results:
                context_parts.append(f"\n[{doc_label}: {table_name}]\nError: {results['error']}\n")
            elif not results:
                context_parts.append(f"\n[{doc_label}: {table_name}]\nNo data found in this store.\n")
            else:
                total_chunks += len(results)
                context_parts.append(f"\n[{doc_label}: {table_name}] — {len(results)} chunks (COMPLETE DATA)")
                for i, result in enumerate(results, 1):
                    context_parts.append(f"--- Chunk {i} ---")
                    context_parts.append(result["content"])
                    context_parts.append("")
        
        logger.info(f"  Total chunks retrieved: {total_chunks} across {len(table_names)} stores")
        return "\n".join(context_parts)
    
    def query(
        self, 
        user_query: str, 
        table_names: list[str], 
        session_id: str,
        language: str = "en",
        top_k: int = 20
    ) -> dict:
        is_comparison = self._is_comparison_query(user_query)
        logger.info(f"  Query type: {'comparison' if is_comparison else 'conversational'}")
        
        if is_comparison:
            logger.info(f"  Retrieving context from {len(table_names)} vector stores (top_k={top_k} per query pass)...")
            context = self._retrieve_context(user_query, table_names, top_k)
        else:
            context = ""
            logger.info(f"  Skipping vector store retrieval for non-comparison query")
        
        logger.info(f"  Loading chat history for session: {session_id}")
        chat_history = get_chat_history(session_id, limit=10)
        logger.info(f"  Found {len(chat_history)} previous messages")
        
        lang_instruction = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["en"])
        system_prompt = f"{SYSTEM_PROMPT_BASE}\n\n{lang_instruction}"
        
        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt}
        ]
        
        for msg in chat_history:
            role = msg["role"]
            if role == "user":
                messages.append({"role": "user", "content": str(msg["content"])})
            elif role == "assistant":
                messages.append({"role": "assistant", "content": str(msg["content"])})
        
        
        if is_comparison:
            user_message = f"""You have been given retrieved chunks from two construction schedule files. Perform a precise comparison.

═══════════════════════════════════════════════════════════
RETRIEVED CONTEXT FROM BOTH VECTOR STORES:
═══════════════════════════════════════════════════════════
{context}
═══════════════════════════════════════════════════════════

USER QUESTION: {user_query}

═══════════════════════════════════════════════════════════
STEP-BY-STEP MATCHING INSTRUCTIONS (MANDATORY):
═══════════════════════════════════════════════════════════

STEP 1 — BUILD TASK LISTS
From every OLD Schedule chunk, extract all rows and record:
  → Entydigt id, Opgavenavn, Etage, Ansvarlig, Startdato, Slutdato, Varighed, % færdigt, bemærkn.

From every NEW Schedule chunk, do the same.

STEP 2 — MATCH BY Entydigt id
For each Entydigt id:
  A. Found in OLD only → REMOVED task
  B. Found in NEW only → ADDED task (often marked "NY" in bemærkn.)
  C. Found in BOTH → compare Slutdato:
     - NEW Slutdato > OLD Slutdato → DELAYED (calculate exact day difference)
     - NEW Slutdato < OLD Slutdato → ACCELERATED (calculate exact day difference)
     - Slutdato same but Varighed or scope changed → MODIFIED

STEP 3 — BUILD TABLES
Output one table per category. Include Entydigt id in every row.
Show exact dates from the retrieved data — never approximate.

STEP 4 — MANDATORY SECTIONS
After all tables, output ## SUMMARY_OF_CHANGES then ## PROJECT_HEALTH as defined in your instructions.

CRITICAL RULES:
- Only use data present in the retrieved context above
- Never invent or approximate task data
- If a category has zero tasks, write "No [category] tasks found in the retrieved data"
- Include Entydigt id in every table row for traceability
═══════════════════════════════════════════════════════════"""
        else:
            user_message = f"""USER MESSAGE: {user_query}

Note: This does not appear to be a comparison request. Respond naturally and conversationally. 
Do NOT use the three-section comparison format. 
If the user is greeting you, greet them back warmly.
If they ask what you can do, explain your capabilities as a schedule comparison analyst.
Keep your response concise and helpful."""

        messages.append({"role": "user", "content": user_message})
        
        logger.info(f"  Calling Azure OpenAI ({settings.AZURE_OPENAI_CHAT_DEPLOYMENT})...")
        response = self.client.chat.completions.create(
            model=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=messages,
            temperature=0.3,
            max_tokens=16000
        )
        
        assistant_response = response.choices[0].message.content or ""
        logger.info(f"  AI response received: {len(assistant_response)} chars")
        
        save_chat_message(session_id, "user", user_query)
        save_chat_message(session_id, "assistant", assistant_response)
        logger.info(f"  Chat history saved")
        
        return {
            "response": assistant_response,
            "sources": list(table_names),
            "context_chunks": len(context.split("Chunk")),
            "is_comparison": is_comparison
        }


rag_agent = RAGAgent()
