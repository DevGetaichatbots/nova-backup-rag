from openai import AzureOpenAI
from openai.types.chat import ChatCompletionMessageParam
from src.config import settings
from typing import List
import json
import logging

logger = logging.getLogger(__name__)

NOVA_INSIGHT_SCHEMA = {
    "name": "nova_insight_report",
    "strict": True,
    "schema": {
        "type": "object",
        "required": [
            "management_conclusion",
            "schedule_overview",
            "delayed_activities",
            "root_cause_analysis",
            "downstream_consequences",
            "priority_actions",
            "resource_assessment",
            "summary_by_area",
            "insight_data"
        ],
        "additionalProperties": False,
        "properties": {
            "management_conclusion": {
                "type": "string",
                "description": "3-5 sentences as a senior construction planner would brief a project director. State the primary risk driver, whether delays are isolated or cascading, the most critical areas, and the single most important action right now."
            },
            "schedule_overview": {
                "type": "object",
                "required": ["schedule_name", "reference_date", "total_activities", "delayed_count", "areas_covered", "format_detected"],
                "additionalProperties": False,
                "properties": {
                    "schedule_name": {"type": "string"},
                    "reference_date": {"type": "string", "description": "dd-mm-yyyy format"},
                    "total_activities": {"type": "integer", "description": "Count of ALL work rows excluding summary/grouping headers"},
                    "delayed_count": {"type": "integer", "description": "Count of rows matching Startdato < reference_date AND progress = 0"},
                    "areas_covered": {"type": "array", "items": {"type": "string"}},
                    "format_detected": {"type": "string", "enum": ["MS Project Export", "Detailtidsplan", "Structured Table", "Unstructured", "Hybrid"]}
                }
            },
            "delayed_activities": {
                "type": "array",
                "description": "ALL delayed activities sorted by priority (CRITICAL_NOW first) then days_overdue descending",
                "items": {
                    "type": "object",
                    "required": ["id", "task_name", "start_date", "end_date", "duration", "progress", "days_overdue", "task_type", "priority", "is_root_cause", "blocked_by_id", "area"],
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string", "description": "Task ID from the schedule (real ID, never N/A)"},
                        "task_name": {"type": "string", "description": "Full task name from Opgavenavn column"},
                        "start_date": {"type": "string", "description": "dd-mm-yyyy format"},
                        "end_date": {"type": "string", "description": "dd-mm-yyyy or - if not available"},
                        "duration": {"type": "string", "description": "Original duration value e.g. 44d, 0d, 15d"},
                        "progress": {"type": "string", "description": "Always 0% for delayed activities"},
                        "days_overdue": {"type": "integer", "description": "Calendar days between start_date and reference_date"},
                        "task_type": {"type": "string", "enum": ["Coordination", "Design", "Bygherre", "Production", "Procurement", "Milestone"]},
                        "priority": {"type": "string", "enum": ["CRITICAL_NOW", "IMPORTANT_NEXT", "MONITOR"]},
                        "is_root_cause": {"type": "boolean", "description": "true if this is a root cause, false if downstream consequence"},
                        "blocked_by_id": {"type": ["string", "null"], "description": "If downstream consequence, the ID of the root cause task. null if root cause."},
                        "area": {"type": "string", "description": "Area or discipline this task belongs to"}
                    }
                }
            },
            "root_cause_analysis": {
                "type": "array",
                "description": "One entry per root cause task (is_root_cause=true)",
                "items": {
                    "type": "object",
                    "required": ["id", "task_name", "days_overdue", "problem_type", "why_it_matters", "downstream_impact", "consequence_if_unresolved", "affected_task_ids"],
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "task_name": {"type": "string"},
                        "days_overdue": {"type": "integer"},
                        "problem_type": {"type": "string", "enum": ["Coordination blockage", "Design input missing", "Bygherre decision pending", "Production delay", "Procurement delay"]},
                        "why_it_matters": {"type": "string", "description": "1 sentence: what does this block or prevent"},
                        "downstream_impact": {"type": "string", "description": "Which tasks/disciplines are affected, or 'Isolated' if none"},
                        "consequence_if_unresolved": {"type": "string", "description": "1 sentence: what happens if this stays unresolved"},
                        "affected_task_ids": {"type": "array", "items": {"type": "string"}, "description": "IDs of downstream tasks blocked by this root cause"}
                    }
                }
            },
            "downstream_consequences": {
                "type": "array",
                "description": "Tasks that are delayed because of a root cause (not root causes themselves)",
                "items": {
                    "type": "object",
                    "required": ["id", "task_name", "blocked_by_id"],
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "task_name": {"type": "string"},
                        "blocked_by_id": {"type": "string", "description": "ID of the root cause task"}
                    }
                }
            },
            "priority_actions": {
                "type": "array",
                "description": "Up to 7 specific practical actions in execution order, written as instructions from an experienced planner",
                "items": {
                    "type": "object",
                    "required": ["step", "action", "action_type"],
                    "additionalProperties": False,
                    "properties": {
                        "step": {"type": "integer", "description": "1-based step number"},
                        "action": {"type": "string", "description": "Specific practical action in plain construction project language"},
                        "action_type": {"type": "string", "enum": ["coordination", "bygherre_decision", "design_input", "freeze_downstream", "reassess", "release_work", "escalation", "procurement"]}
                    }
                }
            },
            "resource_assessment": {
                "type": "array",
                "description": "One entry per CRITICAL_NOW task",
                "items": {
                    "type": "object",
                    "required": ["id", "task_name", "resource_type", "assessment"],
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "task_name": {"type": "string"},
                        "resource_type": {"type": "string", "enum": ["coordination_bottleneck", "design_dependency", "bygherre_escalation", "production_manpower", "management_attention", "procurement_dependency"]},
                        "assessment": {"type": "string", "description": "1-2 sentences: whether adding labour helps, whether management attention is needed, whether prerequisites must be resolved first"}
                    }
                }
            },
            "summary_by_area": {
                "type": "array",
                "description": "One entry per area/discipline sorted by severity",
                "items": {
                    "type": "object",
                    "required": ["area", "delayed_count", "critical_count", "important_count", "monitor_count", "summary"],
                    "additionalProperties": False,
                    "properties": {
                        "area": {"type": "string"},
                        "delayed_count": {"type": "integer"},
                        "critical_count": {"type": "integer"},
                        "important_count": {"type": "integer"},
                        "monitor_count": {"type": "integer"},
                        "summary": {"type": "string", "description": "1-sentence situation summary for this area"}
                    }
                }
            },
            "insight_data": {
                "type": "object",
                "required": ["total_activities", "delayed_count", "critical_count", "important_count", "monitor_count", "root_cause_count", "reference_date", "most_overdue_days", "areas_affected", "format_detected", "schedule_name", "primary_risk"],
                "additionalProperties": False,
                "properties": {
                    "total_activities": {"type": "integer"},
                    "delayed_count": {"type": "integer"},
                    "critical_count": {"type": "integer"},
                    "important_count": {"type": "integer"},
                    "monitor_count": {"type": "integer"},
                    "root_cause_count": {"type": "integer"},
                    "reference_date": {"type": "string"},
                    "most_overdue_days": {"type": "integer"},
                    "areas_affected": {"type": "integer"},
                    "format_detected": {"type": "string"},
                    "schedule_name": {"type": "string"},
                    "primary_risk": {"type": "string", "description": "Short description of the primary risk driver"}
                }
            }
        }
    }
}

