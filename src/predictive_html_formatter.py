import re
import json
import html
from typing import Dict, List, Optional, Tuple

NOVA_ICONS = {
    "report": '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4zm2 2H5V5h14v14zM19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z" fill="currentColor"/></svg>',
    "overview": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path d="M12 6v6l4 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    "overdue": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#ef4444" opacity="0.15"/><path d="M12 8v4M12 16h.01" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round"/></svg>',
    "delayed": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#ef4444" stroke-width="2" opacity="0.9"/><path d="M12 6v6l-3 3" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "calendar": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><rect x="3" y="4" width="18" height="18" rx="2" stroke="currentColor" stroke-width="2"/><path d="M16 2v4M8 2v4M3 10h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    "warning": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M12 2L2 22h20L12 2z" fill="#fbbf24" opacity="0.15"/><path d="M12 9v4M12 17h.01" stroke="#fbbf24" stroke-width="2.5" stroke-linecap="round"/></svg>',
    "check": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#10b981" opacity="0.15"/><path d="M8 12l3 3 5-5" stroke="#10b981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "chart": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M18 20V10M12 20V4M6 20v-6" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "health": '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M22 12h-4l-3 9L9 3l-3 9H2" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
}

MODULE_CONFIG = {
    "SCHEDULE_OVERVIEW": {"label_en": "Schedule Overview", "label_da": "Tidsplanoversigt", "color": "#0ea5e9", "icon": "overview"},
    "TIDSPLANOVERSIGT": {"label_en": "Schedule Overview", "label_da": "Tidsplanoversigt", "color": "#0ea5e9", "icon": "overview"},
    "MODULE_A_DELAYED_ACTIVITIES": {"label_en": "Delayed Activities", "label_da": "Forsinkede Aktiviteter", "color": "#ef4444", "icon": "delayed"},
    "MODUL_A_FORSINKEDE_AKTIVITETER": {"label_en": "Delayed Activities", "label_da": "Forsinkede Aktiviteter", "color": "#ef4444", "icon": "delayed"},
    "MODULE_A_OVERDUE": {"label_en": "Delayed Activities", "label_da": "Forsinkede Aktiviteter", "color": "#ef4444", "icon": "delayed"},
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


def _get_severity_color(days_overdue: int) -> dict:
    if days_overdue >= 120:
        return {"color": "#ff4d6a", "bg": "rgba(255, 77, 106, 0.08)", "border": "rgba(255, 77, 106, 0.25)", "label": "Critical"}
    if days_overdue >= 60:
        return {"color": "#f87171", "bg": "rgba(248, 113, 113, 0.08)", "border": "rgba(248, 113, 113, 0.25)", "label": "High"}
    if days_overdue >= 30:
        return {"color": "#fbbf24", "bg": "rgba(251, 191, 36, 0.08)", "border": "rgba(251, 191, 36, 0.25)", "label": "Medium"}
    return {"color": "#fb923c", "bg": "rgba(251, 146, 60, 0.08)", "border": "rgba(251, 146, 60, 0.25)", "label": "Low"}


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
        width_style = "min-width:60px;" if i == days_col_idx else ("min-width:280px;" if i == 1 else "")
        header_html += f'<th style="padding:14px 16px;text-align:{align};font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:1.2px;white-space:nowrap;border-bottom:2px solid rgba(239,68,68,0.3);background:rgba(0,0,0,0.2);{width_style}">{_escape(h)}</th>'

    rows_html = []
    for idx, row in enumerate(rows):
        bg = "rgba(0,0,0,0.08)" if idx % 2 == 0 else "transparent"

        days_val = 0
        if days_col_idx >= 0 and days_col_idx < len(row):
            days_match = re.search(r"(\d+)", row[days_col_idx])
            if days_match:
                days_val = int(days_match.group(1))

        severity = _get_severity_color(days_val)

        cells_html = ""
        for ci, cell in enumerate(row):
            if ci == 0:
                content = f'<span style="font-weight:700;color:#e2e8f0;font-size:13px;font-family:\'SF Mono\',SFMono-Regular,Menlo,monospace;">{_escape(cell)}</span>'
            elif ci == days_col_idx:
                content = f'<span style="display:inline-flex;align-items:center;gap:6px;font-weight:700;color:{severity["color"]};font-size:13px;"><span style="width:8px;height:8px;border-radius:50%;background:{severity["color"]};flex-shrink:0;box-shadow:0 0 6px {severity["color"]}40;"></span>{_escape(cell)}</span>'
            elif "0%" in cell:
                content = f'<span style="color:#f87171;font-weight:600;font-size:13px;">{_escape(cell)}</span>'
            else:
                content = f'<span style="color:#94a3b8;font-size:13px;">{_escape(cell)}</span>'

            align = "right" if ci == days_col_idx else "left"
            cells_html += f'<td style="padding:13px 16px;border-bottom:1px solid rgba(148,163,184,0.06);vertical-align:middle;text-align:{align};">{content}</td>'

        rows_html.append(f'<tr style="background:{bg};transition:all 0.15s ease;" onmouseover="this.style.background=\'rgba(239,68,68,0.04)\'" onmouseout="this.style.background=\'{bg}\'">{cells_html}</tr>')

    row_count = len(rows)
    count_label = f"{row_count} delayed activit{'y' if row_count == 1 else 'ies'}"

    return f'''<div style="overflow-x:auto;border-radius:14px;margin:16px 0;background:#0f1729;border:1px solid rgba(239,68,68,0.12);box-shadow:0 4px 24px rgba(0,0,0,0.2);">
<div style="padding:12px 16px;background:rgba(239,68,68,0.04);border-bottom:1px solid rgba(239,68,68,0.08);display:flex;align-items:center;justify-content:space-between;">
  <span style="font-size:11px;color:#94a3b8;font-weight:600;letter-spacing:0.5px;">{count_label}</span>
  <span style="font-size:10px;color:#475569;letter-spacing:0.5px;">sorted by days overdue ↓</span>
</div>
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

        if re.match(r"^\d+\.\s+", stripped):
            num_match = re.match(r"^(\d+)\.\s+(.*)", stripped)
            if num_match:
                num = num_match.group(1)
                item_raw = num_match.group(2)
                item_safe = _escape(item_raw)
                item_safe = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color:#e2e8f0;font-weight:600;">\1</strong>', item_safe)
                list_items.append(f'<span style="color:{accent_color};font-weight:700;margin-right:6px;">{num}.</span>{item_safe}')
                continue

        flush_list()

        safe = _escape(stripped)

        bold_line = re.match(r"^\*\*(.+?)\*\*$", stripped)
        if bold_line:
            text = _escape(bold_line.group(1))
            if any(k in text.lower() for k in ["total", "antal", "reference", "referencedato", "filtering", "filtrering", "summary", "oversigt", "most critical", "mest kritiske", "assessment", "vurdering"]):
                is_count = any(k in text.lower() for k in ["total", "antal"])
                is_heading = any(k in text.lower() for k in ["summary", "oversigt", "most critical", "mest kritiske", "assessment", "vurdering"])
                if is_count:
                    parts.append(f'<div style="margin:18px 0 12px;padding:14px 18px;background:rgba(239,68,68,0.06);border-radius:12px;border:1px solid rgba(239,68,68,0.12);"><p style="margin:0;color:#f87171;font-size:15px;font-weight:700;">{text}</p></div>')
                elif is_heading:
                    parts.append(f'<h4 style="margin:22px 0 10px;color:#e2e8f0;font-size:14px;font-weight:700;padding-bottom:8px;border-bottom:1px solid rgba(148,163,184,0.1);">{text}</h4>')
                else:
                    parts.append(f'<p style="margin:10px 0;color:#e2e8f0;font-size:14px;font-weight:600;">{text}</p>')
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


def _build_hero_section(insight_data: Dict, language: str) -> str:
    if not insight_data:
        return ""

    delayed_count = _safe_int(insight_data.get("delayed_count") or 0)
    total_activities = _safe_int(insight_data.get("total_activities") or 0)
    most_overdue = _safe_int(insight_data.get("most_overdue_days") or 0)
    areas_affected = _safe_int(insight_data.get("areas_affected") or 0)
    ref_date = _escape(str(insight_data.get("reference_date") or ""))
    schedule_name = _escape(str(insight_data.get("schedule_name") or ""))
    format_detected = _escape(str(insight_data.get("format_detected") or ""))

    if delayed_count == 0:
        status_color = "#34d399"
        status_glow = "rgba(52,211,153,0.4)"
        status_label = "Ingen forsinkelser" if language == "da" else "No Delays"
        status_bg = "rgba(52,211,153,0.06)"
        status_border = "rgba(52,211,153,0.2)"
    elif delayed_count <= 10:
        status_color = "#fbbf24"
        status_glow = "rgba(251,191,36,0.4)"
        status_label = "Moderat" if language == "da" else "Moderate"
        status_bg = "rgba(251,191,36,0.06)"
        status_border = "rgba(251,191,36,0.2)"
    elif delayed_count <= 25:
        status_color = "#f87171"
        status_glow = "rgba(248,113,113,0.4)"
        status_label = "Alvorlig" if language == "da" else "Serious"
        status_bg = "rgba(248,113,113,0.06)"
        status_border = "rgba(248,113,113,0.2)"
    else:
        status_color = "#ff4d6a"
        status_glow = "rgba(255,77,106,0.4)"
        status_label = "Kritisk" if language == "da" else "Critical"
        status_bg = "rgba(255,77,106,0.06)"
        status_border = "rgba(255,77,106,0.2)"

    pct = min(round((delayed_count / max(total_activities, 1)) * 100), 100) if total_activities > 0 else 0

    bar_width = min(pct, 100)

    return f'''
<div style="margin:0 0 24px 0;background:linear-gradient(145deg,#162032,#1a2742);border-radius:20px;border:1px solid {status_border};overflow:hidden;position:relative;">
  <div style="position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,transparent,{status_color},{status_color},transparent);opacity:0.6;"></div>

  <div style="padding:28px 28px 20px;">
    <div style="display:flex;align-items:center;gap:24px;flex-wrap:wrap;">

      <div style="text-align:center;flex-shrink:0;min-width:120px;">
        <div style="font-size:52px;font-weight:900;color:{status_color};line-height:1;text-shadow:0 0 30px {status_glow};">
          <span style="display:inline-block;animation:novaFadeIn 0.6s ease-out;">0</span>
        </div>
        <div style="font-size:10px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:1.5px;margin-top:6px;">
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
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
          <div style="width:10px;height:10px;border-radius:50%;background:{status_color};box-shadow:0 0 12px {status_glow};"></div>
          <span style="font-size:14px;font-weight:800;color:{status_color};text-transform:uppercase;letter-spacing:1px;">{status_label}</span>
        </div>

        <div style="margin-bottom:14px;">
          <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
            <span style="font-size:10px;color:#475569;font-weight:600;">{"Forsinkede af total" if language == "da" else "Delayed of total"}</span>
            <span style="font-size:11px;color:#94a3b8;font-weight:700;">{delayed_count}/{total_activities} ({pct}%)</span>
          </div>
          <div style="height:8px;background:rgba(148,163,184,0.08);border-radius:4px;overflow:hidden;">
            <div style="height:100%;width:0%;background:linear-gradient(90deg,{status_color},{status_color}dd);border-radius:4px;transition:width 1.2s cubic-bezier(0.4,0,0.2,1);">
              <script>(function(){{ var el = document.currentScript.parentElement; setTimeout(function(){{ el.style.width = '{bar_width}%'; }}, 300); }})();</script>
            </div>
          </div>
        </div>

        <div style="display:flex;gap:16px;flex-wrap:wrap;">
          <div>
            <div style="font-size:9px;color:#475569;text-transform:uppercase;font-weight:700;letter-spacing:1px;">{"Referencedato" if language == "da" else "Ref. Date"}</div>
            <div style="font-size:15px;font-weight:700;color:#e2e8f0;margin-top:2px;">{ref_date}</div>
          </div>
          <div>
            <div style="font-size:9px;color:#475569;text-transform:uppercase;font-weight:700;letter-spacing:1px;">{"Mest Forsinket" if language == "da" else "Most Overdue"}</div>
            <div style="font-size:15px;font-weight:700;color:#f87171;margin-top:2px;">{most_overdue} <span style="font-size:11px;color:#475569;">{"dage" if language == "da" else "days"}</span></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div style="display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid rgba(148,163,184,0.06);">
    <div style="padding:16px;text-align:center;border-right:1px solid rgba(148,163,184,0.06);">
      <div style="font-size:20px;font-weight:800;color:#e2e8f0;">{total_activities}</div>
      <div style="font-size:9px;color:#475569;text-transform:uppercase;font-weight:700;letter-spacing:0.8px;margin-top:3px;">{"Aktiviteter" if language == "da" else "Activities"}</div>
    </div>
    <div style="padding:16px;text-align:center;border-right:1px solid rgba(148,163,184,0.06);">
      <div style="font-size:20px;font-weight:800;color:{status_color};">{delayed_count}</div>
      <div style="font-size:9px;color:#475569;text-transform:uppercase;font-weight:700;letter-spacing:0.8px;margin-top:3px;">{"Forsinkede" if language == "da" else "Delayed"}</div>
    </div>
    <div style="padding:16px;text-align:center;">
      <div style="font-size:20px;font-weight:800;color:#e2e8f0;">{areas_affected}</div>
      <div style="font-size:9px;color:#475569;text-transform:uppercase;font-weight:700;letter-spacing:0.8px;margin-top:3px;">{"Områder" if language == "da" else "Areas"}</div>
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

    report_title = "Nova Insight — Forsinkede Aktiviteter" if language == "da" else "Nova Insight — Delayed Activities"
    subtitle = "Forsinkelsesanalyse drevet af GPT-5.2" if language == "da" else "Delay analysis powered by GPT-5.2"

    html_parts = [f'''
<style>
@keyframes novaFadeIn {{ from {{ opacity:0;transform:translateY(12px); }} to {{ opacity:1;transform:translateY(0); }} }}
@keyframes novaPulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.6; }} }}
.nova-report .module-card {{ animation:novaFadeIn 0.5s ease-out backwards; }}
.nova-report .module-card:nth-child(2) {{ animation-delay:0.1s; }}
.nova-report .module-card:nth-child(3) {{ animation-delay:0.15s; }}
.nova-report .module-card:nth-child(4) {{ animation-delay:0.2s; }}
.nova-report .module-card:nth-child(5) {{ animation-delay:0.25s; }}
.nova-report .module-card:hover {{ border-color:rgba(148,163,184,0.2) !important;transform:translateY(-1px);box-shadow:0 8px 24px rgba(0,0,0,0.3); }}
.nova-report table tr:hover {{ background:rgba(239,68,68,0.04) !important; }}
.nova-report ::-webkit-scrollbar {{ height:6px; }}
.nova-report ::-webkit-scrollbar-track {{ background:rgba(0,0,0,0.2);border-radius:6px; }}
.nova-report ::-webkit-scrollbar-thumb {{ background:rgba(148,163,184,0.25);border-radius:6px; }}
</style>
<div class="nova-report" style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:linear-gradient(180deg,#0c1322 0%,#0f172a 8%,#0f172a 100%);border-radius:24px;padding:32px;border:1px solid rgba(148,163,184,0.08);box-shadow:0 4px 48px rgba(0,0,0,0.4);">

  <div style="text-align:center;margin-bottom:28px;padding-bottom:28px;border-bottom:1px solid rgba(148,163,184,0.08);">
    <div style="display:inline-flex;align-items:center;gap:14px;margin-bottom:12px;">
      <div style="width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#ef4444,#dc2626);box-shadow:0 0 30px rgba(239,68,68,0.25);">
        <span style="color:white;">{NOVA_ICONS["delayed"]}</span>
      </div>
      <div style="text-align:left;">
        <h2 style="font-size:22px;font-weight:800;color:#f1f5f9;margin:0;letter-spacing:-0.5px;">{report_title}</h2>
        <p style="font-size:11px;color:#475569;margin:2px 0 0 0;letter-spacing:0.5px;">{subtitle}</p>
      </div>
    </div>
    <div style="display:inline-flex;gap:8px;margin-top:8px;">
      <span style="padding:4px 12px;border-radius:20px;font-size:10px;font-weight:700;background:rgba(239,68,68,0.1);color:#f87171;border:1px solid rgba(239,68,68,0.15);letter-spacing:0.5px;">MODULE A</span>
      <span style="padding:4px 12px;border-radius:20px;font-size:10px;font-weight:700;background:rgba(139,92,246,0.1);color:#a78bfa;border:1px solid rgba(139,92,246,0.15);letter-spacing:0.5px;">GPT-5.2</span>
    </div>
  </div>''']

    if insight_data:
        html_parts.append(_build_hero_section(insight_data, language))

    if not insight_data:
        no_data_label = "Analytiske data ikke tilgængelige — oversigtsmetrikker kan ikke vises." if language == "da" else "Analytical data unavailable — summary metrics cannot be rendered."
        html_parts.append(f'<div style="margin:0 0 16px 0;padding:14px 20px;background:rgba(251,191,36,0.06);border-radius:12px;border:1px solid rgba(251,191,36,0.15);"><p style="margin:0;color:#fbbf24;font-size:12px;font-weight:600;">{no_data_label}</p></div>')

    module_index = 0
    for section_key, section_body in sections:
        if section_key == "_PREAMBLE":
            html_parts.append(f'<div class="module-card" style="margin:0 0 16px 0;padding:18px 22px;background:rgba(14,165,233,0.04);border-radius:14px;border:1px solid rgba(14,165,233,0.1);border-left:3px solid #0ea5e9;transition:all 0.2s ease;">')
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

        is_module_a = any(k in config_key for k in ["MODULE_A", "MODUL_A", "DELAYED", "OVERDUE", "FORSINKEDE"])

        module_badge = ""
        if is_module_a:
            module_badge = f'<span style="font-size:10px;font-weight:800;color:{color};background:{color}15;padding:3px 8px;border-radius:6px;letter-spacing:0.5px;">A</span>'

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

    timestamp_label = "Genereret af Nova Insight AI" if language == "da" else "Generated by Nova Insight AI"
    html_parts.append(f'''
  <div style="margin-top:8px;padding-top:16px;border-top:1px solid rgba(148,163,184,0.06);display:flex;align-items:center;justify-content:center;gap:8px;">
    <div style="width:6px;height:6px;border-radius:50%;background:#ef4444;box-shadow:0 0 8px rgba(239,68,68,0.4);"></div>
    <span style="font-size:10px;color:#475569;letter-spacing:0.5px;">{timestamp_label}</span>
  </div>
</div>''')

    return "\n".join(html_parts)
