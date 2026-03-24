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
    "chart": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M18 20V10M12 20V4M6 20v-6" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
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
        return {"color": "#ff4d6a", "bg": "rgba(255, 77, 106, 0.08)", "border": "rgba(255, 77, 106, 0.25)", "glow": "rgba(255, 77, 106, 0.4)"}
    if level_lower in ["high", "høj"]:
        return {"color": "#f87171", "bg": "rgba(248, 113, 113, 0.08)", "border": "rgba(248, 113, 113, 0.25)", "glow": "rgba(248, 113, 113, 0.35)"}
    if level_lower in ["medium", "mellem", "elevated"]:
        return {"color": "#fbbf24", "bg": "rgba(251, 191, 36, 0.08)", "border": "rgba(251, 191, 36, 0.25)", "glow": "rgba(251, 191, 36, 0.3)"}
    return {"color": "#34d399", "bg": "rgba(52, 211, 153, 0.08)", "border": "rgba(52, 211, 153, 0.25)", "glow": "rgba(52, 211, 153, 0.3)"}


def _health_badge(text: str) -> str:
    lower = text.lower().strip()
    if "critical" in lower or "kritisk" in lower:
        return f'<span style="display:inline-block;padding:4px 14px;border-radius:20px;font-size:11px;font-weight:700;background:rgba(255,77,106,0.12);color:#ff4d6a;border:1px solid rgba(255,77,106,0.2);letter-spacing:0.3px;">{_escape(text)}</span>'
    if "at risk" in lower or "i fare" in lower or "high" in lower or "høj" in lower:
        return f'<span style="display:inline-block;padding:4px 14px;border-radius:20px;font-size:11px;font-weight:700;background:rgba(248,113,113,0.12);color:#f87171;border:1px solid rgba(248,113,113,0.2);letter-spacing:0.3px;">{_escape(text)}</span>'
    if "attention" in lower or "opmærksomhed" in lower or "medium" in lower or "mellem" in lower or "elevated" in lower:
        return f'<span style="display:inline-block;padding:4px 14px;border-radius:20px;font-size:11px;font-weight:700;background:rgba(251,191,36,0.12);color:#fbbf24;border:1px solid rgba(251,191,36,0.2);letter-spacing:0.3px;">{_escape(text)}</span>'
    if "healthy" in lower or "sund" in lower or "low" in lower or "lav" in lower or "on track" in lower:
        return f'<span style="display:inline-block;padding:4px 14px;border-radius:20px;font-size:11px;font-weight:700;background:rgba(52,211,153,0.12);color:#34d399;border:1px solid rgba(52,211,153,0.2);letter-spacing:0.3px;">{_escape(text)}</span>'
    return f'<span style="display:inline-block;padding:4px 14px;border-radius:20px;font-size:11px;font-weight:700;background:rgba(148,163,184,0.1);color:#94a3b8;border:1px solid rgba(148,163,184,0.15);letter-spacing:0.3px;">{_escape(text)}</span>'


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
        f'<th style="padding:13px 16px;text-align:left;font-size:10px;font-weight:700;color:{accent_color};text-transform:uppercase;letter-spacing:1.2px;white-space:nowrap;border-bottom:2px solid {accent_color}25;background:rgba(0,0,0,0.15);">{_escape(h)}</th>'
        for h in headers
    )

    rows_html = []
    for idx, row in enumerate(rows):
        bg = "rgba(0,0,0,0.06)" if idx % 2 == 0 else "transparent"
        cells_html = ""
        for ci, cell in enumerate(row):
            h_name = headers[ci].lower() if ci < len(headers) else ""
            if any(k in h_name for k in ["health", "risk", "sundhed", "risiko", "type", "assessment", "level", "status"]):
                content = _health_badge(cell)
            elif ci == 0:
                content = f'<span style="font-weight:600;color:#e2e8f0;font-size:13px;">{_escape(cell)}</span>'
            else:
                content = f'<span style="color:#94a3b8;font-size:13px;">{_escape(cell)}</span>'
            cells_html += f'<td style="padding:12px 16px;border-bottom:1px solid rgba(148,163,184,0.06);vertical-align:middle;">{content}</td>'
        rows_html.append(f'<tr style="background:{bg};transition:background 0.15s;">{cells_html}</tr>')

    return f'''<div style="overflow-x:auto;border-radius:12px;margin:14px 0;background:#162032;border:1px solid rgba(148,163,184,0.08);">
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
                f'<li style="margin:7px 0;line-height:1.65;padding-left:20px;position:relative;font-size:13px;color:#cbd5e1;"><span style="position:absolute;left:0;color:{accent_color};font-weight:bold;font-size:16px;line-height:1.4;">›</span>{item}</li>'
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
            parts.append(f'<pre style="margin:12px 0;padding:14px 16px;background:rgba(0,0,0,0.3);border-radius:10px;border:1px solid rgba(148,163,184,0.08);overflow-x:auto;"><code style="font-family:\'SF Mono\',SFMono-Regular,Menlo,Consolas,monospace;font-size:12px;color:#94a3b8;line-height:1.6;">{code_text}</code></pre>')
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
            parts.append(f'<p style="margin:5px 0;color:#94a3b8;line-height:1.6;font-size:12px;font-family:\'SF Mono\',SFMono-Regular,Menlo,monospace;background:rgba(0,0,0,0.2);padding:8px 14px;border-radius:8px;border-left:3px solid {accent_color};">{text}</p>')
            continue

        text = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color:#e2e8f0;font-weight:600;">\1</strong>', safe)
        parts.append(f'<p style="margin:7px 0;color:#cbd5e1;line-height:1.7;font-size:14px;">{text}</p>')

    flush_code()
    flush_table()
    flush_list()
    return "".join(parts)


def _safe_int(val) -> int:
    try:
        return int(round(float(val)))
    except (ValueError, TypeError):
        return 0


def _build_hero_metrics(insight_data: Dict, language: str) -> str:
    if not insight_data:
        return ""

    risk_level = insight_data.get("delay_risk") or "low"
    risk_colors = _get_risk_color(risk_level)
    risk_pct = _safe_int(insight_data.get("delay_risk_percent") or 0)
    risk_score = _safe_int(insight_data.get("delay_risk_score") or 0)
    delay_min = _safe_int(insight_data.get("estimated_delay_days_min") or 0)
    delay_max = _safe_int(insight_data.get("estimated_delay_days_max") or 0)
    total_activities = _safe_int(insight_data.get("total_activities") or 0)
    dep_links = _safe_int(insight_data.get("dependency_links") or 0)
    longest_chain = _safe_int(insight_data.get("longest_chain") or 0)
    complexity = (insight_data.get("complexity") or "medium").capitalize()

    risk_pct = max(0, min(risk_pct, 100))
    risk_label = _escape(risk_level.upper())
    delay_text = f"{delay_min}–{delay_max}" if delay_max > 0 else "N/A"
    delay_unit = "dage" if language == "da" else "days"
    complexity = _escape(complexity)

    gauge_dash = (risk_pct / 100) * 251.2

    return f'''
