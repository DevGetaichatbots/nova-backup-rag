import re
import json
import html
from typing import Dict, List, Optional, Tuple


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


def _get_severity_color(days_overdue: int) -> dict:
    if days_overdue >= 120:
        return {"color": "#dc2626", "bg": "#fef2f2", "border": "#fecaca", "label": "Critical"}
    if days_overdue >= 60:
        return {"color": "#ea580c", "bg": "#fff7ed", "border": "#fed7aa", "label": "High"}
    if days_overdue >= 30:
        return {"color": "#d97706", "bg": "#fffbeb", "border": "#fde68a", "label": "Medium"}
    return {"color": "#0891b2", "bg": "#ecfeff", "border": "#a5f3fc", "label": "Low"}


PRIORITY_STYLES = {
    "CRITICAL NOW": {"color": "#dc2626", "bg": "#fef2f2", "border": "#fecaca"},
    "KRITISK NU": {"color": "#dc2626", "bg": "#fef2f2", "border": "#fecaca"},
    "IMPORTANT NEXT": {"color": "#d97706", "bg": "#fffbeb", "border": "#fde68a"},
    "VIGTIG NÆSTE": {"color": "#d97706", "bg": "#fffbeb", "border": "#fde68a"},
    "MONITOR": {"color": "#0891b2", "bg": "#ecfeff", "border": "#a5f3fc"},
    "OVERVÅG": {"color": "#0891b2", "bg": "#ecfeff", "border": "#a5f3fc"},
}

TASK_TYPE_STYLES = {
    "Coordination": {"color": "#7c3aed", "bg": "#f5f3ff"},
    "Koordinering": {"color": "#7c3aed", "bg": "#f5f3ff"},
    "Design": {"color": "#2563eb", "bg": "#eff6ff"},
    "Bygherre": {"color": "#c026d3", "bg": "#fdf4ff"},
    "Production": {"color": "#059669", "bg": "#ecfdf5"},
    "Produktion": {"color": "#059669", "bg": "#ecfdf5"},
    "Procurement": {"color": "#d97706", "bg": "#fffbeb"},
    "Indkøb": {"color": "#d97706", "bg": "#fffbeb"},
    "Milestone": {"color": "#64748b", "bg": "#f8fafc"},
    "Milepæl": {"color": "#64748b", "bg": "#f8fafc"},
}


