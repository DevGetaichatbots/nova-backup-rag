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

    days_col_idx = -1
    for i, h in enumerate(headers):
        h_lower = h.lower()
        if "overdue" in h_lower or "forsinket" in h_lower or "days" in h_lower or "dage" in h_lower:
            days_col_idx = i
            break

    header_html = ""
    for i, h in enumerate(headers):
        align = "right" if i == days_col_idx else "left"
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
            elif "0%" in cell:
                content = f'<span style="color:#dc2626;font-weight:600;font-size:13px;">{_escape(cell)}</span>'
            else:
                content = f'<span style="color:#4a5568;font-size:13px;">{_escape(cell)}</span>'

            align = "right" if ci == days_col_idx else "left"
            cells_html += f'<td style="padding:11px 14px;border-bottom:1px solid #edf2f7;vertical-align:middle;text-align:{align};">{content}</td>'

        rows_html.append(f'<tr style="background:{bg};transition:background 0.15s;" onmouseover="this.style.background=\'#edf2f7\'" onmouseout="this.style.background=\'{bg}\'">{cells_html}</tr>')

    row_count = len(rows)

    return f'''<div style="overflow-x:auto;border-radius:12px;margin:16px 0;background:#ffffff;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
<table style="width:100%;min-width:700px;border-collapse:collapse;">
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
                f'<li style="margin:6px 0;line-height:1.6;padding-left:18px;position:relative;font-size:14px;color:#4a5568;"><span style="position:absolute;left:0;color:{accent_color};font-weight:bold;font-size:16px;line-height:1.35;">›</span>{item}</li>'
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

        if stripped.startswith("- ") or stripped.startswith("• ") or stripped.startswith("* "):
            item_raw = stripped[2:]
            item_safe = _escape(item_raw)
            item_safe = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color:#1a202c;font-weight:600;">\1</strong>', item_safe)
            list_items.append(item_safe)
            continue

        if re.match(r"^\d+\.\s+", stripped):
            num_match = re.match(r"^(\d+)\.\s+(.*)", stripped)
            if num_match:
                num = num_match.group(1)
                item_raw = num_match.group(2)
                item_safe = _escape(item_raw)
                item_safe = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color:#1a202c;font-weight:600;">\1</strong>', item_safe)
                list_items.append(f'<span style="color:{accent_color};font-weight:700;margin-right:6px;">{num}.</span>{item_safe}')
                continue

        flush_list()

        safe = _escape(stripped)

        bold_line = re.match(r"^\*\*(.+?)\*\*$", stripped)
        if bold_line:
            text = _escape(bold_line.group(1))
            text_lower = text.lower()
            if any(k in text_lower for k in ["total", "antal"]):
                parts.append(f'<div style="margin:18px 0 12px;padding:14px 18px;background:linear-gradient(135deg,#f0fdfa,#ecfeff);border-radius:10px;border:1px solid #99f6e4;"><p style="margin:0;color:#0f766e;font-size:15px;font-weight:700;">{text}</p></div>')
                continue
            if any(k in text_lower for k in ["summary", "oversigt", "most critical", "mest kritiske", "assessment", "vurdering"]):
                parts.append(f'<h4 style="margin:22px 0 10px;color:#1a202c;font-size:14px;font-weight:700;padding-bottom:8px;border-bottom:1px solid #e2e8f0;">{text}</h4>')
                continue
            if any(k in text_lower for k in ["reference", "referencedato", "filtering", "filtrering"]):
                parts.append(f'<p style="margin:8px 0;color:#4a5568;font-size:13px;font-weight:600;background:#f7fafc;padding:8px 14px;border-radius:8px;border-left:3px solid {accent_color};">{text}</p>')
                continue

        text = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color:#1a202c;font-weight:600;">\1</strong>', safe)
        parts.append(f'<p style="margin:6px 0;color:#4a5568;line-height:1.7;font-size:14px;">{text}</p>')

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
    ref_date = _escape(str(insight_data.get("reference_date") or ""))

    if delayed_count == 0:
        status_color = "#0d9488"
        status_bg = "#f0fdfa"
        status_border = "#99f6e4"
        status_label = "Ingen forsinkelser" if language == "da" else "No Delays"
    elif delayed_count <= 10:
        status_color = "#d97706"
        status_bg = "#fffbeb"
        status_border = "#fde68a"
        status_label = "Moderat" if language == "da" else "Moderate"
    elif delayed_count <= 25:
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

    return f'''
