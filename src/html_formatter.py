"""
Premium Structured HTML Converter — SaaS Section-Grouped Layout
Each task category gets its own card with header + table.
Parses: TABLES → SUMMARY_OF_CHANGES → PROJECT_HEALTH
"""
import re
import json
import html
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import base64


SVG_ICONS = {
    "table": '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" stroke-width="2"/><path d="M3 9h18M3 15h18M9 3v18" stroke="currentColor" stroke-width="2"/></svg>',
    "summary": '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="18" height="18" rx="2" fill="currentColor" opacity="0.15"/><path d="M7 8h10M7 12h10M7 16h6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    "pulse": '<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M22 12h-4l-3 9L9 3l-3 9H2" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "download": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>',
    "added": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#10b981" opacity="0.15"/><path d="M12 8v8M8 12h8" stroke="#10b981" stroke-width="2.5" stroke-linecap="round"/></svg>',
    "removed": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#ef4444" opacity="0.15"/><path d="M8 12h8" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round"/></svg>',
    "moved": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#f59e0b" opacity="0.15"/><path d="M8 12h8M12 8l4 4-4 4" stroke="#f59e0b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "delayed": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#ef4444" opacity="0.15"/><path d="M12 6v6l3 3" stroke="#ef4444" stroke-width="2" stroke-linecap="round"/></svg>',
    "accelerated": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#10b981" opacity="0.15"/><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" transform="scale(0.6) translate(8,8)"/></svg>',
    "critical": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M12 2L2 22h20L12 2z" fill="#f59e0b" opacity="0.15"/><path d="M12 9v4M12 17h.01" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round"/></svg>',
    "risks": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#ef4444" opacity="0.15"/><path d="M12 8v4M12 16h.01" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round"/></svg>',
    "default": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="18" height="18" rx="2" fill="#06b6d4" opacity="0.15"/><path d="M9 9h6M9 12h6M9 15h4" stroke="#06b6d4" stroke-width="2" stroke-linecap="round"/></svg>'
}

CATEGORY_CONFIG = {
    "removed": {"label": "Removed Tasks", "label_da": "Fjernede Opgaver", "color": "#ef4444", "bg": "rgba(239, 68, 68, 0.04)", "border": "rgba(239, 68, 68, 0.12)"},
    "added": {"label": "Added Tasks", "label_da": "Tilføjede Opgaver", "color": "#10b981", "bg": "rgba(16, 185, 129, 0.04)", "border": "rgba(16, 185, 129, 0.12)"},
    "moved": {"label": "Modified / Moved Tasks", "label_da": "Ændrede / Flyttede Opgaver", "color": "#f59e0b", "bg": "rgba(245, 158, 11, 0.04)", "border": "rgba(245, 158, 11, 0.12)"},
    "delayed": {"label": "Delayed Tasks", "label_da": "Forsinkede Opgaver", "color": "#ef4444", "bg": "rgba(239, 68, 68, 0.04)", "border": "rgba(239, 68, 68, 0.12)"},
    "accelerated": {"label": "Accelerated Tasks", "label_da": "Fremskyndede Opgaver", "color": "#10b981", "bg": "rgba(16, 185, 129, 0.04)", "border": "rgba(16, 185, 129, 0.12)"},
    "critical": {"label": "Critical Path", "label_da": "Kritisk Vej", "color": "#f59e0b", "bg": "rgba(245, 158, 11, 0.04)", "border": "rgba(245, 158, 11, 0.12)"},
    "risks": {"label": "Risks", "label_da": "Risici", "color": "#ef4444", "bg": "rgba(239, 68, 68, 0.04)", "border": "rgba(239, 68, 68, 0.12)"},
    "default": {"label": "Other Tasks", "label_da": "Andre Opgaver", "color": "#06b6d4", "bg": "rgba(6, 182, 212, 0.04)", "border": "rgba(6, 182, 212, 0.12)"}
}

