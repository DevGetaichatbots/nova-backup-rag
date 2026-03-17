import re
import json
import html
from typing import Dict, List, Optional, Tuple

NOVA_ICONS = {
    "report": '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4zm2 2H5V5h14v14zM19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z" fill="currentColor"/></svg>',
    "overview": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path d="M12 6v6l4 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    "overdue": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#ef4444" opacity="0.15"/><path d="M12 8v4M12 16h.01" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round"/></svg>',
    "anomaly": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M12 2L2 22h20L12 2z" fill="#f59e0b" opacity="0.15"/><path d="M12 9v4M12 17h.01" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round"/></svg>',
    "chain": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#8b5cf6" opacity="0.15"/><path d="M7 12h10M12 7l5 5-5 5" stroke="#8b5cf6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "bottleneck": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#f97316" opacity="0.15"/><path d="M12 8v8M8 12h8" stroke="#f97316" stroke-width="2.5" stroke-linecap="round"/></svg>',
    "cluster": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="18" height="18" rx="2" fill="#06b6d4" opacity="0.15"/><circle cx="8" cy="8" r="2" fill="#06b6d4"/><circle cx="16" cy="8" r="2" fill="#06b6d4"/><circle cx="8" cy="16" r="2" fill="#06b6d4"/><circle cx="16" cy="16" r="2" fill="#06b6d4"/></svg>',
    "duration": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#dc2626" opacity="0.15"/><path d="M12 6v6l3 3" stroke="#dc2626" stroke-width="2" stroke-linecap="round"/></svg>',
    "discipline": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="18" height="18" rx="2" fill="#10b981" opacity="0.15"/><path d="M7 8h10M7 12h10M7 16h6" stroke="#10b981" stroke-width="2" stroke-linecap="round"/></svg>',
    "engine": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#ef4444" opacity="0.15"/><path d="M22 12h-4l-3 9L9 3l-3 9H2" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "health": '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M22 12h-4l-3 9L9 3l-3 9H2" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
}

MODULE_CONFIG = {
    "SCHEDULE_OVERVIEW": {"label_en": "Schedule Overview", "label_da": "Tidsplanoversigt", "color": "#0ea5e9", "icon": "overview"},
    "SCHEDULE_HEALTH_OVERVIEW": {"label_en": "Schedule Health Overview", "label_da": "Tidsplan Sundhedsoverblik", "color": "#8b5cf6", "icon": "health"},
    "TIDSPLAN_SUNDHEDSOVERBLIK": {"label_en": "Schedule Health Overview", "label_da": "Tidsplan Sundhedsoverblik", "color": "#8b5cf6", "icon": "health"},
    "MODULE_A_OVERDUE": {"label_en": "Module A: Overdue Activities", "label_da": "Modul A: Forfaldne Aktiviteter", "color": "#ef4444", "icon": "overdue"},
    "MODULE_B_PROGRESS_ANOMALIES": {"label_en": "Module B: Progress Anomalies", "label_da": "Modul B: Fremdriftsanomalier", "color": "#f59e0b", "icon": "anomaly"},
    "MODULE_C_DEPENDENCY_CHAINS": {"label_en": "Module C: Dependency Chain Risks", "label_da": "Modul C: Afhængighedskæderisici", "color": "#8b5cf6", "icon": "chain"},
    "MODULE_D_DECISION_BOTTLENECKS": {"label_en": "Module D: Decision Bottlenecks", "label_da": "Modul D: Beslutningsflaskehalse", "color": "#f97316", "icon": "bottleneck"},
    "MODULE_E_SCHEDULING_CLUSTERS": {"label_en": "Module E: Scheduling Clusters", "label_da": "Modul E: Planlægningsklynger", "color": "#06b6d4", "icon": "cluster"},
    "MODULE_F_LONG_DURATION_RISKS": {"label_en": "Module F: Long Duration Risks", "label_da": "Modul F: Lang Varighedsrisici", "color": "#dc2626", "icon": "duration"},
    "MODULE_G_DISCIPLINE_PROGRESS": {"label_en": "Module G: Discipline Progress", "label_da": "Modul G: Disciplinfremdrift", "color": "#10b981", "icon": "discipline"},
    "PREDICTIVE_DELAY_ENGINE": {"label_en": "Predictive Delay Engine", "label_da": "Forudsigende Forsinkelsesmotor", "color": "#ef4444", "icon": "engine"},
    "SCHEDULE_COMPLEXITY_SCORE": {"label_en": "Schedule Complexity Score", "label_da": "Tidsplan Kompleksitetsscore", "color": "#8b5cf6", "icon": "overview"},
}