<div style="margin:0 0 24px 0;background:linear-gradient(145deg,#162032,#1a2742);border-radius:20px;border:1px solid {risk_colors["border"]};overflow:hidden;position:relative;">
  <div style="position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,transparent,{risk_colors["color"]},{risk_colors["color"]},transparent);opacity:0.6;"></div>
  <div style="padding:28px 28px 20px;">
    <div style="display:flex;align-items:center;gap:28px;flex-wrap:wrap;">
      <div style="position:relative;width:140px;height:80px;flex-shrink:0;">
        <svg viewBox="0 0 200 110" style="width:100%;height:100%;">
          <defs>
            <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" style="stop-color:#34d399"/>
              <stop offset="40%" style="stop-color:#fbbf24"/>
              <stop offset="70%" style="stop-color:#f87171"/>
              <stop offset="100%" style="stop-color:#ff4d6a"/>
            </linearGradient>
          </defs>
          <path d="M 20 95 A 80 80 0 0 1 180 95" fill="none" stroke="rgba(148,163,184,0.1)" stroke-width="12" stroke-linecap="round"/>
          <path d="M 20 95 A 80 80 0 0 1 180 95" fill="none" stroke="url(#gaugeGrad)" stroke-width="12" stroke-linecap="round" stroke-dasharray="0 251.2">
            <animate attributeName="stroke-dasharray" from="0 251.2" to="{gauge_dash} 251.2" dur="1.2s" fill="freeze" calcMode="spline" keySplines="0.4 0 0.2 1"/>
          </path>
          <text x="100" y="75" text-anchor="middle" style="font-family:-apple-system,sans-serif;font-size:32px;font-weight:900;fill:{risk_colors["color"]};">{risk_pct}%</text>
          <text x="100" y="100" text-anchor="middle" style="font-family:-apple-system,sans-serif;font-size:11px;font-weight:600;fill:#64748b;text-transform:uppercase;letter-spacing:1.5px;">{"RISIKO" if language == "da" else "RISK"}</text>
        </svg>
      </div>
      <div style="flex:1;min-width:200px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
          <div style="width:10px;height:10px;border-radius:50%;background:{risk_colors["color"]};box-shadow:0 0 12px {risk_colors["glow"]};"></div>
          <span style="font-size:14px;font-weight:800;color:{risk_colors["color"]};text-transform:uppercase;letter-spacing:1px;">{risk_label}</span>
        </div>
        <div style="display:flex;gap:20px;flex-wrap:wrap;">
          <div>
            <div style="font-size:9px;color:#475569;text-transform:uppercase;font-weight:700;letter-spacing:1px;">{"Score" if language == "da" else "Score"}</div>
            <div style="font-size:22px;font-weight:800;color:#e2e8f0;margin-top:2px;">{risk_score}</div>
          </div>
          <div>
            <div style="font-size:9px;color:#475569;text-transform:uppercase;font-weight:700;letter-spacing:1px;">{"Est. Forsinkelse" if language == "da" else "Est. Delay"}</div>
            <div style="font-size:22px;font-weight:800;color:#e2e8f0;margin-top:2px;">{delay_text} <span style="font-size:12px;color:#475569;">{delay_unit}</span></div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid rgba(148,163,184,0.06);">
    <div style="padding:16px;text-align:center;border-right:1px solid rgba(148,163,184,0.06);">
      <div style="font-size:20px;font-weight:800;color:#e2e8f0;">{total_activities}</div>
      <div style="font-size:9px;color:#475569;text-transform:uppercase;font-weight:700;letter-spacing:0.8px;margin-top:3px;">{"Aktiviteter" if language == "da" else "Activities"}</div>
    </div>
    <div style="padding:16px;text-align:center;border-right:1px solid rgba(148,163,184,0.06);">
      <div style="font-size:20px;font-weight:800;color:#e2e8f0;">{dep_links}</div>
      <div style="font-size:9px;color:#475569;text-transform:uppercase;font-weight:700;letter-spacing:0.8px;margin-top:3px;">{"Afhængigheder" if language == "da" else "Dependencies"}</div>
    </div>
    <div style="padding:16px;text-align:center;border-right:1px solid rgba(148,163,184,0.06);">
      <div style="font-size:20px;font-weight:800;color:#e2e8f0;">{longest_chain}</div>
      <div style="font-size:9px;color:#475569;text-transform:uppercase;font-weight:700;letter-spacing:0.8px;margin-top:3px;">{"Længste Kæde" if language == "da" else "Longest Chain"}</div>
    </div>
    <div style="padding:16px;text-align:center;">
      <div style="font-size:20px;font-weight:800;color:#e2e8f0;">{complexity}</div>
      <div style="font-size:9px;color:#475569;text-transform:uppercase;font-weight:700;letter-spacing:0.8px;margin-top:3px;">{"Kompleksitet" if language == "da" else "Complexity"}</div>
    </div>
  </div>