CATEGORY_ORDER = ["removed", "added", "delayed", "accelerated", "moved", "critical", "risks", "default"]


def parse_structured_response(markdown: str) -> Dict:
    if not markdown:
        return {"tables_section": "", "summary_section": "", "health_section": "", "health_data": None}

    summary_patterns = [
        r"^##\s*SUMMARY_OF_CHANGES\s*$",
        r"^##\s*OPSUMMERING_AF_ÆNDRINGER\s*$",
        r"^##\s*Summary\s+of\s+Changes",
        r"^##\s*Opsummering\s+af\s+Ændringer"
    ]

    health_patterns = [
        r"^##\s*PROJECT_HEALTH\s*$",
        r"^##\s*PROJEKTSUNDHED\s*$",
        r"^##\s*Project\s+Health",
        r"^##\s*Projektsundhed"
    ]

    summary_start = -1
    health_start = -1

    for pattern in summary_patterns:
        match = re.search(pattern, markdown, re.MULTILINE | re.IGNORECASE)
        if match:
            summary_start = match.start()
            break

    for pattern in health_patterns:
        match = re.search(pattern, markdown, re.MULTILINE | re.IGNORECASE)
        if match:
            health_start = match.start()
            break

    tables_section = ""
    summary_section = ""
    health_section = ""

    if summary_start == -1 and health_start == -1:
        tables_section = markdown
    elif summary_start != -1 and health_start != -1:
        if summary_start < health_start:
            tables_section = markdown[:summary_start].strip()
            summary_section = markdown[summary_start:health_start].strip()
            health_section = markdown[health_start:].strip()
        else:
            tables_section = markdown[:health_start].strip()
            health_section = markdown[health_start:summary_start].strip()
            summary_section = markdown[summary_start:].strip()
    elif summary_start != -1:
        tables_section = markdown[:summary_start].strip()
        summary_section = markdown[summary_start:].strip()
    else:
        tables_section = markdown[:health_start].strip()
        health_section = markdown[health_start:].strip()

    health_data = None
    health_match = re.search(r"<!--HEALTH_DATA:(.*?)-->", health_section, re.DOTALL)
    if health_match:
        try:
            health_data = json.loads(health_match.group(1))
            health_section = re.sub(r"<!--HEALTH_DATA:.*?-->", "", health_section, flags=re.DOTALL).strip()
        except:
            pass

    return {
        "tables_section": tables_section,
        "summary_section": summary_section,
        "health_section": health_section,
        "health_data": health_data
    }


def detect_category(text: str) -> str:
    lower = text.lower()
    if any(k in lower for k in ["removed", "fjern", "not present in new", "dropped", "slettet"]):
        return "removed"
    if any(k in lower for k in ["added", "tilføj", "not present in old", "ny "]):
        return "added"
    if any(k in lower for k in ["delayed", "later", "forsink", "senere"]):
        return "delayed"
    if any(k in lower for k in ["earlier", "accelerat", "tidligere", "fremskynd"]):
        return "accelerated"
    if any(k in lower for k in ["moved", "modified", "ændr", "flytt", "changed"]):
        return "moved"
    if any(k in lower for k in ["critical", "kritisk"]):
        return "critical"
    if any(k in lower for k in ["risk", "risiko"]):
        return "risks"
    return "default"


def _detect_section_category(heading: str) -> str:
    lower = heading.lower()
    if any(k in lower for k in ["removed", "fjern", "slettet", "dropped"]):
        return "removed"
    if any(k in lower for k in ["added", "tilføj", "nye ", "ny ", "new task"]):
        return "added"
    if any(k in lower for k in ["delayed", "forsink", "senere", "later"]):
        return "delayed"
    if any(k in lower for k in ["accelerat", "fremskynd", "earlier", "tidligere"]):
        return "accelerated"
    if any(k in lower for k in ["moved", "modified", "ændr", "flytt", "changed"]):
        return "moved"
    if any(k in lower for k in ["critical", "kritisk"]):
        return "critical"
    if any(k in lower for k in ["risk", "risiko"]):
        return "risks"
    return "default"


