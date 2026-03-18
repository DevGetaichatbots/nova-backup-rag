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
        return {"color": "#ff4d6a", "bg": "rgba(255, 77, 106, 0.08)", "border": "rgba(255, 77, 106, 0.2)"}
    if level_lower in ["high", "høj"]:
        return {"color": "#f87171", "bg": "rgba(248, 113, 113, 0.08)", "border": "rgba(248, 113, 113, 0.2)"}
    if level_lower in ["medium", "mellem", "elevated"]:
        return {"color": "#fbbf24", "bg": "rgba(251, 191, 36, 0.08)", "border": "rgba(251, 191, 36, 0.2)"}
    return {"color": "#34d399", "bg": "rgba(52, 211, 153, 0.08)", "border": "rgba(52, 211, 153, 0.2)"}


def _health_badge(text: str) -> str:
    lower = text.lower().strip()
    if "critical" in lower or "kritisk" in lower:
        return f'<span style="display:inline-block;padding:4px 12px;border-radius:6px;font-size:11px;font-weight:700;background:rgba(255,77,106,0.15);color:#ff4d6a;border:1px solid rgba(255,77,106,0.25);letter-spacing:0.3px;">{_escape(text)}</span>'
    if "at risk" in lower or "i fare" in lower or "high" in lower or "høj" in lower:
        return f'<span style="display:inline-block;padding:4px 12px;border-radius:6px;font-size:11px;font-weight:700;background:rgba(248,113,113,0.15);color:#f87171;border:1px solid rgba(248,113,113,0.25);letter-spacing:0.3px;">{_escape(text)}</span>'
    if "attention" in lower or "opmærksomhed" in lower or "medium" in lower or "mellem" in lower or "elevated" in lower:
        return f'<span style="display:inline-block;padding:4px 12px;border-radius:6px;font-size:11px;font-weight:700;background:rgba(251,191,36,0.15);color:#fbbf24;border:1px solid rgba(251,191,36,0.25);letter-spacing:0.3px;">{_escape(text)}</span>'
    if "healthy" in lower or "sund" in lower or "low" in lower or "lav" in lower or "on track" in lower:
        return f'<span style="display:inline-block;padding:4px 12px;border-radius:6px;font-size:11px;font-weight:700;background:rgba(52,211,153,0.15);color:#34d399;border:1px solid rgba(52,211,153,0.25);letter-spacing:0.3px;">{_escape(text)}</span>'
    return f'<span style="display:inline-block;padding:4px 12px;border-radius:6px;font-size:11px;font-weight:700;background:rgba(148,163,184,0.12);color:#94a3b8;border:1px solid rgba(148,163,184,0.2);letter-spacing:0.3px;">{_escape(text)}</span>'


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
        f'<th style="padding:12px 14px;text-align:left;font-size:10px;font-weight:700;color:{accent_color};text-transform:uppercase;letter-spacing:1.2px;white-space:nowrap;border-bottom:2px solid {accent_color}30;background:transparent;">{_escape(h)}</th>'
        for h in headers
    )

    rows_html = []
    for idx, row in enumerate(rows):
        cells_html = ""
        for ci, cell in enumerate(row):
            h_name = headers[ci].lower() if ci < len(headers) else ""
            if any(k in h_name for k in ["health", "risk", "sundhed", "risiko", "type", "assessment", "level", "status"]):
                content = _health_badge(cell)
            elif ci == 0:
                content = f'<span style="font-weight:600;color:#e2e8f0;font-size:13px;">{_escape(cell)}</span>'
            else:
                content = f'<span style="color:#94a3b8;font-size:13px;">{_escape(cell)}</span>'
            cells_html += f'<td style="padding:11px 14px;border-bottom:1px solid rgba(148,163,184,0.08);vertical-align:middle;">{content}</td>'
        rows_html.append(f'<tr style="transition:background 0.15s;">{cells_html}</tr>')

    return f'''<div style="overflow-x:auto;border-radius:10px;margin:14px 0;background:#1e293b;border:1px solid rgba(148,163,184,0.1);">
<table style="width:100%;min-width:500px;border-collapse:collapse;">
<thead><tr>{header_html}</tr></thead>
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
                f'<li style="margin:7px 0;line-height:1.65;padding-left:18px;position:relative;font-size:13px;color:#cbd5e1;"><span style="position:absolute;left:0;color:{accent_color};font-weight:bold;font-size:14px;">›</span>{item}</li>'
                for item in list_items
            )
            parts.append(f'<ul style="margin:10px 0;padding-left:0;list-style:none;">{items}</ul>')
            list_items = []

    in_code_block = False
    code_lines = []

    def flush_code():
        nonlocal code_lines, in_code_block
        if code_lines:
            code_text = _escape("\n".join(code_lines))
            parts.append(f'<pre style="margin:12px 0;padding:14px 16px;background:rgba(0,0,0,0.3);border-radius:8px;border:1px solid rgba(148,163,184,0.1);overflow-x:auto;"><code style="font-family:\'SF Mono\',SFMono-Regular,Menlo,Consolas,monospace;font-size:12px;color:#94a3b8;line-height:1.6;">{code_text}</code></pre>')
            code_lines = []
        in_code_block = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                flush_code()
            else:
                flush_table()
                flush_list()
                in_code_block = True
            continue

        if in_code_block:
            code_lines.append(line.rstrip())
            continue

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
            item_raw = stripped[2:]
            item_safe = _escape(item_raw)
            item_safe = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color:#e2e8f0;font-weight:600;">\1</strong>', item_safe)
            list_items.append(item_safe)
            continue

        flush_list()

        safe = _escape(stripped)

        if re.match(r"^(Chain|Path|Length|Risk|Weakest|Downstream|Cluster|Score|Complexity|Weighted)", stripped, re.IGNORECASE):
            text = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color:#e2e8f0;">\1</strong>', safe)
            parts.append(f'<p style="margin:5px 0;color:#94a3b8;line-height:1.6;font-size:12px;font-family:\'SF Mono\',SFMono-Regular,Menlo,monospace;background:rgba(0,0,0,0.2);padding:6px 12px;border-radius:6px;border-left:2px solid {accent_color};">{text}</p>')
            continue

        text = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color:#e2e8f0;font-weight:600;">\1</strong>', safe)
        parts.append(f'<p style="margin:7px 0;color:#cbd5e1;line-height:1.7;font-size:14px;">{text}</p>')

    flush_code()
    flush_table()
    flush_list()
    return "".join(parts)


def _build_metrics_bar(insight_data: Dict, language: str) -> str:
    if not insight_data:
        return ""

    risk_level = insight_data.get("delay_risk") or "low"
    risk_colors = _get_risk_color(risk_level)
    risk_pct = insight_data.get("delay_risk_percent") or 0
    delay_min = insight_data.get("estimated_delay_days_min") or 0
    delay_max = insight_data.get("estimated_delay_days_max") or 0
    def _safe_int(val):
        try:
            return int(round(float(val)))
        except (ValueError, TypeError):
            return 0
    risk_pct = _safe_int(risk_pct)
    delay_min = _safe_int(delay_min)
    delay_max = _safe_int(delay_max)

    metrics = [
        {"value": insight_data.get("overdue_count") or 0, "label": "Forfalden" if language == "da" else "Overdue", "color": "#f87171"},
        {"value": insight_data.get("anomaly_count") or 0, "label": "Anomalier" if language == "da" else "Anomalies", "color": "#fbbf24"},
        {"value": insight_data.get("chain_risk_count") or 0, "label": "Kæderisici" if language == "da" else "Chain Risks", "color": "#a78bfa"},
        {"value": insight_data.get("bottleneck_count") or 0, "label": "Flaskehalse" if language == "da" else "Bottlenecks", "color": "#fb923c"},
        {"value": insight_data.get("cluster_count") or 0, "label": "Klynger" if language == "da" else "Clusters", "color": "#22d3ee"},
        {"value": insight_data.get("long_duration_count") or 0, "label": "Lang Varighed" if language == "da" else "Long Duration", "color": "#f87171"},
    ]

    metrics_html = "".join(
        f'<div style="text-align:center;padding:14px 6px;background:rgba(0,0,0,0.2);border-radius:10px;border:1px solid {m["color"]}15;min-width:80px;">'
        f'<div style="font-size:26px;font-weight:800;color:{m["color"]};line-height:1;">{m["value"]}</div>'
        f'<div style="font-size:9px;color:#64748b;text-transform:uppercase;margin-top:5px;font-weight:700;letter-spacing:0.8px;">{m["label"]}</div></div>'
        for m in metrics
    )

    risk_label = risk_level.upper()
    delay_text = f"{delay_min}–{delay_max} {'dage' if language == 'da' else 'days'}" if delay_max > 0 else "N/A"

    return f'''