</div>'''


def _build_analytics_charts(insight_data: Dict, language: str) -> str:
    if not insight_data:
        return ""

    findings = [
        {"key": "overdue_count", "label": "Forfaldne" if language == "da" else "Overdue", "color": "#f87171"},
        {"key": "anomaly_count", "label": "Anomalier" if language == "da" else "Anomalies", "color": "#fbbf24"},
        {"key": "chain_risk_count", "label": "Kæderisici" if language == "da" else "Chain Risks", "color": "#a78bfa"},
        {"key": "bottleneck_count", "label": "Flaskehalse" if language == "da" else "Bottlenecks", "color": "#fb923c"},
        {"key": "cluster_count", "label": "Klynger" if language == "da" else "Clusters", "color": "#22d3ee"},
        {"key": "long_duration_count", "label": "Lang Var." if language == "da" else "Long Dur.", "color": "#f87171"},
    ]

    max_val = max((_safe_int(insight_data.get(f["key"])) for f in findings), default=1)
    if max_val == 0:
        max_val = 1

    bar_width = 100 / len(findings)
    bars_svg = ""
    labels_svg = ""
    for i, f in enumerate(findings):
        val = _safe_int(insight_data.get(f["key"]))
        bar_h = max((val / max_val) * 130, 4)
        x = i * bar_width + bar_width * 0.2
        w = bar_width * 0.6
        y = 160 - bar_h

        bars_svg += f'''
        <rect x="{x}%" y="160" width="{w}%" height="0" rx="4" fill="{f["color"]}" opacity="0.85">
          <animate attributeName="height" from="0" to="{bar_h}" dur="0.8s" begin="{i * 0.1}s" fill="freeze" calcMode="spline" keySplines="0.4 0 0.2 1"/>
          <animate attributeName="y" from="160" to="{y}" dur="0.8s" begin="{i * 0.1}s" fill="freeze" calcMode="spline" keySplines="0.4 0 0.2 1"/>
        </rect>
        <text x="{x + w / 2}%" y="{y - 8}" text-anchor="middle" style="font-family:-apple-system,sans-serif;font-size:13px;font-weight:700;fill:{f["color"]};opacity:0;">
          {val}
          <animate attributeName="opacity" from="0" to="1" dur="0.3s" begin="{i * 0.1 + 0.5}s" fill="freeze"/>
        </text>'''
        labels_svg += f'<text x="{x + w / 2}%" y="178" text-anchor="middle" style="font-family:-apple-system,sans-serif;font-size:8px;font-weight:600;fill:#64748b;text-transform:uppercase;letter-spacing:0.5px;">{f["label"]}</text>'

    risk_pct = _safe_int(insight_data.get("delay_risk_percent") or 0)
    risk_level = insight_data.get("delay_risk") or "low"
    risk_colors = _get_risk_color(risk_level)

    total_findings = sum(_safe_int(insight_data.get(f["key"])) for f in findings)
    donut_segments = ""
    offset = 0
    donut_r = 40
    donut_circ = 2 * 3.14159 * donut_r
    for i, f in enumerate(findings):
        val = _safe_int(insight_data.get(f["key"]))
        if val == 0 or total_findings == 0:
            continue
        pct = val / total_findings
        seg_len = pct * donut_circ
        gap_len = donut_circ - seg_len
        donut_segments += f'''<circle cx="60" cy="60" r="{donut_r}" fill="none" stroke="{f["color"]}" stroke-width="14"
          stroke-dasharray="0 {donut_circ}" stroke-dashoffset="{-offset}" stroke-linecap="round" opacity="0.85">
          <animate attributeName="stroke-dasharray" from="0 {donut_circ}" to="{seg_len} {gap_len}" dur="1s" begin="{i * 0.15}s" fill="freeze" calcMode="spline" keySplines="0.4 0 0.2 1"/>
        </circle>'''
        offset += seg_len

    legend_items = ""
    for f in findings:
        val = _safe_int(insight_data.get(f["key"]))
        if val > 0:
            legend_items += f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0;"><div style="width:8px;height:8px;border-radius:50%;background:{f["color"]};flex-shrink:0;"></div><span style="font-size:11px;color:#94a3b8;">{f["label"]}</span><span style="font-size:11px;font-weight:700;color:#e2e8f0;margin-left:auto;">{val}</span></div>'

    chart_title = "Risikofordeling" if language == "da" else "Risk Distribution"
    bar_title = "Fundoversigt" if language == "da" else "Findings Overview"

    return f'''