def parse_tables_by_section(markdown: str) -> Dict[str, Dict]:
    if not markdown or "|" not in markdown:
        return {}

    sections: Dict[str, Dict] = {}
    lines = markdown.split("\n")
    current_category = None
    current_headers = []

    for line in lines:
        stripped = line.strip()

        heading_match = re.match(r"^#{1,4}\s+(.+)$", stripped)
        if heading_match:
            heading_text = heading_match.group(1).strip()
            cat = _detect_section_category(heading_text)
            if cat not in sections:
                sections[cat] = {"headers": [], "rows": [], "heading": heading_text}
            current_category = cat
            current_headers = []
            continue

        bold_heading = re.match(r"^\*\*([^*]+)\*\*\s*$", stripped)
        if bold_heading and "|" not in stripped:
            heading_text = bold_heading.group(1).strip().rstrip(":")
            cat = _detect_section_category(heading_text)
            if cat not in sections:
                sections[cat] = {"headers": [], "rows": [], "heading": heading_text}
            current_category = cat
            current_headers = []
            continue

        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue

        if re.match(r"^\|[\s\-:|]+\|$", stripped):
            continue

        cells = [c.strip() for c in stripped.strip("|").split("|")]

        if current_category is None:
            cat = detect_category(" ".join(cells))
            if cat not in sections:
                sections[cat] = {"headers": [], "rows": [], "heading": ""}
            current_category = cat

        if not current_headers:
            current_headers = cells
            if current_category in sections and not sections[current_category]["headers"]:
                sections[current_category]["headers"] = cells
            continue

        if current_category in sections:
            sections[current_category]["rows"].append(cells)
        else:
            cat = detect_category(" ".join(cells))
            if cat not in sections:
                sections[cat] = {"headers": current_headers, "rows": [], "heading": ""}
            sections[cat]["rows"].append(cells)

    return sections


def escape_html(text: str) -> str:
    if not text:
        return ""
    return html.escape(str(text))


def get_status_badge(value: str) -> str:
    if not value or value in ["—", "-", "n/a", ""]:
        return '<span style="color:#94a3b8;">—</span>'

    lower = value.lower().strip()
    if any(x in lower for x in ["added", "new", "earlier", "tidligere", "tilføjet"]):
        return f'<span style="display:inline-flex;padding:5px 12px;border-radius:8px;font-size:12px;font-weight:600;background:rgba(16,185,129,0.12);color:#059669;border:1px solid rgba(16,185,129,0.2);">{escape_html(value)}</span>'
    if any(x in lower for x in ["removed", "later", "senere", "delayed", "forsinket", "fjernet"]):
        return f'<span style="display:inline-flex;padding:5px 12px;border-radius:8px;font-size:12px;font-weight:600;background:rgba(239,68,68,0.12);color:#dc2626;border:1px solid rgba(239,68,68,0.2);">{escape_html(value)}</span>'
    if any(x in lower for x in ["moved", "modified", "changed", "ændret", "flyttet"]):
        return f'<span style="display:inline-flex;padding:5px 12px;border-radius:8px;font-size:12px;font-weight:600;background:rgba(245,158,11,0.12);color:#d97706;border:1px solid rgba(245,158,11,0.2);">{escape_html(value)}</span>'
    return f'<span style="display:inline-flex;padding:5px 12px;border-radius:8px;font-size:12px;font-weight:600;background:rgba(100,116,139,0.1);color:#475569;border:1px solid rgba(100,116,139,0.15);">{escape_html(value)}</span>'