<div style="margin:0 0 20px 0;background:#ffffff;border-radius:16px;border:1px solid #e2e8f0;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
  <div style="background:linear-gradient(135deg,#f0fdfa,#ecfeff);padding:24px 28px 20px;border-bottom:1px solid #e2e8f0;">
    <div style="display:flex;align-items:center;gap:24px;flex-wrap:wrap;">

      <div style="text-align:center;flex-shrink:0;min-width:100px;">
        <div style="font-size:48px;font-weight:900;color:{status_color};line-height:1;">
          <span style="display:inline-block;">0</span>
        </div>
        <div style="font-size:10px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:1.5px;margin-top:4px;">
          {"FORSINKEDE" if language == "da" else "DELAYED"}
        </div>
        <script>
          (function() {{
            var el = document.currentScript.parentElement.querySelector('span');
            var target = {delayed_count};
            var duration = 1200;
            var start = performance.now();
            function animate(now) {{
              var elapsed = now - start;
              var progress = Math.min(elapsed / duration, 1);
              var eased = 1 - Math.pow(1 - progress, 3);
              el.textContent = Math.round(eased * target);
              if (progress < 1) requestAnimationFrame(animate);
            }}
            requestAnimationFrame(animate);
          }})();
        </script>
      </div>

      <div style="flex:1;min-width:200px;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
          <span style="display:inline-block;padding:4px 14px;border-radius:20px;font-size:11px;font-weight:700;color:{status_color};background:{status_bg};border:1px solid {status_border};">{status_label}</span>
        </div>

        <div style="margin-bottom:12px;">
          <div style="display:flex;justify-content:space-between;margin-bottom:5px;">
            <span style="font-size:11px;color:#64748b;font-weight:600;">{"Forsinkede af total" if language == "da" else "Delayed of total"}</span>
            <span style="font-size:12px;color:#1a202c;font-weight:700;">{delayed_count}/{total_activities} ({pct}%)</span>
          </div>
          <div style="height:8px;background:#e2e8f0;border-radius:4px;overflow:hidden;">
            <div style="height:100%;width:0%;background:{bar_color};border-radius:4px;transition:width 1.2s cubic-bezier(0.4,0,0.2,1);">
              <script>(function(){{ var el = document.currentScript.parentElement; setTimeout(function(){{ el.style.width = '{bar_width}%'; }}, 300); }})();</script>
            </div>
          </div>
        </div>

        <div style="display:flex;gap:20px;flex-wrap:wrap;">
          <div>
            <div style="font-size:10px;color:#64748b;text-transform:uppercase;font-weight:600;letter-spacing:0.8px;">{"Referencedato" if language == "da" else "Ref. Date"}</div>
            <div style="font-size:14px;font-weight:700;color:#1a202c;margin-top:2px;">{ref_date}</div>
          </div>
          <div>
            <div style="font-size:10px;color:#64748b;text-transform:uppercase;font-weight:600;letter-spacing:0.8px;">{"Mest Forsinket" if language == "da" else "Most Overdue"}</div>
            <div style="font-size:14px;font-weight:700;color:#dc2626;margin-top:2px;">{most_overdue} <span style="font-size:11px;color:#64748b;font-weight:600;">{"dage" if language == "da" else "days"}</span></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div style="display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid #edf2f7;">
    <div style="padding:14px;text-align:center;border-right:1px solid #edf2f7;">
      <div style="font-size:20px;font-weight:800;color:#1a202c;">{total_activities}</div>
      <div style="font-size:9px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:0.8px;margin-top:2px;">{"Aktiviteter" if language == "da" else "Activities"}</div>
    </div>
    <div style="padding:14px;text-align:center;border-right:1px solid #edf2f7;">
      <div style="font-size:20px;font-weight:800;color:{status_color};">{delayed_count}</div>
      <div style="font-size:9px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:0.8px;margin-top:2px;">{"Forsinkede" if language == "da" else "Delayed"}</div>
    </div>
    <div style="padding:14px;text-align:center;">
      <div style="font-size:20px;font-weight:800;color:#1a202c;">{areas_affected}</div>
      <div style="font-size:9px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:0.8px;margin-top:2px;">{"Områder" if language == "da" else "Areas"}</div>
    </div>
  </div>