<div class="module-card" style="margin:0 0 16px 0;padding:24px;background:#1e293b;border-radius:16px;border:1px solid rgba(148,163,184,0.08);border-left:3px solid #00D6D6;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;">
    <div style="width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;background:rgba(0,214,214,0.12);">
      <span style="color:#00D6D6;">{NOVA_ICONS["chart"]}</span>
    </div>
    <h3 style="font-size:15px;font-weight:700;color:#f1f5f9;margin:0;">{"Visuel Analyse" if language == "da" else "Visual Analytics"}</h3>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
    <div style="background:#162032;border-radius:14px;padding:20px;border:1px solid rgba(148,163,184,0.06);">
      <div style="font-size:11px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:1px;margin-bottom:14px;">{bar_title}</div>
      <svg viewBox="0 0 100 185" preserveAspectRatio="xMidYMid meet" style="width:100%;height:auto;">
        <line x1="0" y1="160" x2="100" y2="160" stroke="rgba(148,163,184,0.1)" stroke-width="0.5"/>
        {bars_svg}
        {labels_svg}
      </svg>
    </div>
    <div style="background:#162032;border-radius:14px;padding:20px;border:1px solid rgba(148,163,184,0.06);">
      <div style="font-size:11px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:1px;margin-bottom:14px;">{chart_title}</div>
      <div style="display:flex;align-items:center;gap:16px;">
        <svg viewBox="0 0 120 120" style="width:100px;height:100px;flex-shrink:0;">
          <circle cx="60" cy="60" r="{donut_r}" fill="none" stroke="rgba(148,163,184,0.06)" stroke-width="14"/>
          {donut_segments}
          <text x="60" y="57" text-anchor="middle" style="font-family:-apple-system,sans-serif;font-size:22px;font-weight:900;fill:#e2e8f0;">{total_findings}</text>
          <text x="60" y="72" text-anchor="middle" style="font-family:-apple-system,sans-serif;font-size:8px;font-weight:600;fill:#64748b;text-transform:uppercase;letter-spacing:1px;">{"FUND" if language == "da" else "FOUND"}</text>
        </svg>
        <div style="flex:1;">{legend_items}</div>
      </div>
    </div>
  </div>
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
    subtitle = "Forudsigende risikoanalyse drevet af GPT-5.2" if language == "da" else "Predictive risk analysis powered by GPT-5.2"

    html_parts = [f'''
<style>
@keyframes novaFadeIn {{ from {{ opacity:0;transform:translateY(12px); }} to {{ opacity:1;transform:translateY(0); }} }}
@keyframes novaPulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.6; }} }}
@keyframes novaSlide {{ from {{ transform:scaleX(0); }} to {{ transform:scaleX(1); }} }}
.nova-report .module-card {{ animation:novaFadeIn 0.5s ease-out backwards; }}
.nova-report .module-card:nth-child(2) {{ animation-delay:0.1s; }}
.nova-report .module-card:nth-child(3) {{ animation-delay:0.15s; }}
.nova-report .module-card:nth-child(4) {{ animation-delay:0.2s; }}
.nova-report .module-card:nth-child(5) {{ animation-delay:0.25s; }}
.nova-report .module-card:nth-child(6) {{ animation-delay:0.3s; }}
.nova-report .module-card:nth-child(7) {{ animation-delay:0.35s; }}
.nova-report .module-card:nth-child(8) {{ animation-delay:0.4s; }}
.nova-report .module-card:nth-child(9) {{ animation-delay:0.45s; }}
.nova-report .module-card:nth-child(10) {{ animation-delay:0.5s; }}
.nova-report .module-card:nth-child(11) {{ animation-delay:0.55s; }}
.nova-report .module-card:hover {{ border-color:rgba(148,163,184,0.2) !important;transform:translateY(-1px);box-shadow:0 8px 24px rgba(0,0,0,0.3); }}
.nova-report table tr:hover {{ background:rgba(148,163,184,0.04) !important; }}
.nova-report ::-webkit-scrollbar {{ height:6px; }}
.nova-report ::-webkit-scrollbar-track {{ background:rgba(0,0,0,0.2);border-radius:6px; }}
.nova-report ::-webkit-scrollbar-thumb {{ background:rgba(148,163,184,0.25);border-radius:6px; }}
</style>
<div class="nova-report" style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:linear-gradient(180deg,#0c1322 0%,#0f172a 8%,#0f172a 100%);border-radius:24px;padding:32px;border:1px solid rgba(148,163,184,0.08);box-shadow:0 4px 48px rgba(0,0,0,0.4);">

  <div style="text-align:center;margin-bottom:28px;padding-bottom:28px;border-bottom:1px solid rgba(148,163,184,0.08);">
    <div style="display:inline-flex;align-items:center;gap:14px;margin-bottom:12px;">
      <div style="width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#00D6D6,#0891b2);box-shadow:0 0 30px rgba(0,214,214,0.25);">
        <span style="color:white;">{NOVA_ICONS["report"]}</span>
      </div>
      <div style="text-align:left;">
        <h2 style="font-size:22px;font-weight:800;color:#f1f5f9;margin:0;letter-spacing:-0.5px;">{report_title}</h2>
        <p style="font-size:11px;color:#475569;margin:2px 0 0 0;letter-spacing:0.5px;">{subtitle}</p>
      </div>
    </div>
    <div style="display:inline-flex;gap:8px;margin-top:8px;">
      <span style="padding:4px 12px;border-radius:20px;font-size:10px;font-weight:700;background:rgba(0,214,214,0.1);color:#00D6D6;border:1px solid rgba(0,214,214,0.15);letter-spacing:0.5px;">NOVA INSIGHT</span>
      <span style="padding:4px 12px;border-radius:20px;font-size:10px;font-weight:700;background:rgba(139,92,246,0.1);color:#a78bfa;border:1px solid rgba(139,92,246,0.15);letter-spacing:0.5px;">GPT-5.2</span>
    </div>
  </div>''']

    if insight_data:
        html_parts.append(_build_hero_metrics(insight_data, language))

    if not insight_data:
        no_data_label = "Analytiske data ikke tilgængelige — diagrammer kan ikke vises." if language == "da" else "Analytical data unavailable — charts cannot be rendered."
        html_parts.append(f'<div style="margin:0 0 16px 0;padding:14px 20px;background:rgba(251,191,36,0.06);border-radius:12px;border:1px solid rgba(251,191,36,0.15);"><p style="margin:0;color:#fbbf24;font-size:12px;font-weight:600;">{no_data_label}</p></div>')

    module_index = 0
    for section_key, section_body in sections:
        if section_key == "_PREAMBLE":
            html_parts.append(f'<div class="module-card" style="margin:0 0 16px 0;padding:18px 22px;background:rgba(0,214,214,0.04);border-radius:14px;border:1px solid rgba(0,214,214,0.1);border-left:3px solid #00D6D6;transition:all 0.2s ease;">')
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

        module_letter = ""
        mod_match = re.match(r"MODULE_([A-G])", config_key)
        if mod_match:
            module_letter = mod_match.group(1)

        module_badge = ""
        if module_letter:
            module_badge = f'<span style="font-size:10px;font-weight:800;color:{color};background:{color}15;padding:3px 8px;border-radius:6px;letter-spacing:0.5px;">{module_letter}</span>'

        module_index += 1

        html_parts.append(f'''
  <div class="module-card" style="margin:0 0 16px 0;padding:22px;background:#1e293b;border-radius:16px;border:1px solid rgba(148,163,184,0.06);border-left:3px solid {color};transition:all 0.2s ease;">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
      <div style="width:34px;height:34px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:{color}12;border:1px solid {color}20;">
        <span style="color:{color};">{icon_svg}</span>
      </div>
      <h3 style="font-size:15px;font-weight:700;color:#f1f5f9;margin:0;flex:1;letter-spacing:-0.2px;">{label}</h3>
      {module_badge}
    </div>
    {content_html}
  </div>''')

    if insight_data:
        html_parts.append(_build_analytics_charts(insight_data, language))

    timestamp_label = "Genereret af Nova Insight AI" if language == "da" else "Generated by Nova Insight AI"
    html_parts.append(f'''
  <div style="margin-top:8px;padding-top:16px;border-top:1px solid rgba(148,163,184,0.06);display:flex;align-items:center;justify-content:center;gap:8px;">
    <div style="width:6px;height:6px;border-radius:50%;background:#00D6D6;box-shadow:0 0 8px rgba(0,214,214,0.4);"></div>
    <span style="font-size:10px;color:#475569;letter-spacing:0.5px;">{timestamp_label}</span>
  </div>
</div>''')

    return "".join(html_parts)