def _render_cell(cell: str, header_name: str, is_first: bool, accent_color: str) -> str:
    if is_first:
        return f'<span style="color:#1e293b;font-weight:600;">{escape_html(cell or "—")}</span>'

    h_lower = header_name.lower()

    if any(x in h_lower for x in ["status", "difference", "forskel", "change", "ændring"]):
        return get_status_badge(cell)

    if any(x in h_lower for x in ["week", "uge", "id"]):
        if not cell or cell in ["—", "-"]:
            return '<span style="color:#94a3b8;">—</span>'
        return f'<span style="display:inline-block;padding:4px 10px;border-radius:6px;font-weight:600;background:linear-gradient(135deg,#e0f7f7,#d1fae5);color:#0e7490;font-size:13px;border:1px solid rgba(6,182,212,0.2);">{escape_html(cell)}</span>'

    if any(x in h_lower for x in ["slutdato", "startdato", "date", "dato"]):
        if not cell or cell in ["—", "-"]:
            return '<span style="color:#94a3b8;">—</span>'
        return f'<span style="color:#334155;font-weight:500;font-size:13px;">{escape_html(cell)}</span>'

    if any(x in h_lower for x in ["varighed", "duration"]):
        if not cell or cell in ["—", "-"]:
            return '<span style="color:#94a3b8;">—</span>'
        return f'<span style="display:inline-block;padding:3px 8px;border-radius:6px;background:rgba(100,116,139,0.08);color:#475569;font-size:13px;font-weight:500;">{escape_html(cell)}</span>'

    return f'<span style="color:#475569;font-size:14px;line-height:1.5;">{escape_html(cell or "—")}</span>'


def _build_section_card(category: str, headers: List[str], rows: List[List[str]], language: str, table_id_suffix: str) -> str:
    if not rows:
        return ""

    config = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG["default"])
    label = config["label_da"] if language == "da" else config["label"]
    color = config["color"]
    bg = config["bg"]
    border_color = config["border"]
    icon = SVG_ICONS.get(category, SVG_ICONS["default"])
    count = len(rows)

    parts = [f'''
<div class="category-section" style="margin:0 0 24px 0;border-radius:16px;overflow:hidden;border:1px solid {border_color};background:#ffffff;box-shadow:0 2px 12px rgba(0,0,0,0.04);">
  <div style="display:flex;align-items:center;gap:10px;padding:16px 20px;background:{bg};border-bottom:2px solid {color}25;">
    <span style="color:{color};flex-shrink:0;">{icon}</span>
    <span style="font-size:15px;font-weight:700;color:{color};text-transform:uppercase;letter-spacing:0.8px;">{label}</span>
    <span style="padding:3px 10px;border-radius:20px;font-size:12px;font-weight:700;background:{color}18;color:{color};min-width:22px;text-align:center;">{count}</span>
  </div>
  <div style="overflow-x:auto;">
    <table style="width:100%;min-width:600px;border-collapse:separate;border-spacing:0;">
      <thead>
        <tr style="background:linear-gradient(135deg,#0f172a,#1e293b);">''']

    for idx, header in enumerate(headers):
        is_last = idx == len(headers) - 1
        br = "" if is_last else "border-right:1px solid rgba(255,255,255,0.08);"
        parts.append(f'''
          <th style="padding:14px 16px;text-align:left;font-size:11px;font-weight:700;color:rgba(255,255,255,0.9);text-transform:uppercase;letter-spacing:1px;{br}white-space:nowrap;">{escape_html(header)}</th>''')

    parts.append('''
        </tr>
      </thead>
      <tbody>''')

    for row_idx, row in enumerate(rows):
        row_bg = "#ffffff" if row_idx % 2 == 0 else "#f8fafc"
        parts.append(f'''
        <tr style="background:{row_bg};transition:background 0.15s ease;">''')

        for cell_idx, cell in enumerate(row):
            is_last = cell_idx == len(row) - 1
            br = "" if is_last else "border-right:1px solid #f1f5f9;"
            header_name = headers[cell_idx] if cell_idx < len(headers) else ""
            content = _render_cell(cell, header_name, cell_idx == 0, color)
            parts.append(f'''
          <td style="padding:14px 16px;font-size:14px;{br}border-bottom:1px solid #f1f5f9;vertical-align:middle;">{content}</td>''')

        parts.append('''
        </tr>''')

    parts.append('''
      </tbody>
    </table>
  </div>
</div>''')

    return "".join(parts)