def _render_delayed_table(markdown_lines: List[str]) -> str:
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

    valid_rows = []
    for row in rows:
        if row and row[0].strip().upper() in ("N/A", "-", ""):
            continue
        if any("only" in c.lower() and "met the criteria" in c.lower() for c in row):
            continue
        valid_rows.append(row)
    rows = valid_rows

    days_col_idx = -1
    priority_col_idx = -1
    type_col_idx = -1
    for i, h in enumerate(headers):
        h_lower = h.lower()
        if "overdue" in h_lower or "forsinket" in h_lower:
            days_col_idx = i
        if "priority" in h_lower or "prioritet" in h_lower:
            priority_col_idx = i
        if "task type" in h_lower or "opgavetype" in h_lower:
            type_col_idx = i

    header_html = ""
    for i, h in enumerate(headers):
        align = "right" if i == days_col_idx else ("center" if i in (priority_col_idx, type_col_idx) else "left")
        header_html += f'<th style="padding:12px 14px;text-align:{align};font-size:11px;font-weight:700;color:#4a5568;text-transform:uppercase;letter-spacing:0.8px;white-space:nowrap;border-bottom:2px solid #e2e8f0;background:#f7fafc;">{_escape(h)}</th>'

    rows_html = []
    for idx, row in enumerate(rows):
        bg = "#f7fafc" if idx % 2 == 0 else "#ffffff"

        days_val = 0
        if days_col_idx >= 0 and days_col_idx < len(row):
            days_match = re.search(r"(\d+)", row[days_col_idx])
            if days_match:
                days_val = int(days_match.group(1))

        severity = _get_severity_color(days_val)

        cells_html = ""
        for ci, cell in enumerate(row):
            if ci == 0:
                content = f'<span style="font-weight:700;color:#1a202c;font-size:13px;font-family:\'SF Mono\',SFMono-Regular,Menlo,monospace;">{_escape(cell)}</span>'
            elif ci == days_col_idx:
                content = f'<span style="display:inline-flex;align-items:center;gap:6px;"><span style="display:inline-block;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:700;color:{severity["color"]};background:{severity["bg"]};border:1px solid {severity["border"]};">{_escape(cell)}</span></span>'
            elif ci == priority_col_idx:
                p_style = PRIORITY_STYLES.get(cell.strip(), {"color": "#64748b", "bg": "#f8fafc", "border": "#e2e8f0"})
                content = f'<span style="display:inline-block;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700;color:{p_style["color"]};background:{p_style["bg"]};border:1px solid {p_style["border"]};white-space:nowrap;">{_escape(cell)}</span>'
            elif ci == type_col_idx:
                t_style = TASK_TYPE_STYLES.get(cell.strip(), {"color": "#64748b", "bg": "#f8fafc"})
                content = f'<span style="display:inline-block;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:600;color:{t_style["color"]};background:{t_style["bg"]};white-space:nowrap;">{_escape(cell)}</span>'
            elif "0%" in cell:
                content = f'<span style="color:#dc2626;font-weight:600;font-size:13px;">{_escape(cell)}</span>'
            else:
                content = f'<span style="color:#4a5568;font-size:13px;">{_escape(cell)}</span>'

            align = "right" if ci == days_col_idx else ("center" if ci in (priority_col_idx, type_col_idx) else "left")
            cells_html += f'<td style="padding:11px 14px;border-bottom:1px solid #edf2f7;vertical-align:middle;text-align:{align};">{content}</td>'

        rows_html.append(f'<tr style="background:{bg};transition:background 0.15s;" onmouseover="this.style.background=\'#edf2f7\'" onmouseout="this.style.background=\'{bg}\'">{cells_html}</tr>')

    return f'''<div style="overflow-x:auto;border-radius:12px;margin:16px 0;background:#ffffff;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
<table style="width:100%;min-width:800px;border-collapse:collapse;">
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
            parts.append(_render_delayed_table(table_lines))
            table_lines = []

    def flush_list():
        nonlocal list_items
        if list_items:
            items = "".join(
                f'<li style="margin:8px 0;line-height:1.7;padding-left:20px;position:relative;font-size:14px;color:#4a5568;"><span style="position:absolute;left:0;color:{accent_color};font-weight:bold;font-size:16px;line-height:1.35;">›</span>{item}</li>'
                for item in list_items
            )
            parts.append(f'<ul style="margin:12px 0;padding-left:0;list-style:none;">{items}</ul>')
            list_items = []

    in_code_block = False
    code_lines = []

    def flush_code():
        nonlocal code_lines, in_code_block
        if code_lines:
            code_text = _escape("\n".join(code_lines))
            parts.append(f'<pre style="margin:12px 0;padding:14px 16px;background:#f7fafc;border-radius:8px;border:1px solid #e2e8f0;overflow-x:auto;"><code style="font-family:\'SF Mono\',SFMono-Regular,Menlo,Consolas,monospace;font-size:12px;color:#4a5568;line-height:1.6;">{code_text}</code></pre>')
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

        root_cause_match = re.match(r"^\*\*(ROOT CAUSE|GRUNDÅRSAG):\s*(.+?)\*\*$", stripped)
        if root_cause_match:
            flush_list()
            label = root_cause_match.group(1)
            detail = _escape(root_cause_match.group(2))
            parts.append(f'''<div style="margin:18px 0 10px;padding:14px 18px;background:#fef2f2;border-radius:10px;border:1px solid #fecaca;border-left:4px solid #dc2626;">
