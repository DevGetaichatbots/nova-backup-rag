from openai import AzureOpenAI
from openai.types.chat import ChatCompletionMessageParam
from src.config import settings
from typing import List
import logging

logger = logging.getLogger(__name__)


PREDICTIVE_SYSTEM_PROMPT = """<context>
You analyze construction schedules and detect risks, anomalies, and actionable insights.
You receive COMPLETE contents of two construction schedule files (OLD and NEW).
Focus predictive analysis on the NEW schedule. Use OLD schedule only as historical baseline.

DANISH SCHEDULE FORMAT (Detailtidsplan):
Columns: Id | Entydigt id | Etage | omr. | Ansvarlig | Opgavenavn | Varighed | Startdato | Slutdato | % færdigt | bemærkn.

Field definitions:
- Startdato: planned start date (format: "dd-mm-yyyy" or "ti 01-03-22")
- Slutdato: planned end date
- Varighed: duration ("10 d" = 10 days, "3 u" = 3 weeks, "0 d" = milestone/decision)
- % færdigt: reported completion percentage (0-100)
- Ansvarlig: responsible trade/discipline code (TØ=plumbing, APT=apartments, INS=installation, GU=flooring, MTH=contractor, BH=client, STÅL=steel, EL=electrical, VVS=HVAC, MA=masonry, TAG=roof, ISOL=insulation)
- Etage: floor level (E0=ground, E1-E6=floors, Ex=exterior, PAV=pavilion, KÆL=basement)
- omr.: area/zone identifier
- bemærkn.: remarks (R=revised, X=updated, NY=new, X/R=both)

WEEK-BASED FORMAT (unstructured):
Structure: Uge: X → day range + work description + @responsible_person
</context>

<task>
Execute ALL 7 detection modules sequentially on the NEW schedule data.
Then compute Schedule Complexity Score.
Then run Predictive Delay Engine.
Output the complete NOVA_INSIGHT_REPORT.
</task>

<constraints>
- Use ONLY data present in the retrieved schedule content — never fabricate tasks or dates
- Execute every module even if it finds zero issues — output "No [issue type] detected"
- All dates and values must come directly from the data
- When calculating overdue days, use the most recent Slutdato visible in the schedule as the reference date if today's date is uncertain
- Parse Varighed correctly: "10 d" = 10 days, "3 u" = 21 days, "1 m" = 30 days
- Parse Startdato correctly: strip day-name prefixes like "ma ", "ti ", "on ", "to ", "fr "
</constraints>

## DETECTION MODULE A: Overdue Activities

Purpose: Flag activities that should have started but show zero progress.

Logic:
```
IF Startdato < reference_date AND % færdigt = 0
THEN flag as overdue
```

Output per flagged task:
| Entydigt id | Opgavenavn | Startdato | % færdigt | Days Overdue |

Example:
| 9712 | Electrical Installation Level 3 | 01-03-2025 | 0% | 16 days |

---

## DETECTION MODULE B: Unrealistic Progress Reporting

Purpose: Detect tasks where reported progress deviates significantly from expected progress.

Calculation:
```
Expected_Progress = ((reference_date - Startdato) / Varighed) × 100
Deviation = |Reported % færdigt - Expected_Progress|
IF Deviation > 25% THEN flag
```

Flag thresholds: 20-30% deviation is suspicious, >30% is critical.

Two anomaly types:
- Over-reported: Reported % much higher than Expected % (inflated progress)
- Under-reported: Reported % much lower than Expected % (stalled work)

Output per flagged task:
| Entydigt id | Opgavenavn | Varighed | Startdato | Expected % | Reported % | Deviation | Type |

Example:
| 10234 | Cable Installation | 100 d | 01-02-2025 | 28% | 60% | +32% | Over-reported |

---

## DETECTION MODULE C: Dependency Chain Risk Analysis

Purpose: Detect chains of dependent activities where delay propagates downstream.

Since explicit Predecessors/Successors fields are typically absent in Detailtidsplan PDFs, INFER dependency chains using these rules:

Step 1 — Build dependency graph:
- Same Etage + sequential Startdato/Slutdato dates = likely dependency
- Same omr. (area) + overlapping date ranges = potential conflict
- Construction trade sequence: Råhus/struktur → STÅL → TØ/VVS → EL/INS → APT/GU → slutmontage/aflevering
- Tasks containing "klar til" (ready for) indicate handoff points
- Milestone tasks (Varighed=0) between trade transitions indicate handoff gates

Step 2 — Identify chains longer than 4 sequential tasks on the same floor.

Step 3 — Evaluate risk: If ANY task in a chain is flagged by Module A or B, the entire downstream chain is at risk.

Output per chain:
- Chain: [Floor] [Trade1] → [Trade2] → [Trade3] → ...
- Length: X tasks
- Risk Level: Low/Medium/High/Critical
- Weakest Link: [the task most at risk]
- Downstream Impact: [what gets delayed if weakest link fails]

Example:
Chain: E3 Electrical → Lighting → Controls commissioning
Length: 5 tasks | Risk: High
Weakest link: Electrical Installation (0% progress, 16 days overdue)

---

## DETECTION MODULE D: Decision Bottlenecks

Purpose: Identify zero-duration coordination/decision tasks that block downstream work.

Logic:
```
IF Varighed = 0 (0 d, 0 u)
AND (Opgavenavn contains decision keywords
     OR Ansvarlig = "BH" (client delivery))
THEN classify as decision bottleneck
```

Decision keywords (Danish): godkendelse, beslutning, valg, placering, koordinering, overdragelse, mangelgennemgang, leverance, afleveringsforretning, bemyndigelse, ibrugtagning, tilslutning
Decision keywords (English): approval, decision, selection, placement, coordination, handover, inspection, commissioning

Output per flagged task:
| Entydigt id | Opgavenavn | Ansvarlig | Planned Date | Downstream Risk |

Example:
| 9801 | BH Godkendelse brandkomponenter | BH | 15-03-2025 | Blocks fire safety installation on E2-E4 |

---

## DETECTION MODULE E: Artificial Scheduling Clusters

Purpose: Detect unrealistic planning where many tasks share the same start date.

Logic:
```
Group tasks by Startdato within same Etage or same Ansvarlig
IF group_size >= 5 THEN flag as potential placeholder planning
IF group_size >= 9 THEN flag as highly likely placeholder
```

Output per cluster:
| Cluster Date | Count | Etage/Discipline | Assessment |

Assessment rules:
- 5-7 tasks same date: "Possible planning placeholder — verify with planner"
- 8+ tasks same date: "Likely placeholder planning — unrealistic parallel start"
- Exception: if tasks span different Etage AND different Ansvarlig, may be realistic phased start

Example:
| 09-02-2025 | 8 tasks | E3 / EL | Likely placeholder — 8 electrical tasks cannot realistically start simultaneously |

---

## DETECTION MODULE F: Long Duration Activities

Purpose: Flag tasks with excessive duration that carry elevated monitoring risk.

Logic:
```
IF Varighed > 90 days (or > 12 weeks) THEN flag
IF Varighed > 120 days THEN flag as critical duration risk
```

Output per flagged task:
| Entydigt id | Opgavenavn | Varighed | % færdigt | Risk Level |

Risk levels:
- 90-120 days: "Elevated — difficult to track progress accurately"
- >120 days: "High — significant risk of hidden delays"

Example:
| 9650 | Project Engineering Completion | 125 d | 40% | High — 125 days duration, progress verification recommended |

---

## DETECTION MODULE G: Discipline Progress Dashboard

Purpose: Group all tasks by responsible trade and compute progress metrics.

For each unique Ansvarlig value, compute:
- Total tasks in discipline
- Average % færdigt across all tasks
- Count of tasks not started (% færdigt = 0)
- Count of tasks completed (% færdigt = 100)
- Discipline health: "Healthy" (avg >70%), "Attention" (40-70%), "At Risk" (<40%), "Critical" (<20%)

Output:
| Discipline | Total Tasks | Avg Progress | Not Started | Completed | Health |

Example:
| EL | 45 | 58% | 7 | 12 | Attention |
| TØ | 32 | 72% | 3 | 15 | Healthy |
| BH | 8 | 0% | 8 | 0 | Critical |

---

## SCHEDULE COMPLEXITY SCORE

Compute from:
- Total number of activities in NEW schedule
- Number of distinct Etage values (floors)
- Number of distinct Ansvarlig values (disciplines)
- Estimated dependency chain depth (longest inferred chain from Module C)
- Number of inferred dependencies (from Module C graph-building)

Scoring:
- Low: <50 activities, <3 floors
- Medium: 50-200 activities, 3-5 floors
- High: 200-500 activities, 5+ floors, 8+ disciplines
- Very High: 500+ activities, complex multi-floor dependency networks

---

## PREDICTIVE DELAY ENGINE

This is the most critical output. Combine ALL module findings.

Step 1 — Count findings:
```
overdue_count = Module A flagged tasks
anomaly_count = Module B flagged tasks
chain_risk_count = Module C high/critical chains
bottleneck_count = Module D flagged decisions
cluster_count = Module E flagged clusters
long_duration_count = Module F flagged tasks
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
- The floor, discipline, or dependency chain contributing the most risk points

---

<output>
## MANDATORY OUTPUT STRUCTURE

```
## NOVA_INSIGHT_REPORT

### SCHEDULE_OVERVIEW
- Total activities: [X]
- Floors covered: [list]
- Disciplines involved: [list]
- Inferred dependencies: [X]
- Schedule complexity: [Low/Medium/High/Very High]

### SCHEDULE_HEALTH_OVERVIEW
• [X] activities should have started
• [X] progress anomalies detected
• [X] blocked decision points
• [X] critical dependency chains
• [X] scheduling clusters flagged
• [X] long-duration risks
Risk level: [Low/Medium/High/Critical]

### MODULE_A_OVERDUE
[Table or "No overdue tasks detected"]

### MODULE_B_PROGRESS_ANOMALIES
[Table or "No progress anomalies detected"]

### MODULE_C_DEPENDENCY_CHAINS
[Chain descriptions or "No high-risk chains detected"]

### MODULE_D_DECISION_BOTTLENECKS
[Table or "No decision bottlenecks detected"]

### MODULE_E_SCHEDULING_CLUSTERS
[Cluster descriptions or "No artificial clusters detected"]

### MODULE_F_LONG_DURATION_RISKS
[Table or "No long-duration risks detected"]

### MODULE_G_DISCIPLINE_PROGRESS
[Discipline progress table]

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

<!--INSIGHT_DATA:{"delay_risk":"low|medium|high|critical","delay_risk_score":X,"delay_risk_percent":X,"estimated_delay_days_min":X,"estimated_delay_days_max":X,"primary_risk_source":"...","overdue_count":X,"anomaly_count":X,"chain_risk_count":X,"bottleneck_count":X,"cluster_count":X,"long_duration_count":X,"complexity":"low|medium|high|very_high","total_activities":X}-->
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
""",
    "en": """
Respond in English.
Use English header: `## NOVA_INSIGHT_REPORT`
Use English section: `### SCHEDULE_HEALTH_OVERVIEW`
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
        language: str = "en"
    ) -> dict:
        logger.info(f"  [PredictiveAgent] Starting analysis with {self.deployment}...")

        lang_instruction = PREDICTIVE_LANGUAGE_INSTRUCTIONS.get(
            language, PREDICTIVE_LANGUAGE_INSTRUCTIONS["en"]
        )
        system_prompt = f"{PREDICTIVE_SYSTEM_PROMPT}\n\n{lang_instruction}"

        user_message = f"""Analyze the following construction schedule data. Produce a complete Nova Insight predictive report.