def _build_empty_category_note(category: str, language: str) -> str:
    config = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG["default"])
    label = config["label_da"] if language == "da" else config["label"]
    color = config["color"]
    icon = SVG_ICONS.get(category, SVG_ICONS["default"])
    no_text = "Ingen" if language == "da" else "No"
    found_text = "fundet i de hentede data" if language == "da" else "found in the retrieved data"

    return f'''
<div style="display:flex;align-items:center;gap:10px;padding:14px 20px;margin:0 0 12px 0;border-radius:12px;background:rgba(248,250,252,0.8);border:1px solid #e2e8f0;">
  <span style="color:{color};opacity:0.5;">{icon}</span>
  <span style="font-size:14px;color:#94a3b8;font-weight:500;">{no_text} {label.lower()} {found_text}</span>
</div>'''


def generate_table_html(tables_section: str, language: str = "en") -> str:
    sections = parse_tables_by_section(tables_section)

    total_tasks = sum(len(s["rows"]) for s in sections.values())
    if total_tasks == 0:
        return ""

    date_str = datetime.now().strftime("%Y-%m-%d")
    table_id = f"tbl_{datetime.now().strftime('%H%M%S')}"

    all_rows_for_csv = []
    csv_headers = []
    for cat in CATEGORY_ORDER:
        if cat in sections and sections[cat]["rows"]:
            if not csv_headers and sections[cat]["headers"]:
                csv_headers = sections[cat]["headers"]
            all_rows_for_csv.extend(sections[cat]["rows"])
    csv_data = base64.b64encode(json.dumps([csv_headers] + all_rows_for_csv).encode()).decode()

    download_js = f"(function(){{try{{var d=document.getElementById('csvData_{table_id}');var f=document.getElementById('csvFilename_{table_id}');if(!d||!f)return;var j=decodeURIComponent(escape(atob(d.textContent)));var dt=JSON.parse(j);var fn=f.textContent;var csv=dt.map(function(r){{return r.map(function(c){{var v=String(c||'');if(v.search(/[,\\\"\\\\n]/)!==-1)v='\"'+v.replace(/\"/g,'\"\"')+'\"';return v;}}).join(',')}}).join('\\n');var b=new Blob(['\\uFEFF'+csv],{{type:'text/csv;charset=utf-8;'}});var u=URL.createObjectURL(b);var l=document.createElement('a');l.href=u;l.download=fn;document.body.appendChild(l);l.click();document.body.removeChild(l);URL.revokeObjectURL(u);}}catch(e){{alert('CSV Error: '+e.message);}}}})()".replace("'", "&#39;")

    parts = [f'''
<div class="comparison-results" style="margin-bottom:32px;">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;flex-wrap:wrap;gap:16px;">
    <div style="display:flex;align-items:center;gap:14px;">
      <div style="width:48px;height:48px;border-radius:14px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#06b6d4,#0891b2);box-shadow:0 6px 20px rgba(6,182,212,0.25);">
        <span style="color:white;">{SVG_ICONS["table"]}</span>
      </div>
      <div>
        <h3 style="font-size:22px;font-weight:800;color:#0f172a;margin:0;">{"Sammenligningsresultater" if language == "da" else "Comparison Results"}</h3>
        <p style="font-size:13px;color:#64748b;margin:4px 0 0 0;">{total_tasks} {"opgaver analyseret" if language == "da" else "tasks analyzed"}</p>
      </div>
    </div>
    <button type="button" onclick="{download_js}"
            style="display:inline-flex;align-items:center;gap:8px;padding:12px 24px;border-radius:12px;font-weight:600;font-size:13px;color:white;background:linear-gradient(135deg,#00D6D6,#00B8B8);border:none;cursor:pointer;box-shadow:0 4px 16px rgba(0,214,214,0.3);transition:all 0.2s ease;">
      {SVG_ICONS["download"]}
      <span>{"Eksporter CSV" if language == "da" else "Export CSV"}</span>
    </button>
  </div>

  <div id="csvData_{table_id}" style="display:none;">{csv_data}</div>
  <div id="csvFilename_{table_id}" style="display:none;">comparison_results_{date_str}.csv</div>

  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:10px;margin-bottom:24px;">''']

    for cat in CATEGORY_ORDER:
        if cat not in sections or not sections[cat]["rows"]:
            continue
        config = CATEGORY_CONFIG[cat]
        color = config["color"]
        label_short = (config["label_da"] if language == "da" else config["label"]).split("/")[0].replace("Tasks", "").replace("Opgaver", "").strip()
        count = len(sections[cat]["rows"])
        parts.append(f'''
    <div style="text-align:center;padding:14px 8px;background:linear-gradient(135deg,{color}0a,{color}04);border-radius:12px;border:1px solid {color}18;">
      <div style="font-size:24px;font-weight:800;color:{color};">{count}</div>
      <div style="font-size:10px;color:#64748b;text-transform:uppercase;margin-top:3px;font-weight:600;letter-spacing:0.5px;">{label_short}</div>
    </div>''')

    parts.append('''
  </div>''')

    for cat in CATEGORY_ORDER:
        if cat not in sections:
            continue
        sec = sections[cat]
        if sec["rows"]:
            parts.append(_build_section_card(cat, sec["headers"], sec["rows"], language, table_id))
        else:
            parts.append(_build_empty_category_note(cat, language))

    parts.append('''
</div>''')

    return "".join(parts)


