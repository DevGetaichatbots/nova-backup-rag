"""
Premium Structured HTML Converter
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
    "removed": {"label": "Removed Tasks", "label_da": "Fjernede Opgaver", "color": "#ef4444", "bg": "rgba(239, 68, 68, 0.08)"},
    "added": {"label": "Added Tasks", "label_da": "Tilføjede Opgaver", "color": "#10b981", "bg": "rgba(16, 185, 129, 0.08)"},
    "moved": {"label": "Modified / Moved Tasks", "label_da": "Ændrede / Flyttede Opgaver", "color": "#f59e0b", "bg": "rgba(245, 158, 11, 0.08)"},
    "delayed": {"label": "Delayed Tasks", "label_da": "Forsinkede Opgaver", "color": "#ef4444", "bg": "rgba(239, 68, 68, 0.06)"},
    "accelerated": {"label": "Accelerated Tasks", "label_da": "Fremskyndede Opgaver", "color": "#10b981", "bg": "rgba(16, 185, 129, 0.06)"},
    "critical": {"label": "Critical Path", "label_da": "Kritisk Vej", "color": "#f59e0b", "bg": "rgba(245, 158, 11, 0.06)"},
    "risks": {"label": "Risks", "label_da": "Risici", "color": "#ef4444", "bg": "rgba(239, 68, 68, 0.06)"},
    "default": {"label": "Other Tasks", "label_da": "Andre Opgaver", "color": "#06b6d4", "bg": "rgba(6, 182, 212, 0.06)"}
}


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
    if "removed" in lower or "fjernet" in lower or "not present in new" in lower:
        return "removed"
    if "added" in lower or "tilføjet" in lower or "not present in old" in lower or "new" in lower:
        return "added"
    if "moved" in lower or "modified" in lower or "ændret" in lower or "flyttet" in lower:
        return "moved"
    if "delayed" in lower or "later" in lower or "forsinket" in lower or "senere" in lower:
        return "delayed"
    if "earlier" in lower or "accelerated" in lower or "tidligere" in lower or "fremskyndet" in lower:
        return "accelerated"
    if "critical" in lower or "kritisk" in lower:
        return "critical"
    if "risk" in lower or "risiko" in lower:
        return "risks"
    return "default"


def parse_tables(markdown: str) -> Tuple[List[str], Dict[str, List[List[str]]]]:
    if not markdown or "|" not in markdown:
        return [], {}
    
    lines = markdown.split("\n")
    headers = []
    groups = {k: [] for k in CATEGORY_CONFIG.keys()}
    current_table_headers = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        
        if re.match(r"^\|[\s\-:|]+\|$", line):
            continue
        
        cells = [c.strip() for c in line.strip("|").split("|")]
        
        if not current_table_headers:
            current_table_headers = cells
            if not headers:
                headers = cells
        else:
            category = detect_category(" ".join(cells))
            groups[category].append(cells)
    
    return headers, groups


def escape_html(text: str) -> str:
    if not text:
        return ""
    return html.escape(str(text))


def get_status_badge(value: str) -> str:
    if not value or value in ["—", "-", "n/a", ""]:
        return '<span style="color: #94a3b8;">—</span>'
    
    lower = value.lower().strip()
    if any(x in lower for x in ["added", "new", "earlier", "tidligere", "tilføjet"]):
        return f'<span style="display: inline-flex; padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 600; background: rgba(16, 185, 129, 0.12); color: #059669; border: 1px solid rgba(16, 185, 129, 0.2);">{escape_html(value)}</span>'
    if any(x in lower for x in ["removed", "later", "senere", "delayed", "forsinket", "fjernet"]):
        return f'<span style="display: inline-flex; padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 600; background: rgba(239, 68, 68, 0.12); color: #dc2626; border: 1px solid rgba(239, 68, 68, 0.2);">{escape_html(value)}</span>'
    if any(x in lower for x in ["moved", "modified", "changed", "ændret", "flyttet"]):
        return f'<span style="display: inline-flex; padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 600; background: rgba(245, 158, 11, 0.12); color: #d97706; border: 1px solid rgba(245, 158, 11, 0.2);">{escape_html(value)}</span>'
    return f'<span style="display: inline-flex; padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 600; background: rgba(100, 116, 139, 0.1); color: #475569; border: 1px solid rgba(100, 116, 139, 0.15);">{escape_html(value)}</span>'


def generate_table_html(headers: List[str], groups: Dict[str, List[List[str]]], language: str = "en") -> str:
    total_tasks = sum(len(rows) for rows in groups.values())
    if total_tasks == 0 or not headers:
        return ""
    
    table_id = f"tbl_{datetime.now().strftime('%H%M%S')}"
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    all_rows = []
    for rows in groups.values():
        all_rows.extend(rows)
    csv_data = base64.b64encode(json.dumps([headers] + all_rows).encode()).decode()
    
    html_parts = [f'''
<div class="comparison-table-container" style="margin-bottom: 32px;">
  <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; flex-wrap: wrap; gap: 16px;">
    <div style="display: flex; align-items: center; gap: 14px;">
      <div style="width: 52px; height: 52px; border-radius: 16px; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #06b6d4, #0891b2); box-shadow: 0 8px 24px rgba(6, 182, 212, 0.3);">
        <span style="color: white;">{SVG_ICONS["table"]}</span>
      </div>
      <div>
        <h3 style="font-size: 24px; font-weight: 800; color: #0f172a; margin: 0;">{"Sammenligningsresultater" if language == "da" else "Comparison Results"}</h3>
        <p style="font-size: 14px; color: #64748b; margin: 4px 0 0 0;">{total_tasks} {"opgaver analyseret" if language == "da" else "tasks analyzed"}</p>
      </div>
    </div>
  </div>

  <div id="csvData_{table_id}" style="display:none;">{csv_data}</div>
  <div id="csvFilename_{table_id}" style="display:none;">comparison_results_{date_str}.csv</div>

  <div style="position: relative; overflow: hidden; border-radius: 20px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08), 0 0 0 1px rgba(0, 214, 214, 0.15); background: #ffffff;">
    <div style="overflow-x: auto;">
      <table style="width: 100%; min-width: 700px; border-collapse: separate; border-spacing: 0;">
        <thead>
          <tr style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%);">''']
    
    for idx, header in enumerate(headers):
        is_last = idx == len(headers) - 1
        border = "" if is_last else "border-right: 1px solid rgba(255,255,255,0.08);"
        html_parts.append(f'''
            <th style="padding: 18px 20px; text-align: left; font-size: 11px; font-weight: 700; color: rgba(255,255,255,0.95); text-transform: uppercase; letter-spacing: 1.2px; {border} white-space: nowrap;">
              {escape_html(header)}
              <div style="position: absolute; bottom: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #00D6D6, #06b6d4);"></div>
            </th>''')
    
    html_parts.append('''
          </tr>
        </thead>
        <tbody>''')
    
    category_order = ["removed", "added", "delayed", "accelerated", "moved", "critical", "risks", "default"]
    
    for category in category_order:
        rows = groups.get(category, [])
        if not rows:
            continue
        
        config = CATEGORY_CONFIG[category]
        label = config["label_da"] if language == "da" else config["label"]
        color = config["color"]
        bg = config["bg"]
        icon = SVG_ICONS.get(category, SVG_ICONS["default"])
        
        html_parts.append(f'''
          <tr style="background: {bg};">
            <td colspan="{len(headers)}" style="padding: 14px 20px; border-bottom: 2px solid {color}30;">
              <div style="display: flex; align-items: center; gap: 10px;">
                <span style="color: {color};">{icon}</span>
                <span style="font-size: 14px; font-weight: 700; color: {color}; text-transform: uppercase; letter-spacing: 0.8px;">{label}</span>
                <span style="padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; background: {color}20; color: {color};">{len(rows)}</span>
              </div>
            </td>
          </tr>''')
        
        for row_idx, row in enumerate(rows):
            row_bg = "#ffffff" if row_idx % 2 == 0 else "rgba(248, 250, 252, 0.8)"
            html_parts.append(f'''
          <tr style="background: {row_bg}; transition: all 0.2s ease;">''')
            
            for cell_idx, cell in enumerate(row):
                is_last = cell_idx == len(row) - 1
                border = "" if is_last else "border-right: 1px solid #f1f5f9;"
                header_name = headers[cell_idx] if cell_idx < len(headers) else ""
                
                if cell_idx == 0:
                    content = f'<span style="color: #1e293b; font-weight: 600;">{escape_html(cell or "N/A")}</span>'
                elif any(x in header_name.lower() for x in ["status", "difference", "forskel", "change", "ændring"]):
                    content = get_status_badge(cell)
                elif any(x in header_name.lower() for x in ["week", "uge", "#"]):
                    if not cell or cell in ["—", "-"]:
                        content = '<span style="color: #94a3b8;">—</span>'
                    else:
                        content = f'<span style="display: inline-block; padding: 6px 14px; border-radius: 8px; font-weight: 600; background: linear-gradient(135deg, #e0f7f7, #d1fae5); color: #0e7490; font-size: 13px; border: 1px solid rgba(6, 182, 212, 0.2);">{escape_html(cell)}</span>'
                else:
                    content = f'<span style="color: #475569; font-size: 14px;">{escape_html(cell or "N/A")}</span>'
                
                html_parts.append(f'''
            <td style="padding: 16px 20px; font-size: 14px; {border} border-bottom: 1px solid #f1f5f9; vertical-align: middle;">{content}</td>''')
            
            html_parts.append('''
          </tr>''')
    
    html_parts.append(f'''
        </tbody>
      </table>
    </div>
    <div style="padding: 16px 24px; border-top: 1px solid rgba(0, 214, 214, 0.1); background: linear-gradient(135deg, rgba(240, 253, 250, 0.8), rgba(224, 247, 247, 0.6)); display: flex; justify-content: space-between; align-items: center;">
      <span style="font-size: 14px; color: #475569; font-weight: 500;">Total: {total_tasks} {"opgaver" if language == "da" else "tasks"}</span>
      <span style="font-size: 12px; color: #94a3b8;">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}</span>
    </div>
  </div>
</div>''')
    
    return "".join(html_parts)


def generate_summary_html(summary_content: str, language: str = "en") -> str:
    if not summary_content or not summary_content.strip():
        return ""
    
    lines = summary_content.split("\n")
    processed = []
    list_items = []
    
    def flush_list():
        nonlocal list_items
        if list_items:
            processed.append('<ul style="margin: 12px 0; padding-left: 0; list-style: none;">')
            for item in list_items:
                processed.append(f'<li style="margin: 10px 0; line-height: 1.6; padding-left: 24px; position: relative;"><span style="position: absolute; left: 0; color: #8b5cf6; font-size: 18px;">•</span>{item}</li>')
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
        <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 24px;">
          <div style="width: 52px; height: 52px; border-radius: 16px; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #8b5cf6, #7c3aed); box-shadow: 0 8px 24px rgba(139, 92, 246, 0.3);">
            <span style="color: white;">{SVG_ICONS["summary"]}</span>
          </div>
          <h2 style="font-size: 24px; font-weight: 800; color: #0f172a; margin: 0;">{header_text}</h2>
        </div>''')
            continue
        
        bold_match = re.match(r"^\*\*([^*]+):\*\*$", line) or re.match(r"^\*\*([^*]+)\*\*$", line)
        if bold_match:
            flush_list()
            header_text = bold_match.group(1).rstrip(":")
            processed.append(f'<h3 style="font-size: 15px; font-weight: 700; color: #7c3aed; margin: 24px 0 12px 0; padding-bottom: 8px; border-bottom: 2px solid rgba(139, 92, 246, 0.15); text-transform: uppercase; letter-spacing: 0.5px;">{escape_html(header_text)}</h3>')
            continue
        
        if line.startswith("• ") or line.startswith("* ") or line.startswith("- "):
            item_text = line[2:]
            item_text = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color: #6d28d9; font-weight: 600;">\1</strong>', item_text)
            list_items.append(item_text)
            continue
        
        flush_list()
        text = escape_html(line)
        text = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color: #6d28d9; font-weight: 600;">\1</strong>', text)
        processed.append(f'<p style="margin: 12px 0; color: #334155; line-height: 1.7; font-size: 15px;">{text}</p>')
    
    flush_list()
    
    return f'''
    <div class="summary-section" style="margin: 32px 0; padding: 28px; background: linear-gradient(135deg, rgba(139, 92, 246, 0.06), rgba(124, 58, 237, 0.02)); border-radius: 20px; box-shadow: 0 4px 24px rgba(139, 92, 246, 0.08), 0 0 0 1px rgba(139, 92, 246, 0.1);">
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
        "stable": {"color": "#10b981", "bg": "rgba(16, 185, 129, 0.12)", "border": "rgba(16, 185, 129, 0.25)", "label_en": "Stable", "label_da": "Stabil"},
        "attention": {"color": "#f59e0b", "bg": "rgba(245, 158, 11, 0.12)", "border": "rgba(245, 158, 11, 0.25)", "label_en": "Attention Needed", "label_da": "Kræver Opmærksomhed"},
        "high_risk": {"color": "#ef4444", "bg": "rgba(239, 68, 68, 0.12)", "border": "rgba(239, 68, 68, 0.25)", "label_en": "High Risk", "label_da": "Høj Risiko"}
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
            processed.append('<ul style="margin: 12px 0; padding-left: 0; list-style: none;">')
            for item in list_items:
                processed.append(f'<li style="margin: 10px 0; line-height: 1.6; padding-left: 24px; position: relative;"><span style="position: absolute; left: 0; color: {color}; font-size: 18px;">•</span>{item}</li>')
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
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 28px; flex-wrap: wrap; gap: 20px;">
          <div style="display: flex; align-items: center; gap: 14px;">
            <div style="width: 52px; height: 52px; border-radius: 16px; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, {color}, {color}cc); box-shadow: 0 8px 24px {color}40;">
              <span style="color: white;">{SVG_ICONS["pulse"]}</span>
            </div>
            <h2 style="font-size: 24px; font-weight: 800; color: #0f172a; margin: 0;">{header_text}</h2>
          </div>
          <div style="display: flex; align-items: center; gap: 12px; padding: 12px 24px; border-radius: 50px; background: {bg}; border: 2px solid {border};">
            <div style="width: 12px; height: 12px; border-radius: 50%; background: {color}; box-shadow: 0 0 8px {color}80;"></div>
            <span style="font-size: 15px; font-weight: 700; color: {color};">{status_label}</span>
          </div>
        </div>''')
            continue
        
        if re.match(r"^\*\*Status:\*\*", line, re.IGNORECASE):
            continue
        
        bold_match = re.match(r"^\*\*([^*]+):\*\*$", line) or re.match(r"^\*\*([^*]+)\*\*$", line)
        if bold_match:
            flush_list()
            header_text = bold_match.group(1).rstrip(":")
            processed.append(f'<h3 style="font-size: 15px; font-weight: 700; color: {color}; margin: 24px 0 12px 0; padding-bottom: 8px; border-bottom: 2px solid {color}20; text-transform: uppercase; letter-spacing: 0.5px;">{escape_html(header_text)}</h3>')
            continue
        
        if line.startswith("• ") or line.startswith("* ") or line.startswith("- "):
            item_text = line[2:]
            item_text = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="font-weight: 600;">\1</strong>', item_text)
            list_items.append(item_text)
            continue
        
        flush_list()
        text = escape_html(line)
        text = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="font-weight: 600;">\1</strong>', text)
        processed.append(f'<p style="margin: 12px 0; color: #334155; line-height: 1.7; font-size: 15px;">{text}</p>')
    
    flush_list()
    
    metrics_html = ""
    if health_data:
        metrics = []
        if health_data.get("delayed_count") is not None:
            metrics.append(f'<div style="text-align: center; padding: 16px 12px; background: linear-gradient(135deg, rgba(239, 68, 68, 0.08), rgba(239, 68, 68, 0.03)); border-radius: 14px; border: 1px solid rgba(239, 68, 68, 0.12);"><div style="font-size: 28px; font-weight: 800; color: #ef4444;">{health_data["delayed_count"]}</div><div style="font-size: 10px; color: #64748b; text-transform: uppercase; margin-top: 4px; font-weight: 600;">{"Forsinket" if language == "da" else "Delayed"}</div></div>')
        if health_data.get("accelerated_count") is not None:
            metrics.append(f'<div style="text-align: center; padding: 16px 12px; background: linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(16, 185, 129, 0.03)); border-radius: 14px; border: 1px solid rgba(16, 185, 129, 0.12);"><div style="font-size: 28px; font-weight: 800; color: #10b981;">{health_data["accelerated_count"]}</div><div style="font-size: 10px; color: #64748b; text-transform: uppercase; margin-top: 4px; font-weight: 600;">{"Fremskyndet" if language == "da" else "Accelerated"}</div></div>')
        if health_data.get("added_count") is not None:
            metrics.append(f'<div style="text-align: center; padding: 16px 12px; background: linear-gradient(135deg, rgba(6, 182, 212, 0.08), rgba(6, 182, 212, 0.03)); border-radius: 14px; border: 1px solid rgba(6, 182, 212, 0.12);"><div style="font-size: 28px; font-weight: 800; color: #06b6d4;">{health_data["added_count"]}</div><div style="font-size: 10px; color: #64748b; text-transform: uppercase; margin-top: 4px; font-weight: 600;">{"Tilføjet" if language == "da" else "Added"}</div></div>')
        if health_data.get("removed_count") is not None:
            metrics.append(f'<div style="text-align: center; padding: 16px 12px; background: linear-gradient(135deg, rgba(239, 68, 68, 0.08), rgba(239, 68, 68, 0.03)); border-radius: 14px; border: 1px solid rgba(239, 68, 68, 0.12);"><div style="font-size: 28px; font-weight: 800; color: #ef4444;">{health_data["removed_count"]}</div><div style="font-size: 10px; color: #64748b; text-transform: uppercase; margin-top: 4px; font-weight: 600;">{"Fjernet" if language == "da" else "Removed"}</div></div>')
        
        if metrics:
            metrics_html = f'<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 12px; margin-top: 24px; padding-top: 24px; border-top: 2px solid {color}15;">{"".join(metrics)}</div>'
    
    return f'''
    <div class="health-section" style="margin: 32px 0; padding: 28px; background: linear-gradient(135deg, {bg}, rgba(255,255,255,0.9)); border-radius: 20px; box-shadow: 0 4px 24px {color}15, 0 0 0 1px {color}20;">
      {"".join(processed)}
      {metrics_html}
    </div>'''


def format_response_as_html(markdown: str, language: str = "en") -> str:
    parsed = parse_structured_response(markdown)
    
    headers, groups = parse_tables(parsed["tables_section"])
    
    table_html = generate_table_html(headers, groups, language)
    summary_html = generate_summary_html(parsed["summary_section"], language)
    health_html = generate_health_html(parsed["health_section"], parsed["health_data"], language)
    
    return f'''
<div class="agent-response" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  {table_html}
  {summary_html}
  {health_html}
</div>'''