</div>'''


MODULE_CONFIG = {
    "SCHEDULE_OVERVIEW": {"label_en": "Schedule Overview", "label_da": "Tidsplanoversigt", "color": "#0d9488", "icon": "overview"},
    "TIDSPLANOVERSIGT": {"label_en": "Schedule Overview", "label_da": "Tidsplanoversigt", "color": "#0d9488", "icon": "overview"},
    "MODULE_A_DELAYED_ACTIVITIES": {"label_en": "Delayed Activities", "label_da": "Forsinkede Aktiviteter", "color": "#dc2626", "icon": "delayed"},
    "MODUL_A_FORSINKEDE_AKTIVITETER": {"label_en": "Delayed Activities", "label_da": "Forsinkede Aktiviteter", "color": "#dc2626", "icon": "delayed"},
    "MODULE_A_OVERDUE": {"label_en": "Delayed Activities", "label_da": "Forsinkede Aktiviteter", "color": "#dc2626", "icon": "delayed"},
}

SECTION_ICONS = {
    "overview": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
    "delayed": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>',
}


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
        return f'<div style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;padding:24px;background:#ffffff;border-radius:16px;border:1px solid #e2e8f0;"><h2 style="color:#1a202c;margin-bottom:16px;">Nova Insight Report</h2><div style="white-space:pre-wrap;color:#4a5568;line-height:1.7;font-size:13px;">{safe_text}</div></div>'


def _format_predictive_internal(markdown: str, language: str) -> str:
    insight_data = _parse_insight_data(markdown)
    sections = _split_sections(markdown)

    report_title = "Nova Insight — Forsinkede Aktiviteter" if language == "da" else "Nova Insight — Delayed Activities"
    subtitle = "Forsinkelsesanalyse drevet af Nova Insight" if language == "da" else "Delay analysis powered by Nova Insight"

    html_parts = [f'''
<style>
@keyframes novaFadeIn {{ from {{ opacity:0;transform:translateY(8px); }} to {{ opacity:1;transform:translateY(0); }} }}
.nova-report .module-card {{ animation:novaFadeIn 0.4s ease-out backwards; }}
.nova-report .module-card:nth-child(2) {{ animation-delay:0.08s; }}
.nova-report .module-card:nth-child(3) {{ animation-delay:0.12s; }}
.nova-report .module-card:nth-child(4) {{ animation-delay:0.16s; }}
.nova-report .module-card:nth-child(5) {{ animation-delay:0.2s; }}
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

        is_module_a = any(k in config_key for k in ["MODULE_A", "MODUL_A", "DELAYED", "OVERDUE", "FORSINKEDE"])

        module_badge = ""
        if is_module_a:
            module_badge = f'<span style="font-size:10px;font-weight:700;color:#dc2626;background:#fef2f2;padding:2px 8px;border-radius:6px;border:1px solid #fecaca;letter-spacing:0.3px;">A</span>'

        color_bg = f"{color}08"
        color_border_light = f"{color}30"

        html_parts.append(f'''
  <div class="module-card" style="margin:0 0 14px 0;padding:20px;background:#ffffff;border-radius:14px;border:1px solid #e2e8f0;border-left:3px solid {color};transition:all 0.2s ease;box-shadow:0 1px 2px rgba(0,0,0,0.04);">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
      <div style="width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;background:{color}10;border:1px solid {color}20;">
        <span style="color:{color};">{icon_svg}</span>
      </div>
      <h3 style="font-size:15px;font-weight:700;color:#1a202c;margin:0;flex:1;letter-spacing:-0.2px;">{label}</h3>
      {module_badge}
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