def generate_summary_html(summary_content: str, language: str = "en") -> str:
    if not summary_content or not summary_content.strip():
        return ""

    lines = summary_content.split("\n")
    processed = []
    list_items = []

    def flush_list():
        nonlocal list_items
        if list_items:
            processed.append('<ul style="margin:12px 0;padding-left:0;list-style:none;">')
            for item in list_items:
                processed.append(f'<li style="margin:10px 0;line-height:1.6;padding-left:24px;position:relative;"><span style="position:absolute;left:0;color:#8b5cf6;font-size:18px;">•</span>{item}</li>')
            processed.append('</ul>')
            list_items = []

    for line in lines:
        line = line.strip()
        if not line or line in ["---", "***"]:
            flush_list()
            continue

        if re.match(r"^##\s*(SUMMARY_OF_CHANGES|OPSUMMERING_AF_ÆNDRINGER)", line, re.IGNORECASE):
            flush_list()
            header_text = "Opsummering af Ændringer" if language == "da" else "Summary of Changes"
            processed.append(f'''
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:20px;">
          <div style="width:48px;height:48px;border-radius:14px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#8b5cf6,#7c3aed);box-shadow:0 6px 20px rgba(139,92,246,0.25);">
            <span style="color:white;">{SVG_ICONS["summary"]}</span>
          </div>
          <h2 style="font-size:22px;font-weight:800;color:#0f172a;margin:0;">{header_text}</h2>
        </div>''')
            continue

        bold_match = re.match(r"^\*\*([^*]+):\*\*$", line) or re.match(r"^\*\*([^*]+)\*\*$", line)
        if bold_match:
            flush_list()
            header_text = bold_match.group(1).rstrip(":")
            processed.append(f'<h3 style="font-size:14px;font-weight:700;color:#7c3aed;margin:20px 0 10px 0;padding-bottom:8px;border-bottom:2px solid rgba(139,92,246,0.12);text-transform:uppercase;letter-spacing:0.5px;">{escape_html(header_text)}</h3>')
            continue

        if line.startswith("• ") or line.startswith("* ") or line.startswith("- "):
            item_text = line[2:]
            item_text = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color:#6d28d9;font-weight:600;">\1</strong>', item_text)
            list_items.append(item_text)
            continue

        flush_list()
        text = escape_html(line)
        text = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color:#6d28d9;font-weight:600;">\1</strong>', text)
        processed.append(f'<p style="margin:10px 0;color:#334155;line-height:1.7;font-size:14px;">{text}</p>')

    flush_list()

    return f'''
<div class="summary-section" style="margin:24px 0;padding:24px;background:linear-gradient(135deg,rgba(139,92,246,0.04),rgba(124,58,237,0.02));border-radius:16px;border:1px solid rgba(139,92,246,0.1);">
  {"".join(processed)}
</div>'''


