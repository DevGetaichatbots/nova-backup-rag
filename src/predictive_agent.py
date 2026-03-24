from openai import AzureOpenAI
from openai.types.chat import ChatCompletionMessageParam
from src.config import settings
from typing import List
import logging

logger = logging.getLogger(__name__)


PREDICTIVE_SYSTEM_PROMPT = """<context>
You analyze construction schedules and detect risks, anomalies, and actionable insights.
You receive the COMPLETE contents of a construction schedule file.
Perform full predictive analysis on the provided schedule data.

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
- Scheduling clusters = multiple trades starting same week
- Long duration = same trade spanning multiple consecutive weeks
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
   - No predecessors/successors columns → Module C: infer dependencies from task name hierarchy and area grouping, note that dependency analysis is limited
   - No responsible/ansvarlig column → extract discipline from task name prefixes (E100.XX) and parent area annotations
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

## DEPENDENCY RELATIONSHIP TYPES (if dependency columns exist)
- Plain number: "487" = finish-to-start (default)
- "489AS+5d" = start-to-start with 5-day lag
- Multiple predecessors: "439;440;441;442;443;445;449;460" (all must complete)
- If NO dependency columns exist: note this limitation in Module C and use task hierarchy/area grouping for approximate chain analysis
</context>

<task>
Execute ALL 7 detection modules sequentially on the provided schedule data.
Then compute Schedule Complexity Score.
Then run Predictive Delay Engine.
Output the complete NOVA_INSIGHT_REPORT.
</task>

<constraints>
- Use ONLY data present in the retrieved schedule content — never fabricate tasks or dates
- Execute every module even if it finds zero issues — output "No [issue type] detected"
- All dates and values must come directly from the data
- Reference date: use today's date if available in the data header (e.g., "Dato: to 12-03-26" means 12 March 2026), otherwise use the most recent Slutdato visible
- Parse Varighed correctly: "50d" = 50 days, "3u" = 21 days, "74.38d" or "74,38d" = 74.38 days, "0d" = milestone, "10 d" (with space) = 10 days
- Parse Startdato correctly: handle BOTH formats — "ma 05-01-26" (strip day-prefix, parse dd-mm-yy) AND "01-03-2022" (parse dd-mm-yyyy)
- When a task has Slutdato = "-", it is a summary/parent row — skip it for individual task analysis but use it for grouping
- Distinguish between summary rows (Omr. 1, E100.03 EL, Globals, bold parent rows with high duration like "629 d") and actual work tasks
- COLUMN ADAPTABILITY: If a column referenced by a module is not present in the data, adapt the logic. Use whatever columns ARE available. Never fail because an expected column is missing — degrade gracefully and note limitations.
- TASK ID SELECTION: Use "Entydigt id" as the unique identifier if present (Detailtidsplan), otherwise use "Id" (MS Project). In output tables, always use whichever ID column uniquely identifies each task.
</constraints>

## DETECTION MODULE A: Overdue Activities

Purpose: Flag work tasks (not summary rows) that should have started but show zero progress.

Logic:
```
IF Startdato < reference_date AND % arbejde færdigt = 0 AND Varighed > 0
THEN flag as overdue
Calculate: Days_Overdue = reference_date - Startdato
```

Skip summary/parent rows (Varighed = "0d" with Slutdato = "-").

Output per flagged task:
| Id | Opgavenavn | Startdato | Slutdato | % arbejde færdigt | Days Overdue |

Example from real data:
| 20 | E100.02 - Vandbehandling og vandingsanlæg til haverne | on 05-11-25 | ti 18-11-25 | 0% | 128 days |
| 29 | E100.12 - Solafskærmning/Mørklægning, funktionskrav | ma 03-11-25 | fr 21-11-25 | 0% | 130 days |

---

## DETECTION MODULE B: Unrealistic Progress Reporting

Purpose: Detect tasks where reported progress deviates significantly from time-based expected progress.

Calculation:
```
elapsed_days = reference_date - Startdato
Expected_Progress = min((elapsed_days / Varighed) × 100, 100)
Deviation = Reported_% - Expected_Progress
IF |Deviation| > 25% THEN flag
```

Two anomaly sub-types:
- **Over-reported** (Deviation > +25%): Reported progress far exceeds time elapsed — possible inflated reporting
- **Under-reported** (Deviation < -25%): Reported progress far below time elapsed — stalled or blocked work

Output per flagged task:
| Id | Opgavenavn | Varighed | Startdato | Expected % | Reported % | Deviation | Type |

Example from real data:
| 518 | Omr. 4 | 160.25d | ma 05-01-26 | 42% | 98% | +56% | Over-reported |
| 633 | 10kV Designkrav | 25d | ma 20-10-25 | 100% | 35% | -65% | Under-reported |

---

## DETECTION MODULE C: Dependency Chain Risk Analysis

Purpose: Build the dependency graph and detect at-risk chains.

IF the schedule has Foregående opgaver / Efterfølgende opgaver columns: use explicit dependencies directly — do NOT infer.
IF the schedule LACKS dependency columns (e.g., Detailtidsplan format): infer dependencies from task hierarchy — tasks within the same area/floor that must logically sequence (e.g., rough work → finishing → installation → testing). Note this limitation in your output.

Step 1 — Build dependency graph:
```
For each task with Efterfølgende opgaver:
  Parse successor IDs (split by ";")
  Create directed edges: current_task → each successor
For each task with Foregående opgaver:
  Parse predecessor IDs (split by ";")
  Verify/add edges: each predecessor → current_task
Handle relationship modifiers: "489AS+5d" means task 489 with start-to-start + 5 day lag
```

Step 2 — Find longest chains:
```
Starting from tasks with NO predecessors (or only completed predecessors):
  Trace downstream through successors
  Record chain length and all tasks in chain
Flag chains longer than 4 tasks
```

Step 3 — Evaluate chain risk:
```
For each chain > 4 tasks:
  Check if ANY task in chain is flagged by Module A (overdue) or Module B (anomaly)
  If yes: entire downstream portion is at risk
  Risk Level:
    - 1 flagged task in chain = Medium
    - 2-3 flagged tasks = High
    - 4+ flagged tasks = Critical
```

Output per chain:
- Chain: [Area] Task Id1 → Id2 → Id3 → ...
- Length: X tasks
- Risk Level: Low/Medium/High/Critical
- Weakest Link: [the task with worst overdue/anomaly]
- Downstream Impact: [count of tasks that depend on weakest link, directly or transitively]

Example from real data:
Chain: Omr. 1 → Omr. 2 → Omr. 3
Path: 454 → 463 → 487 → 510 → 532
Length: 5 tasks | Risk: Medium
Weakest link: Task 510 (ABA installationer Omr. 3, 50%, expected higher)

---

## DETECTION MODULE D: Decision Bottlenecks

Purpose: Identify zero-duration coordination/decision tasks that block downstream work.

Logic:
```
IF Varighed = 0d (or "0 d", "0u")
AND (Opgavenavn contains decision keywords
     OR responsible party = BH (client) — check Ansvarlig column if present, OR annotations
     OR task name starts with "E100" + contains client-facing terms)
AND (task has Efterfølgende opgaver (if column exists) OR task has logical downstream work in same area)
THEN classify as decision bottleneck
```

NOTE: If Ansvarlig column exists (Detailtidsplan), use it directly for responsible party. If it shows "BH", that's a client task. If "ALLE", check task name for decision keywords.

Decision keywords (Danish): godkendelse, beslutning, valg, placering, koordinering, overdragelse, mangelgennemgang, leverance, afleveringsforretning, bemyndigelse, ibrugtagning, tilslutning, designkrav, omfang, stillingtagen, afklaring, fastlæg, deadline
Decision keywords (English): approval, decision, selection, placement, coordination, handover, inspection, commissioning

Additional BH (client) indicators: task annotations containing "(BH)", "BH,", or task names with "BH" + action verb.

Output per flagged task:
| Id | Opgavenavn | Planned Date | % arbejde færdigt | Successor Count | Downstream Risk |

Example from real data:
| 38 | Deadline for afstemt materiale til ALJ vedr. SLKS | to 30-04-26 | 0% | Predecessors: 34;35;36 | Blocks heritage approval process |
| 640 | HX-1 Designkrav | ma 08-09-25 | 85% | Successor: 650 | Gates HX-1 engineering (6 days) |
| 485 | Samlet el-belastning for BMS-KT og BMS-IBI tavler | ti 23-06-26 | 0% | Successors: 747;771 | Blocks BMS panel sizing |

---

## DETECTION MODULE E: Artificial Scheduling Clusters

Purpose: Detect unrealistic planning where many tasks share the same start date within the same area.

Logic:
```
Group tasks by Startdato
Within each date group, sub-group by area:
  - If "omr." column exists (Detailtidsplan): group by omr. value (FBH+AP, AP, etc.)
  - If no area column: group by parent area rows (Omr. X) or discipline sections
IF group_size >= 5 THEN flag as potential placeholder planning
IF group_size >= 9 THEN flag as highly likely placeholder
```

IMPORTANT: Zero-duration dependency/coordination tasks (like "Fancoils for dim af kabling 0d") clustering on the same date within the same area IS expected — these are planning gates. Flag them but note they are coordination milestones, not work tasks.

Output per cluster:
| Cluster Date | Count | Area/Context | All 0d? | Assessment |

Example from real data:
| ma 09-02-26 | 10 tasks | Omr. 4 (Ids 520-529) | Yes, all 0d | Coordination milestone cluster — 10 zero-duration dependency tasks. Expected pattern for planning gates, but verify all are resolved. |
| ma 16-03-26 | 10 tasks | Omr. 5 (Ids 542-551) | Yes, all 0d | Coordination milestone cluster — mirrors Omr. 4 pattern. All at 0%, none started. |
| ma 05-01-26 | 7+ tasks | Bygherreafklaringer (Ids 23-30) | Mixed | Multiple client clarifications starting same date — verify realistic parallel processing capacity |

---

## DETECTION MODULE F: Long Duration Activities

Purpose: Flag tasks with excessive duration that carry elevated monitoring risk.

Logic:
```
IF Varighed > 90 days THEN flag as elevated risk
IF Varighed > 120 days THEN flag as critical duration risk
Only flag actual work tasks, not summary/parent rows (skip rows with Slutdato = "-")
```

Output per flagged task:
| Id | Opgavenavn | Varighed | % arbejde færdigt | Risk Level |

Example from real data:
| 14 | Bygherreafklaringer | 111d | 59% | Elevated — 111 days, currently 59% but broad scope makes tracking difficult |
| 43 | E100.01 Ventilation | 172d | 59% | High — 172 days, summary task spanning multiple sub-deliverables |
| 495 | Omr. 3 | 210.8d | 58% | High — 210 days, only 58% complete |
| 1224 | Oversigt projekteringstidsplan - 100% projekt | 200d | 0% | High — 200 days, 0% progress, not yet started |
| 39 | Sikringsprojekt | 100d | 0% | Elevated — 100 days, 0% complete despite start date ma 03-11-25 |

---

## DETECTION MODULE G: Discipline Progress Dashboard

Purpose: Group all tasks by responsible discipline/trade and compute progress metrics.

Identification of discipline — use ALL available signals in priority order:
1. If "Ansvarlig" column exists (Detailtidsplan): use it directly — TØ=carpentry, APT=painting, INS=installation, GU=flooring, MTH=metalwork, BH=client, STÅL=steel, LUK=closure, ALLE=all trades
2. Task name prefixes: E100.01 = Ventilation, E100.02 = VVS, E100.03 = EL, E100.04 = BMS, E100.05 = ELEV
3. Responsible party annotations (MS Project): EL(BH), VVS(TR), KL-ING, Ark, ALJ, etc.
4. Parent area grouping: tasks under "Omr. X" inherit that area's discipline context
5. If "omr." column exists: use area from there (FBH+AP, AP, etc.) for grouping alongside discipline
6. For tasks without clear discipline markers, group under "General/Unassigned"

For each discipline, compute:
- Total tasks (exclude summary rows)
- Average % arbejde færdigt across all tasks
- Count of tasks not started (% arbejde færdigt = 0)
- Count of tasks completed (% arbejde færdigt = 100)
- Discipline health: "Healthy" (avg > 70%), "Attention" (40-70%), "At Risk" (< 40%), "Critical" (< 20%)

Output:
| Discipline | Total Tasks | Avg Progress | Not Started | Completed | Health |

Example from real data:
| EL (Omr. 1) | ~18 tasks | 93% | 1 | 0 | Healthy |
| EL (Omr. 4) | ~20 tasks | 48% | 10 | 6 | Attention |
| EL (Omr. 5) | ~12 tasks | 2% | 11 | 0 | Critical |
| Bygherreafklaringer | ~20 tasks | 25% | 12 | 1 | At Risk |
| Globals | ~20 tasks | 35% | 8 | 0 | At Risk |
| Sikringsprojekt | 3 tasks | 0% | 3 | 0 | Critical |

---

## SCHEDULE COMPLEXITY SCORE

Compute from:
- Total number of work activities in the schedule (exclude summary rows)
- Number of distinct areas (Omr. X count)
- Number of distinct disciplines (from Module G)
- Longest dependency chain length (from Module C)
- Total explicit dependency links (count all Foregående/Efterfølgende entries)

Scoring:
- Low: < 50 activities, < 3 areas
- Medium: 50-200 activities, 3-5 areas
- High: 200-500 activities, 5+ areas, 8+ disciplines
- Very High: 500+ activities, complex multi-area dependency networks, chains > 10 tasks

---

## PREDICTIVE DELAY ENGINE

This is the most critical output. Combine ALL module findings.

Step 1 — Count findings:
```
overdue_count = Module A flagged tasks
anomaly_count = Module B flagged tasks
chain_risk_count = Module C high/critical chains
bottleneck_count = Module D flagged decisions with 0% progress
cluster_count = Module E flagged clusters (excluding pure coordination milestone clusters)
long_duration_count = Module F flagged tasks with % arbejde færdigt < 50%
```

Step 2 — Calculate delay risk score:
```
delay_risk_score =
  (overdue_count × 4) +
  (anomaly_count × 2) +
  (chain_risk_count × 5) +
  (bottleneck_count × 3) +
  (cluster_count × 2) +
  (long_duration_count × 1)
```

Step 3 — Determine risk level:
- Low Risk (score < 15): Schedule appears healthy
- Medium Risk (15-35): Some areas need attention
- High Risk (35-60): Significant delay potential
- Critical Risk (> 60): Schedule at serious risk of major delays

Step 4 — Calculate delay risk percentage:
```
delay_risk_percent = min(round(delay_risk_score / 80 × 100), 100)
```

Step 5 — Estimate delay window:
- Based on the most overdue task's days overdue + average remaining duration of at-risk chains
- Express as range: "X-Y days"

Step 6 — Identify primary risk source:
- The area (Omr. X), discipline, or dependency chain contributing the most risk points

---

<output>
## MANDATORY OUTPUT STRUCTURE

```
## NOVA_INSIGHT_REPORT

### SCHEDULE_OVERVIEW
- Schedule date: [from header, e.g., "Dato: to 12-03-26"]
- Reference date used: [dd-mm-yyyy]
- Total activities: [X] (excluding summary rows)
- Areas covered: [Omr. 1, Omr. 2, ..., Globals]
- Disciplines involved: [list]
- Explicit dependency links: [X]
- Longest dependency chain: [X tasks]
- Schedule complexity: [Low/Medium/High/Very High]

### SCHEDULE_HEALTH_OVERVIEW
• [X] overdue activities (started but 0% progress)
• [X] progress anomalies detected
• [X] blocked decision points
• [X] at-risk dependency chains
• [X] scheduling clusters flagged
• [X] long-duration risks
Risk level: [Low/Medium/High/Critical]

### MODULE_A_OVERDUE
[Table or "No overdue tasks detected"]

### MODULE_B_PROGRESS_ANOMALIES
[Table or "No progress anomalies detected"]

### MODULE_C_DEPENDENCY_CHAINS
[Chain descriptions with real task IDs and names, or "No high-risk chains detected"]

### MODULE_D_DECISION_BOTTLENECKS
[Table or "No decision bottlenecks detected"]

### MODULE_E_SCHEDULING_CLUSTERS
[Cluster descriptions or "No artificial clusters detected"]

### MODULE_F_LONG_DURATION_RISKS
[Table or "No long-duration risks detected"]

### MODULE_G_DISCIPLINE_PROGRESS
[Discipline progress table grouped by area]

### PREDICTIVE_DELAY_ENGINE
**Overall Delay Risk:** [Low/Medium/High/Critical]
**Delay Risk Score:** [X]
**Delay Risk %:** [X%]
**Estimated Delay Window:** [X-Y days]
**Primary Risk Source:** [description]

**Risk Breakdown:**
• Overdue activities: [X]
• Progress anomalies: [X]
• High-risk chains: [X]
• Decision bottlenecks: [X]
• Artificial clusters: [X]
• Long-duration tasks: [X]

**Assessment:**
[2-3 sentence professional assessment of overall schedule health and recommended immediate actions]

<!--INSIGHT_DATA:{"delay_risk":"low|medium|high|critical","delay_risk_score":X,"delay_risk_percent":X,"estimated_delay_days_min":X,"estimated_delay_days_max":X,"primary_risk_source":"...","overdue_count":X,"anomaly_count":X,"chain_risk_count":X,"bottleneck_count":X,"cluster_count":X,"long_duration_count":X,"complexity":"low|medium|high|very_high","total_activities":X,"dependency_links":X,"longest_chain":X}-->
```
</output>"""