<p style="margin:0;color:#991b1b;font-size:14px;font-weight:700;"><span style="margin-right:8px;">🔴</span>{_escape(label)}: {detail}</p></div>''')
            continue

        downstream_match = re.match(r"^\*\*(Downstream consequences|Afledte konsekvenser).*?\*\*", stripped)
        if downstream_match:
            flush_list()
            text = _escape(downstream_match.group(0).strip("*"))
            parts.append(f'<h4 style="margin:22px 0 10px;color:#64748b;font-size:13px;font-weight:700;padding:10px 16px;background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;">{text}</h4>')
            continue

        if stripped.startswith("- ") or stripped.startswith("• ") or stripped.startswith("* "):
            item_raw = stripped[2:]
            item_safe = _escape(item_raw)
            item_safe = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color:#1a202c;font-weight:600;">\1</strong>', item_safe)

            if re.search(r'\bID\s+N/?A\b', item_raw, re.IGNORECASE):
                continue

            for pkey, pstyle in PRIORITY_STYLES.items():
                if pkey in item_safe:
                    item_safe = item_safe.replace(_escape(pkey), f'<span style="display:inline-block;padding:1px 8px;border-radius:6px;font-size:11px;font-weight:700;color:{pstyle["color"]};background:{pstyle["bg"]};border:1px solid {pstyle["border"]};">{_escape(pkey)}</span>')
                    break

            resource_keywords = ["manpower", "management attention", "site labour", "labour", "escalation", "client", "coordination bottleneck", "design dependency", "production delay",
                                 "mandskab", "ledelsens opmærksomhed", "arbejdskraft", "eskalering", "koordineringsflaskehals", "designafhængighed"]
            for kw in resource_keywords:
                if kw.lower() in item_safe.lower():
                    idx_kw = item_safe.lower().index(kw.lower())
                    original_kw = item_safe[idx_kw:idx_kw+len(kw)]
                    item_safe = item_safe.replace(original_kw, f'<strong style="color:#0d9488;">{original_kw}</strong>', 1)
                    break

            list_items.append(item_safe)
            continue

        if re.match(r"^\d+\.\s+", stripped):
            num_match = re.match(r"^(\d+)\.\s+(.*)", stripped)
            if num_match:
                item_raw = num_match.group(2)
                if re.search(r'\bID\s+N/?A\b', item_raw, re.IGNORECASE):
                    continue
                num = num_match.group(1)
                item_safe = _escape(item_raw)
                item_safe = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color:#1a202c;font-weight:600;">\1</strong>', item_safe)
                list_items.append(f'<span style="display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:#0d9488;color:white;font-size:12px;font-weight:700;margin-right:10px;flex-shrink:0;">{num}</span>{item_safe}')
                continue

        flush_list()

        safe = _escape(stripped)

        bold_line = re.match(r"^\*\*(.+?)\*\*$", stripped)
        if bold_line:
            text = _escape(bold_line.group(1))
            text_lower = text.lower()
            if any(k in text_lower for k in ["total", "antal", "delayed activities", "forsinkede aktiviteter"]):
                parts.append(f'<div style="margin:18px 0 12px;padding:14px 18px;background:linear-gradient(135deg,#f0fdfa,#ecfeff);border-radius:10px;border:1px solid #99f6e4;"><p style="margin:0;color:#0f766e;font-size:15px;font-weight:700;">{text}</p></div>')
                continue
            if any(k in text_lower for k in ["summary", "oversigt", "most critical", "mest kritiske", "assessment", "vurdering"]):
                parts.append(f'<h4 style="margin:22px 0 10px;color:#1a202c;font-size:14px;font-weight:700;padding-bottom:8px;border-bottom:1px solid #e2e8f0;">{text}</h4>')
                continue
            if any(k in text_lower for k in ["reference", "referencedato", "filtering", "filtrering"]):
                parts.append(f'<p style="margin:8px 0;color:#4a5568;font-size:13px;font-weight:600;background:#f7fafc;padding:8px 14px;border-radius:8px;border-left:3px solid {accent_color};">{text}</p>')
                continue

        text = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color:#1a202c;font-weight:600;">\1</strong>', safe)
        parts.append(f'<p style="margin:8px 0;color:#4a5568;line-height:1.8;font-size:14px;">{text}</p>')

    flush_code()
    flush_table()
    flush_list()
    return "".join(parts)


def _safe_int(val) -> int:
    try:
        return int(round(float(val)))
    except (ValueError, TypeError):
        return 0


def _build_hero_section(insight_data: Dict, language: str) -> str:
    if not insight_data:
        return ""

    delayed_count = _safe_int(insight_data.get("delayed_count") or 0)
    total_activities = _safe_int(insight_data.get("total_activities") or 0)
    most_overdue = _safe_int(insight_data.get("most_overdue_days") or 0)
    areas_affected = _safe_int(insight_data.get("areas_affected") or 0)
    critical_count = _safe_int(insight_data.get("critical_count") or 0)
    important_count = _safe_int(insight_data.get("important_count") or 0)
    monitor_count = _safe_int(insight_data.get("monitor_count") or 0)
    root_cause_count = _safe_int(insight_data.get("root_cause_count") or 0)
    ref_date = _escape(str(insight_data.get("reference_date") or ""))
    primary_risk = _escape(str(insight_data.get("primary_risk") or ""))

    if critical_count == 0 and delayed_count == 0:
        status_color = "#0d9488"
        status_bg = "#f0fdfa"
        status_border = "#99f6e4"
        status_label = "Ingen forsinkelser" if language == "da" else "No Delays"
    elif critical_count <= 3:
        status_color = "#d97706"
        status_bg = "#fffbeb"
        status_border = "#fde68a"
        status_label = "Moderat" if language == "da" else "Moderate"
    elif critical_count <= 8:
        status_color = "#ea580c"
        status_bg = "#fff7ed"
        status_border = "#fed7aa"
        status_label = "Alvorlig" if language == "da" else "Serious"
    else:
        status_color = "#dc2626"
        status_bg = "#fef2f2"
        status_border = "#fecaca"
        status_label = "Kritisk" if language == "da" else "Critical"

    pct = min(round((delayed_count / max(total_activities, 1)) * 100), 100) if total_activities > 0 else 0
    bar_width = min(pct, 100)
    bar_color = "#0d9488" if pct < 15 else ("#d97706" if pct < 30 else ("#ea580c" if pct < 50 else "#dc2626"))

    priority_breakdown = ""
    if critical_count > 0 or important_count > 0 or monitor_count > 0:
        crit_label = "Kritisk" if language == "da" else "Critical"
        imp_label = "Vigtig" if language == "da" else "Important"
        mon_label = "Overvåg" if language == "da" else "Monitor"
        priority_breakdown = f'''
    <div style="display:flex;gap:12px;margin-top:12px;flex-wrap:wrap;">
      <div style="display:flex;align-items:center;gap:6px;">
        <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#dc2626;"></span>
        <span style="font-size:12px;color:#4a5568;font-weight:600;">{critical_count} {crit_label}</span>
      </div>
      <div style="display:flex;align-items:center;gap:6px;">
        <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#d97706;"></span>
        <span style="font-size:12px;color:#4a5568;font-weight:600;">{important_count} {imp_label}</span>
      </div>
      <div style="display:flex;align-items:center;gap:6px;">
        <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#0891b2;"></span>
        <span style="font-size:12px;color:#4a5568;font-weight:600;">{monitor_count} {mon_label}</span>
      </div>
    </div>'''

    return f'''