def _escape(text: str) -> str:
    if not text:
        return ""
    return html.escape(str(text))


def _parse_insight_data(markdown: str) -> Optional[Dict]:
    match = re.search(r"<!--INSIGHT_DATA:(.*?)-->", markdown, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    return None


def _get_risk_color(level: str) -> dict:
    level_lower = (level or "").lower()
    if level_lower in ["critical", "kritisk"]:
        return {"color": "#dc2626", "bg": "rgba(220, 38, 38, 0.1)", "border": "rgba(220, 38, 38, 0.25)"}
    if level_lower in ["high", "høj"]:
        return {"color": "#ef4444", "bg": "rgba(239, 68, 68, 0.1)", "border": "rgba(239, 68, 68, 0.25)"}
    if level_lower in ["medium", "mellem", "elevated"]:
        return {"color": "#f59e0b", "bg": "rgba(245, 158, 11, 0.1)", "border": "rgba(245, 158, 11, 0.25)"}
    return {"color": "#10b981", "bg": "rgba(16, 185, 129, 0.1)", "border": "rgba(16, 185, 129, 0.25)"}


def _health_badge(text: str) -> str:
    lower = text.lower().strip()
    if "critical" in lower or "kritisk" in lower:
        return f'<span style="display:inline-block;padding:4px 12px;border-radius:8px;font-size:12px;font-weight:700;background:rgba(220,38,38,0.12);color:#dc2626;border:1px solid rgba(220,38,38,0.2);">{_escape(text)}</span>'
    if "at risk" in lower or "i fare" in lower or "high" in lower or "høj" in lower:
        return f'<span style="display:inline-block;padding:4px 12px;border-radius:8px;font-size:12px;font-weight:700;background:rgba(239,68,68,0.12);color:#ef4444;border:1px solid rgba(239,68,68,0.2);">{_escape(text)}</span>'
    if "attention" in lower or "opmærksomhed" in lower or "medium" in lower or "mellem" in lower or "elevated" in lower:
        return f'<span style="display:inline-block;padding:4px 12px;border-radius:8px;font-size:12px;font-weight:700;background:rgba(245,158,11,0.12);color:#d97706;border:1px solid rgba(245,158,11,0.2);">{_escape(text)}</span>'
    if "healthy" in lower or "sund" in lower or "low" in lower or "lav" in lower:
        return f'<span style="display:inline-block;padding:4px 12px;border-radius:8px;font-size:12px;font-weight:700;background:rgba(16,185,129,0.12);color:#059669;border:1px solid rgba(16,185,129,0.2);">{_escape(text)}</span>'
    return f'<span style="display:inline-block;padding:4px 12px;border-radius:8px;font-size:12px;font-weight:700;background:rgba(100,116,139,0.1);color:#475569;border:1px solid rgba(100,116,139,0.15);">{_escape(text)}</span>'


def _render_table(markdown_lines: List[str], accent_color: str) -> str:
    rows = []
    headers = []
    for line in markdown_lines:
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        if re.match(r"^\|[\s\-:|]+\|$", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not headers:
            headers = cells
        else:
            rows.append(cells)

    if not headers:
        return ""

    header_html = "".join(
        f'<th style="padding:14px 16px;text-align:left;font-size:11px;font-weight:700;color:rgba(255,255,255,0.95);text-transform:uppercase;letter-spacing:1px;white-space:nowrap;border-right:1px solid rgba(255,255,255,0.08);">{_escape(h)}</th>'
        for h in headers
    )

    rows_html = []
    for idx, row in enumerate(rows):
        bg = "#ffffff" if idx % 2 == 0 else "rgba(248,250,252,0.8)"
        cells_html = ""
        for ci, cell in enumerate(row):
            h_name = headers[ci].lower() if ci < len(headers) else ""
            if any(k in h_name for k in ["health", "risk", "sundhed", "risiko", "type", "assessment", "level"]):
                content = _health_badge(cell)
            elif ci == 0:
                content = f'<span style="font-weight:600;color:#1e293b;">{_escape(cell)}</span>'
            else:
                content = f'<span style="color:#475569;font-size:14px;">{_escape(cell)}</span>'
            cells_html += f'<td style="padding:14px 16px;font-size:14px;border-bottom:1px solid #f1f5f9;border-right:1px solid #f1f5f9;vertical-align:middle;">{content}</td>'
        rows_html.append(f'<tr style="background:{bg};transition:all 0.2s ease;">{cells_html}</tr>')

    return f'''<div style="overflow-x:auto;border-radius:16px;box-shadow:0 4px 16px rgba(0,0,0,0.06),0 0 0 1px {accent_color}20;margin:16px 0;">
<table style="width:100%;min-width:600px;border-collapse:separate;border-spacing:0;">
<thead><tr style="background:linear-gradient(135deg,#0f172a,#1e293b);">{header_html}</tr></thead>
<tbody>{"".join(rows_html)}</tbody>
</table></div>'''


def _render_content_block(lines: List[str], accent_color: str) -> str:
    parts = []
    table_lines = []
    list_items = []

    def flush_table():
        nonlocal table_lines
        if table_lines:
            parts.append(_render_table(table_lines, accent_color))
            table_lines = []

    def flush_list():
        nonlocal list_items
        if list_items:
            items = "".join(
                f'<li style="margin:8px 0;line-height:1.7;padding-left:20px;position:relative;"><span style="position:absolute;left:0;color:{accent_color};font-weight:bold;">•</span>{item}</li>'
                for item in list_items
            )
            parts.append(f'<ul style="margin:12px 0;padding-left:0;list-style:none;">{items}</ul>')
            list_items = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_table()
            flush_list()
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            flush_list()
            table_lines.append(stripped)
            continue

        flush_table()

        if stripped.startswith("- ") or stripped.startswith("• ") or stripped.startswith("* "):
            item = stripped[2:]
            item = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color:#1e293b;font-weight:600;">\1</strong>', item)
            list_items.append(item)
            continue

        flush_list()

        if stripped.startswith("```"):
            continue

        bold_line = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color:#1e293b;font-weight:600;">\1</strong>', _escape(stripped))
        bold_line = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color:#1e293b;font-weight:600;">\1</strong>', stripped)

        if re.match(r"^(Chain|Path|Length|Risk|Weakest|Downstream|Cluster)", stripped, re.IGNORECASE):
            text = re.sub(r"\*\*([^*]+)\*\*", r'<strong>\1</strong>', stripped)
            parts.append(f'<p style="margin:6px 0;color:#334155;line-height:1.6;font-size:14px;font-family:monospace;background:rgba(0,0,0,0.03);padding:6px 12px;border-radius:8px;border-left:3px solid {accent_color};">{text}</p>')
            continue

        text = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color:#1e293b;font-weight:600;">\1</strong>', stripped)
        parts.append(f'<p style="margin:8px 0;color:#334155;line-height:1.7;font-size:15px;">{text}</p>')

    flush_table()
    flush_list()
    return "".join(parts)


def _build_metrics_bar(insight_data: Dict, language: str) -> str:
    if not insight_data:
        return ""

    risk_level = insight_data.get("delay_risk", "low")
    risk_colors = _get_risk_color(risk_level)
    risk_pct = insight_data.get("delay_risk_percent", 0)
    delay_min = insight_data.get("estimated_delay_days_min", 0)
    delay_max = insight_data.get("estimated_delay_days_max", 0)

    metrics = [
        {"value": insight_data.get("overdue_count", 0), "label": "Forfalden" if language == "da" else "Overdue", "color": "#ef4444"},
        {"value": insight_data.get("anomaly_count", 0), "label": "Anomalier" if language == "da" else "Anomalies", "color": "#f59e0b"},
        {"value": insight_data.get("chain_risk_count", 0), "label": "Kæderisici" if language == "da" else "Chain Risks", "color": "#8b5cf6"},
        {"value": insight_data.get("bottleneck_count", 0), "label": "Flaskehalse" if language == "da" else "Bottlenecks", "color": "#f97316"},
        {"value": insight_data.get("cluster_count", 0), "label": "Klynger" if language == "da" else "Clusters", "color": "#06b6d4"},
        {"value": insight_data.get("long_duration_count", 0), "label": "Lang Varighed" if language == "da" else "Long Duration", "color": "#dc2626"},
    ]

    metrics_html = "".join(
        f'<div style="text-align:center;padding:16px 8px;background:linear-gradient(135deg,{m["color"]}0d,{m["color"]}05);border-radius:14px;border:1px solid {m["color"]}20;min-width:90px;">'
        f'<div style="font-size:28px;font-weight:800;color:{m["color"]};">{m["value"]}</div>'
        f'<div style="font-size:10px;color:#64748b;text-transform:uppercase;margin-top:4px;font-weight:600;letter-spacing:0.5px;">{m["label"]}</div></div>'
        for m in metrics
    )

    risk_label = risk_level.upper()
    delay_text = f"{delay_min}-{delay_max} {'dage' if language == 'da' else 'days'}" if delay_max > 0 else "N/A"

    return f'''
<div style="margin:24px 0;padding:24px;background:linear-gradient(135deg,{risk_colors["bg"]},rgba(255,255,255,0.9));border-radius:20px;border:2px solid {risk_colors["border"]};">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:16px;">
    <div>
      <div style="font-size:12px;color:#64748b;text-transform:uppercase;font-weight:600;letter-spacing:1px;margin-bottom:4px;">{"Forsinkelsesrisiko" if language == "da" else "Delay Risk"}</div>
      <div style="font-size:32px;font-weight:900;color:{risk_colors["color"]};">{risk_pct}%</div>
    </div>
    <div style="display:flex;align-items:center;gap:12px;padding:12px 24px;border-radius:50px;background:{risk_colors["bg"]};border:2px solid {risk_colors["border"]};">
      <div style="width:12px;height:12px;border-radius:50%;background:{risk_colors["color"]};box-shadow:0 0 8px {risk_colors["color"]}80;"></div>
      <span style="font-size:15px;font-weight:700;color:{risk_colors["color"]};">{risk_label}</span>
    </div>
    <div style="text-align:right;">
      <div style="font-size:12px;color:#64748b;text-transform:uppercase;font-weight:600;letter-spacing:1px;margin-bottom:4px;">{"Estimeret Forsinkelse" if language == "da" else "Est. Delay Window"}</div>
      <div style="font-size:20px;font-weight:700;color:#1e293b;">{delay_text}</div>
    </div>
  </div>
  <div style="width:100%;height:8px;background:rgba(0,0,0,0.06);border-radius:4px;overflow:hidden;margin-bottom:20px;">
    <div style="width:{min(risk_pct, 100)}%;height:100%;background:linear-gradient(90deg,{risk_colors["color"]},{risk_colors["color"]}cc);border-radius:4px;transition:width 0.5s ease;"></div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:10px;">{metrics_html}</div>
</div>'''


def _split_sections(markdown: str) -> List[Tuple[str, str]]:
    cleaned = re.sub(r"<!--INSIGHT_DATA:.*?-->", "", markdown, flags=re.DOTALL).strip()

    section_pattern = r"^###\s+(\S+.*?)$"
    matches = list(re.finditer(section_pattern, cleaned, re.MULTILINE))

    sections = []
    preamble_end = matches[0].start() if matches else len(cleaned)
    preamble = cleaned[:preamble_end].strip()

    report_header = re.match(r"^##\s+(NOVA_INSIGHT_REPORT|NOVA_INSIGHT_RAPPORT)\s*$", preamble, re.MULTILINE)
    if report_header:
        preamble = preamble[report_header.end():].strip()
    if preamble:
        sections.append(("_PREAMBLE", preamble))

    for i, m in enumerate(matches):
        header = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(cleaned)
        body = cleaned[start:end].strip()
        sections.append((header, body))

    return sections


def format_predictive_as_html(markdown: str, language: str = "en") -> str:
    if not markdown or not markdown.strip():
        return ""

    insight_data = _parse_insight_data(markdown)
    sections = _split_sections(markdown)

    report_title = "Nova Insight Rapport" if language == "da" else "Nova Insight Report"

    html_parts = [f'''
<style>
.nova-report .module-card:hover {{ box-shadow: 0 8px 32px rgba(0,0,0,0.1) !important; }}
.nova-report table tr:hover {{ background: rgba(0,214,214,0.04) !important; }}
.nova-report .table-scroll::-webkit-scrollbar {{ height:8px; }}
.nova-report .table-scroll::-webkit-scrollbar-track {{ background:rgba(0,0,0,0.03);border-radius:8px; }}
.nova-report .table-scroll::-webkit-scrollbar-thumb {{ background:linear-gradient(135deg,#00D6D6,#00B8B8);border-radius:8px; }}
</style>
<div class="nova-report" style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:28px;padding:24px;background:linear-gradient(135deg,#0f172a,#1e293b);border-radius:20px;box-shadow:0 12px 40px rgba(15,23,42,0.25);">
    <div style="width:56px;height:56px;border-radius:16px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#00D6D6,#06b6d4);box-shadow:0 8px 24px rgba(0,214,214,0.35);">
      <span style="color:white;">{NOVA_ICONS["report"]}</span>
    </div>
    <div>
      <h2 style="font-size:24px;font-weight:800;color:white;margin:0;">{report_title}</h2>
      <p style="font-size:13px;color:rgba(255,255,255,0.6);margin:4px 0 0 0;">{"Forudsigende risikoanalyse drevet af GPT-5.2" if language == "da" else "Predictive risk analysis powered by GPT-5.2"}</p>
    </div>
  </div>''']

    if insight_data:
        html_parts.append(_build_metrics_bar(insight_data, language))

    for section_key, section_body in sections:
        if section_key == "_PREAMBLE":
            html_parts.append(f'<div style="margin:16px 0;padding:16px 20px;background:rgba(0,214,214,0.04);border-radius:12px;border-left:4px solid #00D6D6;">')
            html_parts.append(_render_content_block(section_body.split("\n"), "#0ea5e9"))
            html_parts.append('</div>')
            continue

        config_key = section_key.upper().replace(" ", "_")
        config = MODULE_CONFIG.get(config_key, None)

        if not config:
            for mk, mv in MODULE_CONFIG.items():
                if mk in config_key or config_key in mk:
                    config = mv
                    break

        if not config:
            config = {"label_en": section_key.replace("_", " ").title(), "label_da": section_key.replace("_", " ").title(), "color": "#64748b", "icon": "overview"}

        label = config["label_da"] if language == "da" else config["label_en"]
        color = config["color"]
        icon_key = config.get("icon", "overview")
        icon_svg = NOVA_ICONS.get(icon_key, NOVA_ICONS["overview"])

        content_html = _render_content_block(section_body.split("\n"), color)

        html_parts.append(f'''
  <div class="module-card" style="margin:20px 0;padding:24px;background:linear-gradient(135deg,{color}08,rgba(255,255,255,0.95));border-radius:20px;box-shadow:0 4px 20px rgba(0,0,0,0.05),0 0 0 1px {color}18;transition:box-shadow 0.3s ease;">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
      <div style="width:40px;height:40px;border-radius:12px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,{color},{color}cc);box-shadow:0 4px 12px {color}30;">
        <span style="color:white;">{icon_svg}</span>
      </div>
      <h3 style="font-size:18px;font-weight:700;color:#0f172a;margin:0;">{label}</h3>
    </div>
    {content_html}
  </div>''')

    html_parts.append('</div>')
    return "".join(html_parts)
