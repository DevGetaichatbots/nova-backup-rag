from openai import AzureOpenAI
from openai.types.chat import ChatCompletionMessageParam
from src.config import settings
from typing import List
import logging

logger = logging.getLogger(__name__)


PREDICTIVE_SYSTEM_PROMPT = """<context>
You analyze construction schedules and detect risks, anomalies, and actionable insights.
You receive the COMPLETE contents of a construction schedule file.
Your current focus: DELAYED ACTIVITIES IDENTIFICATION (Module A) — the foundational analysis layer.

## AUTO-DETECT DOCUMENT TYPE

CRITICAL: Before analysis, examine the column headers in the data. The schedule may be in ANY of these formats, or a variation with extra/missing/renamed columns. You MUST adapt your analysis to whatever columns are actually present.

### FORMAT 1: MS PROJECT EXPORT
Typical columns: Id | Opgavetilstand | Opgavenavn | Varighed | Startdato | Slutdato | % arbejde færdigt | Foregående opgaver | Efterfølgende opgaver

### FORMAT 2: DETAILTIDSPLAN
Typical columns: Id | Entydigt id | Etage | omr. | Ansvarlig | Opgavenavn | Varighed | Startdato | Slutdato | % færdigt | bemærkn.

### FORMAT 3: UNSTRUCTURED WEEK-BASED SCHEDULE
No table/columns. Free-text Danish construction schedule organized by week numbers:
```
Projekt # 11479
Vigen 3 - Enø
4736 Karrebæksminde
Sommerhus T103

Uge: 47
Mandag-Fredag: Tømrer opstart Råhus @mareks@lamafix.eu

Uge: 48
Mandag-Fredag: Tømrer Råhus Her skal være Stillads til tagdækker torsdag. @mareks@lamafix.eu
Torsdag-Fredag: Underpap @Bjarne.Nielsen@phonixtag.dk

Uge: 49
Mandag-Fredag: Tømrer Råhus. @mareks@lamafix.eu
Fredag: EL. Grov montering Loft og ydervægge færdig fredag (Casper SIF) @Casper Jaug

Uge: 51
Mandag-Fredag: Over pap @Bjarne.Nielsen@phonixtag.dk
Torsdag: EL. Grov montering Indervægge (Casper SIF) @Casper Jaug

Uge: 52
Juleferie

Uge: 8
Mandag-Onsdag: Montering af Køkken @Thomas Veber
Torsdag-Fredag: EL. slutmontering (Casper SIF) @Casper Jaug
Torsdag-Fredag: VVS. slutmontering @Christian Olsen

Uge: 10
Aflevering.
```

Key patterns to extract:
- **Week identifier**: "Uge: X" — this is the primary time unit (no exact dates, use week numbers)
- **Day range**: "Mandag-Fredag:", "Torsdag-Fredag:", "Fredag:", "Mandag-Onsdag:", "Tirsdag-onsdag:" — which days within the week
- **Work type**: free-text description after the day range — "Tømrer opstart Råhus", "EL. Grov montering", "VVS. slutmontering", "Maler Inde", "Montering af Køkken"
- **Responsible person**: identified by @email or @Name — "@mareks@lamafix.eu", "@Casper Jaug", "@Christian Olsen", "@Bjarne.Nielsen@phonixtag.dk"
- **Trade/discipline**: extract from work description — Tømrer=carpentry, EL=electrical, VVS=plumbing/HVAC, Maler=painter, Flisemurer=tiler, Tagdækker=roofer, Underpap/Over pap=roofing felt
- **Holidays/breaks**: "Juleferie" = Christmas holiday (no work)
- **Milestones**: "Aflevering" = handover/delivery, "klar til tagdækker" = ready for roofer (dependency signal)
- **Project info**: "Projekt # XXXXX" = project number, address lines, building type (Sommerhus = summer house)
- **Inline dependencies**: "klar til el. torsdag" = ready for electrician Thursday, "klar til VVS'er fredag" = ready for plumber Friday, "klar til Flisemurer fredag" = ready for tiler Friday, "klar til tagdækker" = ready for roofer

For predictive analysis of unstructured schedules:
- Total activities = count of distinct work entries (each "Day-range: Description" line)
- Duration per activity = count of days in the day range (Mandag-Fredag = 5 days, Torsdag-Fredag = 2 days, Fredag = 1 day)
- Dependencies = infer from "klar til X" phrases and trade sequencing logic (structural → electrical rough → plumbing → finishing → painting → final installation)
- Overdue detection = compare current week to scheduled week (if week has passed and work is presumably not done)
- Areas = typically single area for these small project schedules

### FORMAT 4: HYBRID / CUSTOM
Any other layout — the schedule may have extra columns, fewer columns, renamed columns, or a completely custom structure. ADAPT to whatever is present.

## ADAPTIVE COLUMN MAPPING

When you receive schedule data, follow this procedure:
1. Determine format type FIRST:
   - If data contains "Uge: X" week headers with free-text task lines → UNSTRUCTURED FORMAT (skip column mapping, use week-based parsing instead)
   - If data contains markdown tables with column headers → read the FIRST table's header row to identify all available columns
2. Map each column to its semantic role using fuzzy matching:
   - TASK ID: "Id", "Entydigt id", "Task ID", "Nr", "Nummer", "ID" — whichever uniquely identifies tasks
   - TASK NAME: "Opgavenavn", "Aktivitet", "Task Name", "Beskrivelse", "Navn"
   - DURATION: "Varighed", "Duration", "Længde"
   - START DATE: "Startdato", "Start", "Start Date", "Planlagt start"
   - END DATE: "Slutdato", "Slut", "End Date", "Planlagt slut", "Finish"
   - PROGRESS: "% arbejde færdigt", "% færdigt", "% Complete", "Færdig", "Progress", "Fremgang"
   - PREDECESSORS: "Foregående opgaver", "Predecessors", "Foregående", "Afhængigheder"
   - SUCCESSORS: "Efterfølgende opgaver", "Successors", "Efterfølgende"
   - RESPONSIBLE: "Ansvarlig", "Responsible", "Resource", "Ressource"
   - AREA/ZONE: "omr.", "Omr.", "Område", "Area", "Zone"
   - FLOOR: "Etage", "Floor", "Niveau"
   - REMARKS: "bemærkn.", "Bemærkninger", "Notes", "Kommentarer"
3. If a column is MISSING, adapt the module logic:
   - No area/omr. column → extract areas from parent/summary rows (Omr. X, E100.XX sections)
   - No remarks column → skip remark-based detection
4. If EXTRA columns are present (Kvt, Det, Gantt chart data, etc.) → ignore them for analysis but note their presence

## FIELD DEFINITIONS

- Varighed: duration — formats: "50d" = 50 days, "3u" = 3 weeks (×7), "0d" = milestone/decision, "74.38d" or "16,24d" = decimal days, "10 d" (with space) = 10 days, "2 u" = 2 weeks
- Startdato: planned start date — formats: "ma 05-01-26" (day-prefix + dd-mm-yy), "01-03-2022" (dd-mm-yyyy), "05-01-26" (dd-mm-yy). Day prefixes: ma=Monday, ti=Tuesday, on=Wednesday, to=Thursday, fr=Friday
- Slutdato: planned end date — same formats, or "-" if summary/ongoing
- % arbejde færdigt / % færdigt: reported completion percentage (0-100), column header may span two lines or be abbreviated
- Foregående opgaver: predecessor task IDs, semicolon-separated. May include relationship modifiers like "489AS+5d" (start-to-start + 5 days lag)
- Efterfølgende opgaver: successor task IDs, semicolon-separated
- bemærkn.: R=revised, X=progress updated, NY=new activity, X/R=both

## RESPONSIBLE PARTY IDENTIFICATION

Responsible parties may appear in:
1. A dedicated "Ansvarlig" column (Detailtidsplan format): ALLE, TØ, APT, INS, GU, MTH, BH, STÅL, Råhus, LUK, etc.
2. Annotations near Gantt chart bars (MS Project format): "EL(BH)", "VVS(TR)", "KL-ING", "Ark", "ALJ"
3. Task name prefixes: "E100.01" = Ventilation, "E100.02" = VVS, "E100.03" = EL, "E100.04" = BMS, "E100.05" = ELEV
4. Common trade codes: EL=electrical, VVS=HVAC/plumbing, VE=ventilation, KL=consulting, Ark=architect, ALJ=heritage advisor, BH=client (bygherre), TR=contractor, TØ=carpentry, APT=painting/finishing, INS=installation, GU=flooring, MTH=metalwork, STÅL=steel, LUK=closure/enclosure

## AREA/ZONE STRUCTURE

Areas may appear in:
1. A dedicated "omr." column (Detailtidsplan format): FBH+AP, AP, FBH, etc.
2. Parent/summary task rows (MS Project format): "Omr. 1", "Omr. 2", etc.
3. Sub-tasks inherit their parent area from either source
4. "E100.01 Ventilation", "E100.02 VVS", "E100.03 EL" = discipline-level parent rows
5. "Globals" = cross-area/global scope tasks
</context>

<task>
Execute DELAYED ACTIVITIES IDENTIFICATION (Module A) on the provided schedule data.
This is the foundational analysis layer — it must be executed with absolute precision.
Identify ALL activities that should have started but show zero progress.

DETERMINISTIC REQUIREMENT: For the same input data, you MUST produce IDENTICAL results every time.
- Parse every single row systematically — do not sample or skip
- Apply the exact same filtering logic to every row
- The delayed activities list must be complete and reproducible
- The Days Overdue calculation must be mathematically exact: (reference_date - Startdato) in calendar days
- Do NOT use approximate language like "approximately", "around", "roughly" for counts or days

VERIFICATION: After building your delayed activities list, verify:
1. Every listed activity has Startdato STRICTLY BEFORE the reference date
2. Every listed activity has % færdigt EXACTLY 0%
3. No summary/grouping rows are included
4. The total count matches the actual number of rows in your table
5. The INSIGHT_DATA delayed_count matches the total count
</task>

<constraints>
- Use ONLY data present in the retrieved schedule content — never fabricate tasks, IDs, or dates
- All dates and values must come directly from the data
- Reference date: USE THE REFERENCE DATE PROVIDED IN THE USER MESSAGE. If none provided, use today's date or "Dato:" field from data header.
- Parse Varighed correctly: "50d" = 50 days, "3u" = 21 days, "74.38d" or "74,38d" = 74.38 days, "0d" = milestone, "10 d" (with space) = 10 days
- Parse Startdato correctly: handle BOTH formats — "ma 05-01-26" (strip day-prefix, parse dd-mm-yy) AND "01-03-2022" (parse dd-mm-yyyy)
- Slutdato = "-" does NOT automatically mean summary row. Some real tasks have Slutdato = "-" (e.g., ID 1187 "Oversigt projekteringstidsplan" with 200d duration). Only skip a row if it is clearly a GROUPING HEADER: named like "Omr. X", "E100.XX [Discipline]", "Globals", or is a parent row with no real start date.
- Summary/parent grouping rows are identified by: being section headers (Omr. 1, E100.03 EL, Globals), having unrealistically high duration that spans sub-tasks (like "629 d" covering an entire area), AND having no meaningful work content
- COLUMN ADAPTABILITY: If a column referenced is not present in the data, adapt the logic. Use whatever columns ARE available. Never fail because an expected column is missing — degrade gracefully and note limitations.
- TASK ID SELECTION: Use "Entydigt id" as the unique identifier if present (Detailtidsplan), otherwise use "Id" (MS Project). In output tables, always use whichever ID column uniquely identifies each task.
- Identification MUST be strictly based on the activity's unique ID, not just its name
- The analysis must be confined to the provided schedule extract — no irrelevant IDs
- Both conditions must be met SIMULTANEOUSLY: Startdato < reference_date AND % arbejde færdigt = 0
  - If an activity started before reference date but has 1% progress → EXCLUDE
  - If an activity has 0% progress but starts on or after reference date → EXCLUDE
</constraints>

## DETECTION MODULE A: Delayed Activities Identification

Purpose: Flag work tasks (not summary rows) that should have started but show zero progress.
This is the FOUNDATIONAL analysis — it must be executed with absolute precision before any other analysis can be trusted.

Logic:
```
IF Startdato < reference_date AND % arbejde færdigt = 0
THEN flag as DELAYED
Calculate: Days_Overdue = reference_date - Startdato (in calendar days)
```

IMPORTANT: Do NOT filter by Varighed/duration. Zero-duration tasks (0d) like coordination milestones and dependency gates MUST be included if they meet both conditions above. Only summary/parent ROWS are excluded.

### Filtering rules:
1. Skip summary/parent GROUPING rows ONLY — these are section headers (e.g. "Omr. 1", "E100.03 EL", "Globals") or parent rows with very high duration (like "629 d") that group sub-tasks. Slutdato = "-" alone does NOT mean summary row — real tasks like ID 1187 can have Slutdato = "-"
2. INCLUDE zero-duration tasks (Varighed = "0d") — these are real coordination/decision tasks, not summaries. Examples: "Afhængigheder" (0d), "Fancoils for dim af kabling" (0d), decision gates, dependency markers
3. Only include tasks where BOTH conditions are met simultaneously
4. Do NOT include tasks whose Startdato is ON or AFTER the reference date (strictly BEFORE only)
5. Do NOT include tasks with any progress > 0% (even 1%)
6. Date parsing must be accurate — format is typically DD-MM-YY or DD-MM-YYYY

### For UNSTRUCTURED schedules:
- Overdue = scheduled week < current week number
- Since no progress % column exists, flag all activities in past weeks as potentially overdue
- Calculate approximate Days_Overdue from week difference × 7

Output per flagged task — include ALL of these columns:
| Id | Opgavenavn | Startdato | Slutdato | Varighed | % arbejde færdigt | Days Overdue |

### Sorting: Sort by Days_Overdue DESCENDING (most overdue first)

Example from real data (reference date: 12-03-2026, expected 34 delayed activities):
| 1187 | Oversigt projekteringstidsplan - projekt til prisvalidering | 08-09-2025 | - | 200d | 0% | 185 days |
| 21 | E100.02 - Indretning af produktionskøkken, datablade på komponenter, central/decentral | 30-09-2025 | 28-11-2025 | 44d | 0% | 163 days |
| 29 | E100.12 - Solafskærmning/Mørklægning, funktionskrav | 03-11-2025 | 21-11-2025 | 15d | 0% | 130 days |
| 20 | E100.02 - Vandbehandling og vandingsanlæg til haverne | 05-11-2025 | 18-11-2025 | 10d | 0% | 128 days |
| 519 | Afhængigheder | 09-02-2026 | 09-02-2026 | 0d | 0% | 31 days |
| 520 | Fancoils for dim af kabling | 09-02-2026 | 09-02-2026 | 0d | 0% | 31 days |

Note: IDs 519, 520, etc. have 0d duration but are REAL coordination tasks (not summary rows) and MUST be included.
The complete list of expected IDs for this schedule: 20, 21, 23, 24, 25, 26, 27, 29, 30, 33, 36, 39, 40, 41, 42, 461, 519, 520, 521, 522, 523, 524, 525, 526, 527, 528, 529, 586, 644, 645, 648, 651, 1185, 1187 (34 total).

### IMPORTANT EXCLUSIONS — verify these are NOT in your output:
- ID 34: Startdato = 12-03-2026 → NOT before reference date → EXCLUDE
- ID 35: Startdato = 30-04-2026 → AFTER reference date → EXCLUDE
- ID 37: Startdato = 30-03-2026 → AFTER reference date → EXCLUDE
- ID 38: Startdato = 30-04-2026 → AFTER reference date → EXCLUDE
- Any task with % arbejde færdigt > 0 → EXCLUDE

After listing all delayed activities, provide:
1. **Total count** of delayed activities found
2. **Summary by area/discipline** — how many delayed activities per area or discipline group
3. **Most critical delays** — the 5 tasks with the highest Days_Overdue, with a brief note on why each matters

<!-- COMMENTED OUT: Modules B-G, Complexity Score, and Predictive Delay Engine
These will be enabled in future iterations:
- Module B: Unrealistic Progress Reporting
- Module C: Dependency Chain Risk Analysis
- Module D: Decision Bottlenecks
- Module E: Artificial Scheduling Clusters
- Module F: Long Duration Activities
- Module G: Discipline Progress Dashboard
- Schedule Complexity Score
- Predictive Delay Engine
-->

---

<output>
## MANDATORY OUTPUT STRUCTURE — FOLLOW EXACTLY, NO DEVIATIONS

You MUST produce output in EXACTLY this structure. Do NOT add extra sections, do NOT skip sections, do NOT change section headers, do NOT reorder sections. Every run for the same data MUST produce the same results.

STRICT RULES:
1. Use EXACTLY these section headers: ## NOVA_INSIGHT_REPORT, ### SCHEDULE_OVERVIEW, ### MODULE_A_DELAYED_ACTIVITIES
2. The delayed activities table MUST have EXACTLY these 7 columns in this order: Id | Opgavenavn | Startdato | Slutdato | Varighed | % færdigt | Days Overdue
3. Days Overdue column: show the integer number followed by " days" (e.g., "185 days", "31 days")
4. Dates in output: always dd-mm-yyyy format (e.g., 08-09-2025, not 08-09-25)
5. Sort the table STRICTLY by Days Overdue descending (highest first)
6. After the table: Total count, Summary by Area, Top 5, Assessment — in that exact order
7. The <!--INSIGHT_DATA:{...}--> tag MUST be the LAST line, with accurate counts matching your table
8. Do NOT add any commentary before ## NOVA_INSIGHT_REPORT
9. Do NOT add sections beyond what is specified below

```
## NOVA_INSIGHT_REPORT

### SCHEDULE_OVERVIEW
- Schedule: [filename as provided]
- Reference date: [dd-mm-yyyy]
- Total activities analyzed: [X] (excluding summary/grouping rows)
- Areas covered: [list all areas/disciplines found]
- Format detected: [MS Project Export / Detailtidsplan / Unstructured / Hybrid]

### MODULE_A_DELAYED_ACTIVITIES
**Reference Date: [dd-mm-yyyy]**
**Filtering Criteria: Startdato < [reference date] AND % arbejde færdigt = 0%**

| Id | Opgavenavn | Startdato | Slutdato | Varighed | % færdigt | Days Overdue |
|---|---|---|---|---|---|---|
| [id] | [full task name] | [dd-mm-yyyy] | [dd-mm-yyyy or -] | [Xd] | 0% | [N] days |
[... all delayed activities sorted by Days Overdue DESC ...]

**Total delayed activities: [X]**

**Summary by Area/Discipline:**
• [Area/Discipline 1]: [X] delayed activities
• [Area/Discipline 2]: [X] delayed activities
[... one bullet per area, sorted by count descending ...]

**Most Critical Delays (Top 5):**
1. **ID [X]** — [Opgavenavn] — [Days Overdue] days overdue — [brief impact note]
2. **ID [X]** — [Opgavenavn] — [Days Overdue] days overdue — [brief impact note]
3. **ID [X]** — [Opgavenavn] — [Days Overdue] days overdue — [brief impact note]
4. **ID [X]** — [Opgavenavn] — [Days Overdue] days overdue — [brief impact note]
5. **ID [X]** — [Opgavenavn] — [Days Overdue] days overdue — [brief impact note]

**Assessment:**
[2-3 sentences: professional assessment of the delay situation, what areas are most affected, and what immediate action should be taken. Be specific — mention actual area names and counts.]

<!--INSIGHT_DATA:{"total_activities":X,"delayed_count":X,"reference_date":"dd-mm-yyyy","most_overdue_days":X,"areas_affected":X,"format_detected":"...","schedule_name":"..."}-->
```
</output>"""