PREDICTIVE_SYSTEM_PROMPT = """<context>
You are Nova Insight — a senior construction schedule analyst and decision support system.
You analyze construction schedules and produce actionable intelligence for project managers.
You return your analysis as STRICT JSON matching the provided schema. Every field must be filled with real data from the schedule.

You receive the COMPLETE contents of a construction schedule file.

Your analysis has TWO layers:
1. DETECTION LAYER (Module A): Identify ALL delayed activities with absolute precision
2. DECISION SUPPORT LAYER: Transform raw delays into root cause understanding, consequence mapping, priority ranking, and practical action guidance

You are NOT a simple reporting tool. You think and reason like an experienced construction planner. You understand that:
- Some delays are root causes, others are downstream consequences
- Not every delay matters equally — some block entire disciplines, others are isolated
- Many construction delays cannot be solved by adding labour — they require coordination, design decisions, or management escalation
- A project manager needs to know WHAT to do, in WHAT ORDER, not just what is wrong

## AUTO-DETECT DOCUMENT TYPE

CRITICAL: Before analysis, examine the column headers in the data. The schedule may be in ANY of these formats, or a variation with extra/missing/renamed columns. You MUST adapt your analysis to whatever columns are actually present.

### FORMAT 1: MS PROJECT EXPORT
Typical columns: Id | Opgavetilstand | Opgavenavn | Varighed | Startdato | Slutdato | % arbejde færdigt | Foregående opgaver | Efterfølgende opgaver

### FORMAT 2: DETAILTIDSPLAN
Typical columns: Id | Entydigt id | Etage | omr. | Ansvarlig | Opgavenavn | Varighed | Startdato | Slutdato | % færdigt | bemærkn.

### FORMAT 3: UNSTRUCTURED WEEK-BASED SCHEDULE
No table/columns. Free-text Danish construction schedule organized by week numbers (Uge: X).
Activities = each "Day-range: Description @person" line. Duration = day count in range. Dependencies = "klar til X" phrases + trade sequencing.

### FORMAT 4: HYBRID / CUSTOM
Any other layout — ADAPT to whatever is present.

## ADAPTIVE COLUMN MAPPING

CRITICAL ID RULE:
Each data row is formatted as "Id: 41 | Opgavenavn: Placering af ... | Varighed: 1d | Startdato: ma 05-01-26 | ...".
The number after "Id:" IS the real task identifier. In this example, the ID is "41".
You MUST extract this number and use it as the "id" field in your JSON output.
NEVER output empty IDs. NEVER use row numbers, sequence numbers, or task names as IDs.
If the format uses "Entydigt id" instead of "Id", use that value.

1. Determine format type FIRST (week-based vs table-based)
2. Map columns to semantic roles:
   - TASK ID: "Id", "Entydigt id", "Task ID" — use "Entydigt id" if present (Detailtidsplan), else "Id". Extract the VALUE after the colon.
   - TASK NAME: "Opgavenavn", "Aktivitet", "Task Name"
   - DURATION: "Varighed", "Duration"
   - START DATE: "Startdato", "Start", "Start Date"
   - END DATE: "Slutdato", "Slut", "End Date", "Finish"
   - PROGRESS: "% arbejde færdigt", "% færdigt", "% Complete"
   - PREDECESSORS: "Foregående opgaver", "Predecessors"
   - SUCCESSORS: "Efterfølgende opgaver", "Successors"
   - RESPONSIBLE: "Ansvarlig", "Responsible"
   - AREA: "omr.", "Område", "Area"
3. Missing columns → degrade gracefully. Extra columns → ignore.

## FIELD DEFINITIONS

- Varighed: "50d" = 50 days, "3u" = 21 days, "0d" = milestone, "74.38d"/"16,24d" = decimal days, "10 d" (with space) = 10 days
- Startdato: "ma 05-01-26" (strip day-prefix, dd-mm-yy), "01-03-2022" (dd-mm-yyyy), "05-01-26" (dd-mm-yy)
- Slutdato: same formats, or "-" if summary/ongoing
- % arbejde færdigt / % færdigt: 0-100
- Foregående opgaver: semicolon-separated predecessor IDs, may include "489AS+5d"
- bemærkn.: R=revised, X=progress updated, NY=new activity

## RESPONSIBLE PARTY IDENTIFICATION

1. "Ansvarlig" column: ALLE, TØ, APT, INS, GU, MTH, BH, STÅL, Råhus, LUK
2. Gantt annotations: "EL(BH)", "VVS(TR)", "KL-ING", "Ark", "ALJ"
3. Task name prefixes: E100.01=Ventilation, E100.02=VVS, E100.03=EL, E100.04=BMS, E100.05=ELEV
4. Trade codes: EL=electrical, VVS=HVAC/plumbing, VE=ventilation, BH=client, TR=contractor, TØ=carpentry, APT=painting, INS=installation

## AREA/ZONE STRUCTURE

1. "omr." column (Detailtidsplan): FBH+AP, AP, FBH, etc.
2. Parent/summary rows (MS Project): "Omr. 1", "Omr. 2", etc.
3. Sub-tasks inherit parent area
4. "E100.01 Ventilation", "E100.02 VVS", "E100.03 EL" = discipline-level parents
5. "Globals" = cross-area/global scope
</context>

<task>
Execute a COMPLETE ANALYSIS on the provided schedule data. Return your results as JSON matching the strict schema.

## PHASE 1: DELAYED ACTIVITIES DETECTION (Module A)

### DETECTION RULE (ABSOLUTE — NO EXCEPTIONS):
An activity is DELAYED if BOTH are true:
  1. Startdato is BEFORE the reference date (any year — 2020, 2021, 2022, 2023, 2024, 2025 are ALL before 2026)
  2. Progress = 0% (or "0")

That's it. No other filter. No duration filter. No importance filter.
If an activity started in 2020 and still has 0% — it is delayed (2190+ days overdue).
If an activity started yesterday with 0% — it is delayed (1 day overdue).
If 50 activities have the same start date and all have 0% — ALL 50 are delayed.

### WHAT TO EXCLUDE (ONLY these):
- Grouping/summary HEADER rows: "Omr. 1", "Omr. 2", "E100.01 Ventilation", "E100.02 VVS", "E100.03 EL", "Globals", "Afhængigheder", "Færdiggøre projektering"
- These are section headers with very high durations that group sub-tasks
- EVERYTHING ELSE with 0% and Startdato < reference_date is a delayed activity

### PASS 1: Scan EVERY single row from first to last
- Read EVERY row. Do NOT stop after finding a few.
- For each row: check progress column. If 0% → candidate.
- If progress > 0% → skip.
- If grouping header → skip.

### PASS 2: Filter candidates by date
- Parse Startdato. If Startdato < reference_date → DELAYED. Include it.
- If Startdato >= reference_date → not delayed yet. Skip.
- Calculate days_overdue = reference_date minus Startdato in calendar days.
- IMPORTANT: A start date in year 2025 IS before a reference date in 2026. Year 2024 IS before 2026. Etc.

### PASS 3: Extract the real ID
- For each delayed activity, extract the "Id" column value (the number after "Id:").
- This is MANDATORY. The "id" field in your output must contain this number, e.g., "41", "520", "33".

### PASS 4: Verify completeness
After collecting all delayed activities, verify:
1. You processed EVERY row in the data (not just the first page or first area)
2. Every listed activity truly has Startdato < reference_date AND 0% progress
3. You included activities from ALL areas/disciplines (Omr. 1, Omr. 2, Omr. 3, etc.)
4. You did not miss any — go back and scan again if uncertain
5. Every activity has a real numeric ID from the Id column

## PHASE 2: DECISION SUPPORT ANALYSIS

### STEP 1: Classify each delayed activity by task_type
- Coordination: cross-discipline coordination, meetings, trade dependencies
- Design: design input, specs, drawings, data sheets
- Bygherre: client decisions, approvals, clarifications
- Production: physical construction/installation work
- Procurement: ordering, delivering, confirming materials
- Milestone: zero-duration markers, decision gates

### STEP 2: Root cause vs consequence
- Root cause: delay NOT caused by another delayed task
- Downstream consequence: delayed because depends on another delayed task
Use predecessors/successors if available. Otherwise infer from naming, sequencing, area grouping.

### STEP 3: Downstream impact per root cause
- Which tasks/disciplines affected
- Isolated vs cascading
- How many downstream tasks may slip

### STEP 4: Priority classification
- CRITICAL_NOW: Root cause, high overdue, blocks multiple downstream. Immediate action this week.
- IMPORTANT_NEXT: Significant delay, may block some work. Resolve within 1-2 weeks.
- MONITOR: Lower-priority, isolated, or downstream consequence. Track only.

### STEP 5: Action recommendations
Specific, practical, in plain construction language. Like an experienced planner's instructions.

### STEP 6: Sequence of action
Numbered steps. What to do first, second, third. Turns report into action plan.

### STEP 7: Resource logic
For each critical issue: manpower problem, coordination bottleneck, design dependency, or bygherre escalation.
</task>

<constraints>
- Use ONLY data from the schedule — never fabricate tasks, IDs, or dates
- NEVER create fake entries. Every item must correspond to a REAL activity with real values
- If fewer activities exist, list only those — do NOT pad
- Reference date: USE THE PROVIDED REFERENCE DATE. If none, use "Dato:" field or today's date
- Parse Varighed: "50d"=50 days, "3u"=21 days, "0d"=milestone, "74.38d"/"74,38d"=decimal
- Parse Startdato: "ma 05-01-26" (strip prefix, dd-mm-yy), "01-03-2022" (dd-mm-yyyy)
- Slutdato="-" does NOT mean summary. Only skip if clearly GROUPING HEADER (Omr. X, E100.XX, Globals)
- Summary rows: section headers with very high duration spanning sub-tasks AND no real work content
- Both conditions simultaneously: Startdato < reference_date AND progress = 0%
- Include 0d tasks (coordination milestones) if they meet both conditions
- Dates in output: always dd-mm-yyyy format
- management_conclusion must be written in the response language (Danish if da, English if en)
- All text fields (task names, assessments, actions) must be in the response language
- Keep original Danish task names — do not translate Opgavenavn
</constraints>

## DETECTION MODULE A: Delayed Activities

Logic: IF Startdato < reference_date AND progress = 0 THEN flag as DELAYED
Include 0d tasks. Exclude only summary/parent GROUPING rows.

## LANGUAGE HANDLING
The management_conclusion, priority_actions, resource_assessment, summary_by_area, and all descriptive text fields must be in the requested language. Task names (task_name) stay in their original language from the PDF."""