<div style="margin:0 0 20px 0;background:#ffffff;border-radius:16px;border:1px solid #e2e8f0;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
  <div style="background:linear-gradient(135deg,#f0fdfa,#ecfeff);padding:24px 28px 20px;border-bottom:1px solid #e2e8f0;">
    <div style="display:flex;align-items:center;gap:24px;flex-wrap:wrap;">

      <div style="text-align:center;flex-shrink:0;min-width:100px;">
        <div style="font-size:48px;font-weight:900;color:{status_color};line-height:1;">
          {delayed_count}
        </div>
        <div style="font-size:10px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:1.5px;margin-top:4px;">
          {"FORSINKEDE" if language == "da" else "DELAYED"}
        </div>
      </div>

      <div style="flex:1;min-width:200px;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
          <span style="display:inline-block;padding:4px 14px;border-radius:20px;font-size:11px;font-weight:700;color:{status_color};background:{status_bg};border:1px solid {status_border};">{status_label}</span>
        </div>
        <div style="margin-bottom:8px;">
          <div style="display:flex;justify-content:space-between;margin-bottom:5px;">
            <span style="font-size:11px;color:#64748b;font-weight:600;">{"Forsinkede af total" if language == "da" else "Delayed of total"}</span>
            <span style="font-size:12px;color:#1a202c;font-weight:700;">{delayed_count}/{total_activities} ({pct}%)</span>
          </div>
          <div style="height:8px;background:#e2e8f0;border-radius:4px;overflow:hidden;">
            <div style="height:100%;width:{bar_width}%;background:{bar_color};border-radius:4px;"></div>
          </div>
        </div>
        {priority_breakdown}

        <div style="display:flex;gap:20px;flex-wrap:wrap;margin-top:14px;">
          <div>
            <div style="font-size:10px;color:#64748b;text-transform:uppercase;font-weight:600;letter-spacing:0.8px;">{"Referencedato" if language == "da" else "Ref. Date"}</div>
            <div style="font-size:14px;font-weight:700;color:#1a202c;margin-top:2px;">{ref_date}</div>
          </div>
          <div>
            <div style="font-size:10px;color:#64748b;text-transform:uppercase;font-weight:600;letter-spacing:0.8px;">{"Mest Forsinket" if language == "da" else "Most Overdue"}</div>
            <div style="font-size:14px;font-weight:700;color:#dc2626;margin-top:2px;">{most_overdue} <span style="font-size:11px;color:#64748b;font-weight:600;">{"dage" if language == "da" else "days"}</span></div>
          </div>
          <div>
            <div style="font-size:10px;color:#64748b;text-transform:uppercase;font-weight:600;letter-spacing:0.8px;">{"Grundårsager" if language == "da" else "Root Causes"}</div>
            <div style="font-size:14px;font-weight:700;color:#7c3aed;margin-top:2px;">{root_cause_count}</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div style="display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid #edf2f7;">
    <div style="padding:14px;text-align:center;border-right:1px solid #edf2f7;">
      <div style="font-size:20px;font-weight:800;color:#1a202c;">{total_activities}</div>
      <div style="font-size:9px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:0.8px;margin-top:2px;">{"Aktiviteter" if language == "da" else "Activities"}</div>
    </div>
    <div style="padding:14px;text-align:center;border-right:1px solid #edf2f7;">
      <div style="font-size:20px;font-weight:800;color:{status_color};">{delayed_count}</div>
      <div style="font-size:9px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:0.8px;margin-top:2px;">{"Forsinkede" if language == "da" else "Delayed"}</div>
    </div>
    <div style="padding:14px;text-align:center;border-right:1px solid #edf2f7;">
      <div style="font-size:20px;font-weight:800;color:#dc2626;">{critical_count}</div>
      <div style="font-size:9px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:0.8px;margin-top:2px;">{"Kritiske" if language == "da" else "Critical"}</div>
    </div>
    <div style="padding:14px;text-align:center;">
      <div style="font-size:20px;font-weight:800;color:#1a202c;">{areas_affected}</div>
      <div style="font-size:9px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:0.8px;margin-top:2px;">{"Områder" if language == "da" else "Areas"}</div>
    </div>
  </div>