def generate_health_html(health_content: str, health_data: Optional[Dict], language: str = "en") -> str:
    if not health_content or not health_content.strip():
        return ""

    status = "stable"
    if health_data and health_data.get("status"):
        status = health_data["status"]
    elif "high risk" in health_content.lower() or "høj risiko" in health_content.lower():
        status = "high_risk"
    elif "attention" in health_content.lower() or "opmærksomhed" in health_content.lower():
        status = "attention"

    status_config = {
        "stable": {"color": "#10b981", "bg": "rgba(16,185,129,0.06)", "border": "rgba(16,185,129,0.15)", "label_en": "Stable", "label_da": "Stabil"},
        "attention": {"color": "#f59e0b", "bg": "rgba(245,158,11,0.06)", "border": "rgba(245,158,11,0.15)", "label_en": "Attention Needed", "label_da": "Kræver Opmærksomhed"},
        "high_risk": {"color": "#ef4444", "bg": "rgba(239,68,68,0.06)", "border": "rgba(239,68,68,0.15)", "label_en": "High Risk", "label_da": "Høj Risiko"}
    }

    config = status_config.get(status, status_config["stable"])
    color = config["color"]
    bg = config["bg"]
    border = config["border"]
    status_label = config["label_da"] if language == "da" else config["label_en"]

    lines = health_content.split("\n")
    processed = []
    list_items = []

    def flush_list():
        nonlocal list_items
        if list_items:
            processed.append('<ul style="margin:12px 0;padding-left:0;list-style:none;">')
            for item in list_items:
                processed.append(f'<li style="margin:8px 0;line-height:1.6;padding-left:24px;position:relative;"><span style="position:absolute;left:0;color:{color};font-size:18px;">•</span>{item}</li>')
            processed.append('</ul>')
            list_items = []

    for line in lines:
        line = line.strip()
        if not line or line == "---":
            flush_list()
            continue

        if re.match(r"^##\s*(PROJECT_HEALTH|PROJEKTSUNDHED)", line, re.IGNORECASE):
            flush_list()
            header_text = "Projektsundhed" if language == "da" else "Project Health"
            processed.append(f'''
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:16px;">
          <div style="display:flex;align-items:center;gap:14px;">
            <div style="width:48px;height:48px;border-radius:14px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,{color},{color}cc);box-shadow:0 6px 20px {color}30;">
              <span style="color:white;">{SVG_ICONS["pulse"]}</span>
            </div>
            <h2 style="font-size:22px;font-weight:800;color:#0f172a;margin:0;">{header_text}</h2>
          </div>
          <div style="display:flex;align-items:center;gap:10px;padding:10px 20px;border-radius:50px;background:{bg};border:2px solid {border};">
            <div style="width:10px;height:10px;border-radius:50%;background:{color};box-shadow:0 0 8px {color}80;"></div>
            <span style="font-size:14px;font-weight:700;color:{color};">{status_label}</span>
          </div>
        </div>''')
            continue

        if re.match(r"^\*\*Status:\*\*", line, re.IGNORECASE):
            continue

        bold_match = re.match(r"^\*\*([^*]+):\*\*$", line) or re.match(r"^\*\*([^*]+)\*\*$", line)
        if bold_match:
            flush_list()
            header_text = bold_match.group(1).rstrip(":")
            processed.append(f'<h3 style="font-size:14px;font-weight:700;color:{color};margin:20px 0 10px 0;padding-bottom:8px;border-bottom:2px solid {color}15;text-transform:uppercase;letter-spacing:0.5px;">{escape_html(header_text)}</h3>')
            continue

        if line.startswith("• ") or line.startswith("* ") or line.startswith("- "):
            item_text = line[2:]
            item_text = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="font-weight:600;">\1</strong>', item_text)
            list_items.append(item_text)
            continue

        flush_list()
        text = escape_html(line)
        text = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="font-weight:600;">\1</strong>', text)
        processed.append(f'<p style="margin:10px 0;color:#334155;line-height:1.7;font-size:14px;">{text}</p>')

    flush_list()

    metrics_html = ""
    if health_data:
        metrics = []
        metric_items = [
            ("delayed_count", "#ef4444", "Forsinket" if language == "da" else "Delayed"),
            ("accelerated_count", "#10b981", "Fremskyndet" if language == "da" else "Accelerated"),
            ("added_count", "#06b6d4", "Tilføjet" if language == "da" else "Added"),
            ("removed_count", "#ef4444", "Fjernet" if language == "da" else "Removed"),
        ]
        for key, m_color, m_label in metric_items:
            val = health_data.get(key)
            if val is not None:
                metrics.append(f'<div style="text-align:center;padding:14px 10px;background:linear-gradient(135deg,{m_color}0a,{m_color}04);border-radius:12px;border:1px solid {m_color}15;"><div style="font-size:24px;font-weight:800;color:{m_color};">{val}</div><div style="font-size:10px;color:#64748b;text-transform:uppercase;margin-top:3px;font-weight:600;">{m_label}</div></div>')

        if metrics:
            metrics_html = f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:10px;margin-top:20px;padding-top:20px;border-top:2px solid {color}10;">{"".join(metrics)}</div>'

    return f'''
<div class="health-section" style="margin:24px 0;padding:24px;background:linear-gradient(135deg,{bg},rgba(255,255,255,0.95));border-radius:16px;border:1px solid {border};">
  {"".join(processed)}
  {metrics_html}
</div>'''