PREDICTIVE_LANGUAGE_INSTRUCTIONS = {
    "da": """
IMPORTANT: All descriptive text must be in Danish (Dansk):
- management_conclusion: written in Danish
- priority_actions[].action: written in Danish
- resource_assessment[].assessment: written in Danish
- summary_by_area[].summary: written in Danish
- root_cause_analysis[].why_it_matters, downstream_impact, consequence_if_unresolved: Danish
- Keep task_name values in their ORIGINAL language from the PDF (do not translate)
- Enum values (task_type, priority, problem_type, resource_type, action_type) stay in English — these are machine-readable
""",
    "en": """
Respond with all descriptive text in English.
Keep task_name values in their original language from the PDF (do not translate).
Enum values stay as defined in the schema.
"""
}


class PredictiveAgent:
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
        self.deployment = settings.AZURE_OPENAI_PREDICTIVE_DEPLOYMENT
        logger.info(f"PredictiveAgent initialized with model: {self.deployment}")

    def analyze(
        self,
        context: str,
        user_query: str,
        language: str = "en",
        schedule_filename: str = None,
        reference_date: str = None
    ) -> dict:
        logger.info(f"  [PredictiveAgent] Starting analysis with {self.deployment} (strict JSON schema)...")

        lang_instruction = PREDICTIVE_LANGUAGE_INSTRUCTIONS.get(
            language, PREDICTIVE_LANGUAGE_INSTRUCTIONS["en"]
        )
        system_prompt = f"{PREDICTIVE_SYSTEM_PROMPT}\n\n{lang_instruction}"

        schedule_label = schedule_filename if schedule_filename else "Schedule"

        ref_date_instruction = ""
        if reference_date:
            ref_date_instruction = f"""
REFERENCE DATE (MANDATORY): {reference_date}
This date was extracted from the uploaded filename. You MUST use this exact date as the reference date for all overdue calculations.
Do NOT use any other date. Do NOT use today's date. Use: {reference_date}
"""

        user_message = f"""Analyze the following construction schedule data.

Schedule filename: "{schedule_label}"
{ref_date_instruction}
═══════════════════════════════════════════════════════════
COMPLETE SCHEDULE DATA (ALL PAGES):
═══════════════════════════════════════════════════════════
{context}
═══════════════════════════════════════════════════════════

CRITICAL INSTRUCTIONS:
1. The data above is a COMPLETE markdown table extracted from the PDF via OCR. Every row is included.
2. The table has column headers in the first row (e.g. Id, Opgavenavn, Varighed, Startdato, Slutdato, % arbejde færdigt, etc.)
3. Read the "Id" column value for each row. Output that value in the "id" field.
4. The "% arbejde færdigt" (or similar) column contains the progress percentage.
5. The "Startdato" column contains the start date. Dates may be in formats like "ma 05-01-26", "ti 16-12-25", etc.

PHASE 1 — FIND ALL DELAYED ACTIVITIES:
- A row is delayed if: Startdato < reference_date AND progress = 0%
- Include ALL such rows. If there are 30 delayed activities, output all 30. If there are 50, output all 50.
- Do NOT limit to 4 or 5. Scan EVERY row. Include activities from ALL areas (Omr. 1, Omr. 2, Omr. 3, etc.)
- Activities from year 2025, 2024, 2023, etc. with 0% are ALL delayed relative to a 2026 reference date.
- Multiple activities with the same start date? Include ALL of them if they have 0%.
- Only skip grouping/summary headers (e.g. section headers like "Omr. 1", "E100.XX", "Globals", "Afhængigheder", "Færdiggøre projektering").

PHASE 2 — DECISION SUPPORT:
- Classify each delayed activity by task_type
- Determine root causes vs downstream consequences
- Assign priority (CRITICAL_NOW / IMPORTANT_NEXT / MONITOR)
- Generate action recommendations
- Write management conclusion

Return complete JSON matching the strict schema."""

        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            api_params = {
                "model": self.deployment,
                "messages": messages,
                "max_completion_tokens": 65536,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": NOVA_INSIGHT_SCHEMA
                }
            }

            try:
                api_params["reasoning_effort"] = "medium"
                response = self.client.chat.completions.create(**api_params)
            except Exception as reasoning_err:
                err_str = str(reasoning_err)
                if "reasoning_effort" in err_str or "Unrecognized" in err_str:
                    logger.warning(f"  [PredictiveAgent] reasoning_effort not supported, retrying without it")
                    del api_params["reasoning_effort"]
                    response = self.client.chat.completions.create(**api_params)
                else:
                    raise reasoning_err

            choice = response.choices[0]
            raw_content = choice.message.content or ""

            reasoning_content = getattr(choice.message, 'reasoning_content', None)
            if not reasoning_content:
                reasoning_content = getattr(choice.message, 'reasoning', None)
            if not reasoning_content and hasattr(choice.message, 'model_extra') and choice.message.model_extra:
                reasoning_content = choice.message.model_extra.get('reasoning_content') or choice.message.model_extra.get('reasoning')

            if reasoning_content:
                logger.info(f"  [PredictiveAgent] === LLM REASONING START ===")
                reasoning_str = str(reasoning_content)
                reasoning_lines = reasoning_str.split('\n')
                for line in reasoning_lines:
                    logger.info(f"  [PredictiveAgent] REASONING: {line}")
                logger.info(f"  [PredictiveAgent] === LLM REASONING END ({len(reasoning_str)} chars) ===")
            else:
                logger.info(f"  [PredictiveAgent] No reasoning content returned by model")

            model_used = getattr(response, 'model', self.deployment)
            usage = getattr(response, 'usage', None)
            usage_parts = []
            if usage:
                usage_parts.append(f"prompt={usage.prompt_tokens}")
                usage_parts.append(f"completion={usage.completion_tokens}")
                reasoning_tokens = getattr(usage, 'completion_tokens_details', None)
                if reasoning_tokens:
                    r_tokens = getattr(reasoning_tokens, 'reasoning_tokens', None)
                    if r_tokens is None and hasattr(reasoning_tokens, 'model_extra'):
                        r_tokens = reasoning_tokens.model_extra.get('reasoning_tokens')
                    if r_tokens is not None:
                        usage_parts.append(f"reasoning={r_tokens}")
            usage_info = f", tokens: {', '.join(usage_parts)}" if usage_parts else ""

            if not raw_content and hasattr(choice.message, 'refusal') and choice.message.refusal:
                logger.warning(f"  [PredictiveAgent] Model refused: {choice.message.refusal}")
                return {"predictive_insights": None, "model": self.deployment, "status": "error", "error": f"Model refused: {choice.message.refusal}"}

            if not raw_content:
                logger.warning(f"  [PredictiveAgent] Empty content. finish_reason={choice.finish_reason}")
                return {"predictive_insights": None, "model": self.deployment, "status": "error", "error": "Empty response from model"}

            try:
                parsed_json = json.loads(raw_content)
            except json.JSONDecodeError as je:
                logger.error(f"  [PredictiveAgent] JSON parse error: {je}")
                return {"predictive_insights": raw_content, "predictive_json": None, "model": self.deployment, "status": "error", "error": f"Invalid JSON: {je}"}

            required_keys = {"management_conclusion", "schedule_overview", "delayed_activities",
                             "root_cause_analysis", "priority_actions", "resource_assessment",
                             "summary_by_area", "insight_data"}
            missing_keys = required_keys - set(parsed_json.keys())
            if missing_keys:
                logger.error(f"  [PredictiveAgent] Schema validation failed — missing keys: {missing_keys}")
                return {"predictive_insights": raw_content, "predictive_json": None, "model": self.deployment, "status": "error", "error": f"Schema validation failed: missing {missing_keys}"}

            if not isinstance(parsed_json.get("delayed_activities"), list):
                logger.error(f"  [PredictiveAgent] Schema validation failed — delayed_activities is not a list")
                return {"predictive_insights": raw_content, "predictive_json": None, "model": self.deployment, "status": "error", "error": "Schema validation failed: delayed_activities is not a list"}

            delayed_count = len(parsed_json.get("delayed_activities", []))
            root_causes = sum(1 for a in parsed_json.get("delayed_activities", []) if a.get("is_root_cause"))
            logger.info(f"  [PredictiveAgent] JSON response: {delayed_count} delayed activities, {root_causes} root causes, model: {model_used}{usage_info}")

            delayed_ids = [a.get("id", "?") for a in parsed_json.get("delayed_activities", [])]
            logger.info(f"  [PredictiveAgent] Delayed activity IDs: {delayed_ids}")

            return {
                "predictive_insights": raw_content,
                "predictive_json": parsed_json,
                "model": self.deployment,
                "status": "success"
            }

        except Exception as e:
            logger.error(f"  [PredictiveAgent] Error: {e}")
            return {
                "predictive_insights": None,
                "predictive_json": None,
                "model": self.deployment,
                "status": "error",
                "error": str(e)
            }


predictive_agent = PredictiveAgent()