</div>'''


MODULE_CONFIG = {
    "MANAGEMENT_CONCLUSION": {"label_en": "Management Conclusion", "label_da": "Ledelseskonklusion", "color": "#0d9488", "icon": "management"},
    "LEDELSESKONKLUSION": {"label_en": "Management Conclusion", "label_da": "Ledelseskonklusion", "color": "#0d9488", "icon": "management"},
    "SCHEDULE_OVERVIEW": {"label_en": "Schedule Overview", "label_da": "Tidsplanoversigt", "color": "#0d9488", "icon": "overview"},
    "TIDSPLANOVERSIGT": {"label_en": "Schedule Overview", "label_da": "Tidsplanoversigt", "color": "#0d9488", "icon": "overview"},
    "DELAYED_ACTIVITIES": {"label_en": "Delayed Activities", "label_da": "Forsinkede Aktiviteter", "color": "#dc2626", "icon": "delayed"},
    "FORSINKEDE_AKTIVITETER": {"label_en": "Delayed Activities", "label_da": "Forsinkede Aktiviteter", "color": "#dc2626", "icon": "delayed"},
    "MODULE_A_DELAYED_ACTIVITIES": {"label_en": "Delayed Activities", "label_da": "Forsinkede Aktiviteter", "color": "#dc2626", "icon": "delayed"},
    "MODUL_A_FORSINKEDE_AKTIVITETER": {"label_en": "Delayed Activities", "label_da": "Forsinkede Aktiviteter", "color": "#dc2626", "icon": "delayed"},
    "ROOT_CAUSE_ANALYSIS": {"label_en": "Root Cause Analysis", "label_da": "Årsagsanalyse", "color": "#7c3aed", "icon": "rootcause"},
    "ÅRSAGSANALYSE": {"label_en": "Root Cause Analysis", "label_da": "Årsagsanalyse", "color": "#7c3aed", "icon": "rootcause"},
    "PRIORITY_ACTIONS": {"label_en": "Priority Actions", "label_da": "Prioriterede Handlinger", "color": "#059669", "icon": "actions"},
    "PRIORITEREDE_HANDLINGER": {"label_en": "Priority Actions", "label_da": "Prioriterede Handlinger", "color": "#059669", "icon": "actions"},
    "RESOURCE_ASSESSMENT": {"label_en": "Resource Assessment", "label_da": "Ressourcevurdering", "color": "#d97706", "icon": "resource"},
    "RESSOURCEVURDERING": {"label_en": "Resource Assessment", "label_da": "Ressourcevurdering", "color": "#d97706", "icon": "resource"},
    "SUMMARY_BY_AREA": {"label_en": "Summary by Area", "label_da": "Oversigt efter Område", "color": "#2563eb", "icon": "area"},
    "OVERSIGT_EFTER_OMRÅDE": {"label_en": "Summary by Area", "label_da": "Oversigt efter Område", "color": "#2563eb", "icon": "area"},
}

SECTION_ICONS = {
    "management": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
    "overview": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
    "delayed": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>',
    "rootcause": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
    "actions": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>',
    "resource": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    "area": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>',
}


def _split_sections(markdown: str) -> List[Tuple[str, str]]:
    cleaned = re.sub(r"<!--INSIGHT_DATA:.*?-->", "", markdown, flags=re.DOTALL).strip()
    cleaned = re.sub(r"IMPORTANT:\s*total_activities\s*=.*?delayed_count\.", "", cleaned, flags=re.DOTALL).strip()

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
        return f'<div style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;padding:24px;background:#ffffff;border-radius:16px;border:1px solid #e2e8f0;"><h2 style="color:#1a202c;margin-bottom:16px;">Nova Insight Report</h2><div style="white-space:pre-wrap;color:#4a5568;line-height:1.7;font-size:13px;">{safe_text}</div></div>'


def _format_predictive_internal(markdown: str, language: str) -> str:
    insight_data = _parse_insight_data(markdown)
    sections = _split_sections(markdown)

    report_title = "Nova Insight — Tidsplananalyse" if language == "da" else "Nova Insight — Schedule Analysis"
    subtitle = "Beslutningsstøtte til projektledere" if language == "da" else "Decision support for project managers"

    html_parts = [f'''