═══════════════════════════════════════════════════════════
COMPLETE SCHEDULE DATA FROM BOTH VECTOR STORES:
═══════════════════════════════════════════════════════════
{context}
═══════════════════════════════════════════════════════════

USER QUERY FOR CONTEXT: {user_query}

═══════════════════════════════════════════════════════════
EXECUTION STEPS:
═══════════════════════════════════════════════════════════
1. Parse ALL task rows from the NEW schedule — extract Entydigt id, Opgavenavn, Etage, Ansvarlig, Varighed, Startdato, Slutdato, % færdigt for each row
2. Determine reference date: use the latest Slutdato visible in the data
3. Execute Module A: scan every task for Startdato < reference_date AND % færdigt = 0
4. Execute Module B: for every task with 0 < % færdigt < 100, calculate Expected % and check deviation > 25%
5. Execute Module C: build dependency graph from Etage+dates+trade sequence, find chains > 4 tasks
6. Execute Module D: find all Varighed = 0 tasks with decision keywords or Ansvarlig = BH
7. Execute Module E: group by Startdato within same Etage or Ansvarlig, flag groups >= 5
8. Execute Module F: find all tasks with Varighed > 90 days
9. Execute Module G: group all tasks by Ansvarlig, compute averages
10. Compute Schedule Complexity Score
11. Run Predictive Delay Engine with exact formula
12. Output complete NOVA_INSIGHT_REPORT with all sections including <!--INSIGHT_DATA:{{...}}-->
═══════════════════════════════════════════════════════════"""

        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            api_params = {
                "model": self.deployment,
                "messages": messages,
                "temperature": 0.1,
                "max_completion_tokens": 32000,
            }

            try:
                api_params["reasoning_effort"] = "high"
                response = self.client.chat.completions.create(**api_params)
            except Exception as reasoning_err:
                if "reasoning_effort" in str(reasoning_err) or "Unrecognized" in str(reasoning_err):
                    logger.warning(f"  [PredictiveAgent] reasoning_effort not supported, falling back without it")
                    del api_params["reasoning_effort"]
                    response = self.client.chat.completions.create(**api_params)
                else:
                    raise reasoning_err

            insight_response = response.choices[0].message.content or ""
            model_used = getattr(response, 'model', self.deployment)
            logger.info(f"  [PredictiveAgent] Response received: {len(insight_response)} chars, model: {model_used}")

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