<div style="margin:0 0 20px 0;padding:22px;background:#1e293b;border-radius:14px;border:1px solid {risk_colors["border"]};">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;flex-wrap:wrap;gap:14px;">
    <div>
      <div style="font-size:10px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:1.2px;margin-bottom:4px;">{"Forsinkelsesrisiko" if language == "da" else "Delay Risk"}</div>
      <div style="font-size:36px;font-weight:900;color:{risk_colors["color"]};line-height:1;">{risk_pct}<span style="font-size:18px;color:#64748b;">%</span></div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;padding:8px 18px;border-radius:8px;background:rgba(0,0,0,0.25);border:1px solid {risk_colors["border"]};">
      <div style="width:8px;height:8px;border-radius:50%;background:{risk_colors["color"]};box-shadow:0 0 10px {risk_colors["color"]};"></div>
      <span style="font-size:12px;font-weight:700;color:{risk_colors["color"]};text-transform:uppercase;letter-spacing:0.8px;">{risk_label}</span>
    </div>
    <div style="text-align:right;">
      <div style="font-size:10px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:1.2px;margin-bottom:4px;">{"Estimeret Forsinkelse" if language == "da" else "Est. Delay"}</div>
      <div style="font-size:20px;font-weight:700;color:#e2e8f0;">{delay_text}</div>
    </div>
  </div>
  <div style="width:100%;height:6px;background:rgba(0,0,0,0.3);border-radius:3px;overflow:hidden;margin-bottom:18px;">
    <div style="width:{min(risk_pct, 100)}%;height:100%;background:linear-gradient(90deg,{risk_colors["color"]},transparent);border-radius:3px;"></div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(85px,1fr));gap:8px;">{metrics_html}</div>
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

    try:
        return _format_predictive_internal(markdown, language)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Predictive HTML formatter error: {e}")
        safe_text = _escape(markdown)
        return f'<div class="nova-report" style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;padding:24px;background:#0f172a;border-radius:16px;"><h2 style="color:#e2e8f0;margin-bottom:16px;">Nova Insight Report</h2><div style="white-space:pre-wrap;color:#94a3b8;line-height:1.7;font-size:13px;">{safe_text}</div></div>'