<style>
@keyframes novaFadeIn {{ from {{ opacity:0;transform:translateY(8px); }} to {{ opacity:1;transform:translateY(0); }} }}
.nova-report .module-card {{ animation:novaFadeIn 0.4s ease-out backwards; }}
.nova-report .module-card:nth-child(2) {{ animation-delay:0.08s; }}
.nova-report .module-card:nth-child(3) {{ animation-delay:0.12s; }}
.nova-report .module-card:nth-child(4) {{ animation-delay:0.16s; }}
.nova-report .module-card:nth-child(5) {{ animation-delay:0.2s; }}
.nova-report .module-card:nth-child(6) {{ animation-delay:0.24s; }}
.nova-report .module-card:nth-child(7) {{ animation-delay:0.28s; }}
.nova-report .module-card:hover {{ border-color:#cbd5e1 !important;box-shadow:0 4px 12px rgba(0,0,0,0.06); }}
.nova-report table tr:hover {{ background:#edf2f7 !important; }}
.nova-report ::-webkit-scrollbar {{ height:6px; }}
.nova-report ::-webkit-scrollbar-track {{ background:#f1f5f9;border-radius:6px; }}
.nova-report ::-webkit-scrollbar-thumb {{ background:#cbd5e1;border-radius:6px; }}
</style>
<div class="nova-report" style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#ffffff;border-radius:20px;padding:28px;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,0.06);">

  <div style="text-align:center;margin-bottom:24px;padding-bottom:24px;border-bottom:1px solid #edf2f7;">
    <div style="display:inline-flex;align-items:center;gap:12px;margin-bottom:10px;">
      <div style="width:40px;height:40px;border-radius:12px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#0d9488,#0891b2);box-shadow:0 2px 8px rgba(13,148,136,0.2);">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l-3 3"/></svg>
      </div>
      <div style="text-align:left;">
        <h2 style="font-size:20px;font-weight:800;color:#1a202c;margin:0;letter-spacing:-0.3px;">{report_title}</h2>
        <p style="font-size:11px;color:#94a3b8;margin:2px 0 0 0;letter-spacing:0.3px;">{subtitle}</p>
      </div>
    </div>
    
  </div>''']

    if insight_data:
        html_parts.append(_build_hero_section(insight_data, language))

    if not insight_data:
        no_data_label = "Analytiske data ikke tilgængelige — oversigtsmetrikker kan ikke vises." if language == "da" else "Analytical data unavailable — summary metrics cannot be rendered."
        html_parts.append(f'<div style="margin:0 0 16px 0;padding:12px 18px;background:#fffbeb;border-radius:10px;border:1px solid #fde68a;"><p style="margin:0;color:#92400e;font-size:12px;font-weight:600;">{no_data_label}</p></div>')

    for section_key, section_body in sections:
        if section_key == "_PREAMBLE":
            html_parts.append(f'<div class="module-card" style="margin:0 0 14px 0;padding:16px 20px;background:#f0fdfa;border-radius:12px;border:1px solid #99f6e4;border-left:3px solid #0d9488;transition:all 0.2s ease;">')
            html_parts.append(_render_content_block(section_body.split("\n"), "#0d9488"))
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
        icon_svg = SECTION_ICONS.get(icon_key, SECTION_ICONS["overview"])

        content_html = _render_content_block(section_body.split("\n"), color)

        is_management = any(k in config_key for k in ["MANAGEMENT", "LEDELSE"])
        is_root_cause = any(k in config_key for k in ["ROOT_CAUSE", "ÅRSAG"])
        is_actions = any(k in config_key for k in ["PRIORITY_ACTIONS", "PRIORITEREDE"])

        extra_style = ""
        if is_management:
            extra_style = "background:linear-gradient(135deg,#f0fdfa,#ecfeff);border:1px solid #99f6e4;border-left:4px solid #0d9488;"
        elif is_root_cause:
            extra_style = "border-left:4px solid #7c3aed;"
        elif is_actions:
            extra_style = "border-left:4px solid #059669;"

        html_parts.append(f'''
  <div class="module-card" style="margin:0 0 14px 0;padding:20px;background:#ffffff;border-radius:14px;border:1px solid #e2e8f0;{extra_style}transition:all 0.2s ease;box-shadow:0 1px 2px rgba(0,0,0,0.04);">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
      <div style="width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;background:{color}10;border:1px solid {color}20;">
        <span style="color:{color};">{icon_svg}</span>
      </div>
      <h3 style="font-size:15px;font-weight:700;color:#1a202c;margin:0;flex:1;letter-spacing:-0.2px;">{label}</h3>
    </div>
    {content_html}
  </div>''')

    timestamp_label = "Genereret af Nova Insight AI" if language == "da" else "Generated by Nova Insight AI"
    html_parts.append(f'''
  <div style="margin-top:8px;padding-top:14px;border-top:1px solid #edf2f7;display:flex;align-items:center;justify-content:center;gap:8px;">
    <div style="width:6px;height:6px;border-radius:50%;background:#0d9488;box-shadow:0 0 6px rgba(13,148,136,0.3);"></div>
    <span style="font-size:10px;color:#94a3b8;letter-spacing:0.5px;">{timestamp_label}</span>
  </div>
</div>''')

    return "\n".join(html_parts)