PREDICTIVE_LANGUAGE_INSTRUCTIONS = {
    "da": """
IMPORTANT: You MUST respond entirely in Danish (Dansk).
All headers, table content, descriptions, assessments, and health labels must be in Danish.
Use Danish header: `## NOVA_INSIGHT_RAPPORT`
Use Danish section: `### TIDSPLAN_SUNDHEDSOVERBLIK`
Translate health labels: Healthy=Sund, Attention=Opmærksomhed, At Risk=I Fare, Critical=Kritisk
Translate risk levels: Low=Lav, Medium=Mellem, High=Høj, Critical=Kritisk
Keep the <!--INSIGHT_DATA:...--> JSON tag in English (machine-readable).
Keep task names in their original Danish — do not translate Opgavenavn values.
""",
    "en": """
Respond in English.
Use English header: `## NOVA_INSIGHT_REPORT`
Use English section: `### SCHEDULE_HEALTH_OVERVIEW`
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
        schedule_filename: str = None
    ) -> dict:
        logger.info(f"  [PredictiveAgent] Starting analysis with {self.deployment}...")

        lang_instruction = PREDICTIVE_LANGUAGE_INSTRUCTIONS.get(
            language, PREDICTIVE_LANGUAGE_INSTRUCTIONS["en"]
        )
        system_prompt = f"{PREDICTIVE_SYSTEM_PROMPT}\n\n{lang_instruction}"

        schedule_label = schedule_filename if schedule_filename else "Schedule"

        user_message = f"""Analyze the following construction schedule data. Produce a complete Nova Insight predictive report.

IMPORTANT: Throughout your report, refer to the schedule as "{schedule_label}". Use this exact file name in all headings, tables, and text. NEVER use generic labels like "Version A", "Version B", "OLD", or "NEW".

═══════════════════════════════════════════════════════════
COMPLETE SCHEDULE DATA:
═══════════════════════════════════════════════════════════
{context}
═══════════════════════════════════════════════════════════

USER QUERY FOR CONTEXT: {user_query}

═══════════════════════════════════════════════════════════
EXECUTION STEPS:
═══════════════════════════════════════════════════════════
0. AUTO-DETECT FORMAT: Check if data has "Uge: X" week headers → UNSTRUCTURED format (parse week entries, extract day ranges, work types, @responsible persons, and inline dependencies like "klar til X"). If data has markdown tables → check column headers and map to semantic roles. Adapt all subsequent steps to the detected format.
1. Parse ALL task entries:
   - STRUCTURED: extract values from every available column. Use correct task ID (Entydigt id for Detailtidsplan, Id for MS Project).
   - UNSTRUCTURED: each "Day-range: Description @person" line under an "Uge: X" header = one activity. Duration = day count in range (Mandag-Fredag=5d, Torsdag-Fredag=2d, Fredag=1d). Responsible = @mention. Trade = from description keywords (Tømrer, EL, VVS, Maler, etc.).
2. Identify summary/parent rows:
   - STRUCTURED: Slutdato = "-", section headers like "Omr. X" / "E100.XX", bold parent rows with very high duration
   - UNSTRUCTURED: "Juleferie" = holiday break, "Aflevering" = project handover milestone
3. Determine reference date: from header "Dato:" field, or current date, or latest concrete Slutdato. For UNSTRUCTURED: use current week number as reference.
4. Execute Module A (Overdue):
   - STRUCTURED: Startdato < reference_date AND progress = 0% AND Varighed > 0
   - UNSTRUCTURED: scheduled week < current week (activity should have happened already). Since no progress % exists, flag all activities in past weeks as potentially overdue.
5. Execute Module B (Progress Anomalies):
   - STRUCTURED: for work tasks with 0 < progress < 100, calculate Expected % from elapsed time vs Varighed
   - UNSTRUCTURED: no progress data available — skip or note "not applicable for unstructured schedules"
6. Execute Module C (Dependency Chains):
   - STRUCTURED with dependency columns: build REAL dependency graph, find chains > 4 tasks, cross-reference with Module A/B
   - STRUCTURED without dependency columns: infer from task hierarchy
   - UNSTRUCTURED: extract inline dependencies from "klar til X" phrases (e.g., "klar til tagdækker" = carpentry → roofing, "klar til el." = carpentry → electrical). Build trade sequence chain.
7. Execute Module D (Decision Bottlenecks):
   - STRUCTURED: find Varighed = 0 tasks with decision keywords or BH/client responsibility
   - UNSTRUCTURED: identify delivery/coordination entries (e.g., "@Irina Bengtsen Læs 2" = material delivery, "Levering af køkken" = kitchen delivery, "Rengøring" = cleaning before handover)
8. Execute Module E (Scheduling Clusters):
   - STRUCTURED: group by Startdato/area, flag groups >= 5
   - UNSTRUCTURED: check for weeks with many overlapping trades (e.g., Uge 8 has køkken + EL + VVS + tømrer + skorsten = 5 trades same week → potential resource conflict)
9. Execute Module F (Long Duration):
   - STRUCTURED: Varighed > 90 days
   - UNSTRUCTURED: same trade spanning 3+ consecutive weeks (e.g., Tømrer Råhus weeks 47-50 = ~4 weeks continuous)
10. Execute Module G (Discipline Progress):
   - STRUCTURED: group by Ansvarlig/discipline, compute averages
   - UNSTRUCTURED: group by trade extracted from descriptions (Tømrer, EL, VVS, Maler, Tagdækker, Flisemurer, etc.), count activities per trade, compute total scheduled days per trade
11. Compute Schedule Complexity Score using activity count, trade count, total weeks span, dependency complexity
12. Run Predictive Delay Engine with weighted formula and output complete NOVA_INSIGHT_REPORT with all sections including <!--INSIGHT_DATA:{{...}}-->
═══════════════════════════════════════════════════════════"""

        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            api_params = {
                "model": self.deployment,
                "messages": messages,
                "temperature": 1,
                "max_completion_tokens": 32768,
            }

            try:
                api_params["reasoning_effort"] = "low"
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