def format_response_as_html(markdown: str, language: str = "en") -> str:
    try:
        return _format_response_internal(markdown, language)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"HTML formatter error: {e}")
        safe_text = escape_html(markdown)
        return f'<div style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;padding:24px;"><div style="white-space:pre-wrap;color:#334155;line-height:1.7;font-size:14px;">{safe_text}</div></div>'


def _format_response_internal(markdown: str, language: str) -> str:
    parsed = parse_structured_response(markdown)

    table_html = generate_table_html(parsed["tables_section"], language)
    summary_html = generate_summary_html(parsed["summary_section"], language)
    health_html = generate_health_html(parsed["health_section"], parsed["health_data"], language)

    styles = '''
<style>
.comparison-results .category-section table tr:hover { background: rgba(0,214,214,0.04) !important; }
.comparison-results button:hover { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(0,214,214,0.4) !important; }
.comparison-results table::-webkit-scrollbar { height: 8px; }
.comparison-results table::-webkit-scrollbar-track { background: rgba(0,0,0,0.03); border-radius: 8px; }
.comparison-results table::-webkit-scrollbar-thumb { background: linear-gradient(135deg,#00D6D6,#00B8B8); border-radius: 8px; }
</style>'''

    return f'''
{styles}
<div class="agent-response" style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  {table_html}
  {summary_html}
  {health_html}
</div>'''