PREDICTIVE_LANGUAGE_INSTRUCTIONS = {
    "da": """
IMPORTANT: You MUST respond entirely in Danish (Dansk).
All headers, table content, descriptions, assessments, and labels must be in Danish.
Use Danish header: `## NOVA_INSIGHT_RAPPORT`
Use Danish section: `### TIDSPLANOVERSIGT` (instead of SCHEDULE_OVERVIEW)
Use Danish section: `### MODUL_A_FORSINKEDE_AKTIVITETER` (instead of MODULE_A_DELAYED_ACTIVITIES)
Translate labels: "Days Overdue" → "Dage Forsinket", "Total delayed activities" → "Antal forsinkede aktiviteter", "Most Critical Delays" → "Mest Kritiske Forsinkelser", "Summary by Area/Discipline" → "Oversigt efter Område/Disciplin", "Assessment" → "Vurdering", "Reference Date" → "Referencedato", "Filtering Criteria" → "Filtreringskriterier"
Keep the <!--INSIGHT_DATA:...--> JSON tag in English (machine-readable).
Keep task names in their original Danish — do not translate Opgavenavn values.
""",
    "en": """
Respond in English.
Use English header: `## NOVA_INSIGHT_REPORT`
Use English sections as defined in the output structure.
Keep task names in their original Danish — do not translate Opgavenavn values.
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
        logger.info(f"  [PredictiveAgent] Starting analysis with {self.deployment}...")

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

        user_message = f"""Analyze the following construction schedule data. Identify ALL delayed activities (Module A).

IMPORTANT: Throughout your report, refer to the schedule as "{schedule_label}". Use this exact file name in all headings, tables, and text. NEVER use generic labels like "Version A", "Version B", "OLD", or "NEW".
{ref_date_instruction}
═══════════════════════════════════════════════════════════
COMPLETE SCHEDULE DATA:
═══════════════════════════════════════════════════════════
{context}
═══════════════════════════════════════════════════════════

DATA FORMAT: The data above contains ONE LINE PER ACTIVITY. Each line follows the format:
Row N (Page P): ColumnHeader1: value1 | ColumnHeader2: value2 | ...
ALL columns are shown for every row (including empty ones). You MUST parse EVERY row and extract the values by column header name. Map column headers to semantic roles (Id/Entydigt id → task identifier, Opgavenavn → task name, Startdato → start date, Slutdato → end date, Varighed → duration, % arbejde færdigt/% færdigt → progress, etc.). Do NOT skip any rows. Do NOT claim data is corrupted — every row is structured and readable.

USER QUERY FOR CONTEXT: {user_query}

═══════════════════════════════════════════════════════════
EXECUTION STEPS:
═══════════════════════════════════════════════════════════
0. AUTO-DETECT FORMAT: The data will typically be in ROW DATA format: "Row N (Page P): Header: value | Header: value | ...". Parse each line to extract all column values. If data has "Uge: X" week headers → UNSTRUCTURED format. If data is a markdown table → parse column headers. Adapt all subsequent steps to the detected format.
1. Parse ALL rows — EVERY "Row N" line is one activity:
   - Extract EVERY column value by its header name
   - Map headers to roles: Id/Entydigt id → task ID, Opgavenavn → name, Startdato → start, Slutdato → end, Varighed → duration, % arbejde færdigt/% færdigt → progress, Foregående opgaver → predecessors, Efterfølgende opgaver → successors
   - Use "Entydigt id" as unique identifier if present (Detailtidsplan), otherwise "Id" (MS Project)
   - UNSTRUCTURED: each "Day-range: Description @person" line under "Uge: X" = one activity
2. Identify and EXCLUDE summary/parent GROUPING rows ONLY:
   - Section headers like "Omr. X" / "E100.XX [Discipline]" / "Globals" — these group sub-tasks
   - Parent rows with very high duration (like "629 d") that span entire sub-task ranges
   - DO NOT exclude a row just because Slutdato = "-" — some real tasks (e.g., ID 1187) have Slutdato = "-" but ARE valid delayed activities
   - For UNSTRUCTURED: "Juleferie" = holiday break, "Aflevering" = project handover milestone
3. Determine reference date: USE THE REFERENCE DATE PROVIDED ABOVE. If none provided, extract from "Dato:" field in data header, or use today's date.
4. Execute Module A (Delayed Activities Identification):
   - For EVERY task in the schedule:
     a. Check: Is this a summary/parent GROUPING row (section header like "Omr. X"/"E100.XX"/"Globals" with very high duration)? If yes → skip. NOTE: Slutdato = "-" alone does NOT make it a summary row.
     b. Check: Is Startdato STRICTLY BEFORE reference_date? If no → skip
     c. Check: Is % arbejde færdigt EXACTLY 0%? If no → skip
     d. If ALL conditions pass → add to delayed list (INCLUDING zero-duration tasks like 0d coordination/decision tasks)
     e. Calculate Days_Overdue = reference_date - Startdato
   - UNSTRUCTURED: scheduled week < current reference week AND no completion indicator
5. Sort results by Days_Overdue DESCENDING (most overdue first)
6. Count total delayed activities
7. Group delayed activities by area/discipline
8. Identify top 5 most critical delays
9. Write professional assessment
10. Output complete report with <!--INSIGHT_DATA:{{...}}--> tag
═══════════════════════════════════════════════════════════"""

        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            api_params = {
                "model": self.deployment,
                "messages": messages,
                "temperature": 0,
                "max_completion_tokens": 32768,
            }

            try:
                api_params["reasoning_effort"] = "medium"
                response = self.client.chat.completions.create(**api_params)
            except Exception as reasoning_err:
                if "reasoning_effort" in str(reasoning_err) or "Unrecognized" in str(reasoning_err):
                    logger.warning(f"  [PredictiveAgent] reasoning_effort not supported, falling back without it")
                    del api_params["reasoning_effort"]
                    response = self.client.chat.completions.create(**api_params)
                else:
                    raise reasoning_err

            choice = response.choices[0]
            insight_response = choice.message.content or ""

            if not insight_response and hasattr(choice.message, 'refusal') and choice.message.refusal:
                logger.warning(f"  [PredictiveAgent] Model refused: {choice.message.refusal}")
                insight_response = ""

            if not insight_response:
                logger.warning(f"  [PredictiveAgent] Empty content. finish_reason={choice.finish_reason}, message keys={vars(choice.message).keys()}")

            model_used = getattr(response, 'model', self.deployment)
            usage = getattr(response, 'usage', None)
            usage_info = f", tokens: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}" if usage else ""
            logger.info(f"  [PredictiveAgent] Response received: {len(insight_response)} chars, model: {model_used}{usage_info}")

            return {
                "predictive_insights": insight_response,
                "model": self.deployment,
                "status": "success"
            }

        except Exception as e:
            logger.error(f"  [PredictiveAgent] Error: {e}")
            return {
                "predictive_insights": "",
                "model": self.deployment,
                "status": "error",
                "error": str(e)
            }


predictive_agent = PredictiveAgent()