def _format_predictive_internal(markdown: str, language: str) -> str:
    insight_data = _parse_insight_data(markdown)
    sections = _split_sections(markdown)

    report_title = "Nova Insight Rapport" if language == "da" else "Nova Insight Report"

    html_parts = [f'''
<style>
.nova-report .module-card:hover {{ border-color: rgba(148,163,184,0.2) !important; }}
.nova-report table tr:hover {{ background: rgba(148,163,184,0.06) !important; }}
.nova-report ::-webkit-scrollbar {{ height:6px; }}
.nova-report ::-webkit-scrollbar-track {{ background:rgba(0,0,0,0.2);border-radius:6px; }}
.nova-report ::-webkit-scrollbar-thumb {{ background:rgba(148,163,184,0.3);border-radius:6px; }}
</style>
<div class="nova-report" style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0f172a;border-radius:20px;padding:28px;border:1px solid rgba(148,163,184,0.1);">
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:24px;padding-bottom:24px;border-bottom:1px solid rgba(148,163,184,0.1);">
    <div style="width:48px;height:48px;border-radius:12px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#00D6D6,#0891b2);box-shadow:0 0 24px rgba(0,214,214,0.2);">
      <span style="color:white;">{NOVA_ICONS["report"]}</span>
    </div>
    <div style="flex:1;">
      <h2 style="font-size:20px;font-weight:800;color:#f1f5f9;margin:0;letter-spacing:-0.3px;">{report_title}</h2>
      <p style="font-size:12px;color:#64748b;margin:3px 0 0 0;letter-spacing:0.3px;">{"Forudsigende risikoanalyse · GPT-5.2" if language == "da" else "Predictive risk analysis · GPT-5.2"}</p>
    </div>
    <div style="padding:6px 14px;border-radius:6px;background:rgba(0,214,214,0.1);border:1px solid rgba(0,214,214,0.2);">
      <span style="font-size:10px;font-weight:700;color:#00D6D6;text-transform:uppercase;letter-spacing:1px;">AI</span>
    </div>
  </div>''']

    if insight_data:
        html_parts.append(_build_metrics_bar(insight_data, language))

    for section_key, section_body in sections:
        if section_key == "_PREAMBLE":
            html_parts.append(f'<div style="margin:0 0 16px 0;padding:14px 18px;background:rgba(0,214,214,0.04);border-radius:10px;border-left:3px solid #00D6D6;">')
            html_parts.append(_render_content_block(section_body.split("\n"), "#22d3ee"))
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
  <div class="module-card" style="margin:0 0 16px 0;padding:20px;background:#1e293b;border-radius:14px;border:1px solid rgba(148,163,184,0.08);border-left:3px solid {color};transition:border-color 0.2s ease;">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
      <div style="width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;background:{color}18;">
        <span style="color:{color};">{icon_svg}</span>
      </div>
      <h3 style="font-size:15px;font-weight:700;color:#f1f5f9;margin:0;letter-spacing:-0.2px;">{label}</h3>
    </div>
    {content_html}
  </div>''')

    html_parts.append('</div>')
    return "".join(html_parts)
