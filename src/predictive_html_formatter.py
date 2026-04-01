import json
import html
from typing import Dict, List, Optional


def _e(text) -> str:
    if text is None:
        return ""
    return html.escape(str(text))


def _safe_int(val) -> int:
    try:
        return int(round(float(val)))
    except (ValueError, TypeError):
        return 0


def _svg(name: str, size: int = 16, color: str = "currentColor") -> str:
    icons = {
        "clock": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
        "alert-circle": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>',
        "alert-triangle": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        "activity": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
        "search": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
        "check-square": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>',
        "users": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
        "grid": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>',
        "link": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>',
        "compass": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>',
        "pen-tool": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19l7-7 3 3-7 7-3-3z"/><path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"/><path d="M2 2l7.586 7.586"/><circle cx="11" cy="11" r="2"/></svg>',
        "user": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
        "tool": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>',
        "package": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>',
        "flag": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>',
        "zap": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
        "target": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
        "arrow-right": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>',
        "pause": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>',
        "refresh": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>',
        "play": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
        "clipboard": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>',
        "calendar": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
        "bar-chart": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/></svg>',
        "file-text": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>',
        "shield": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
        "trending-up": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
        "circle-dot": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3" fill="{color}"/></svg>',
    }
    return icons.get(name, "")


def _icon_box(icon_name: str, color: str, size: int = 16) -> str:
    return f'<span style="display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;flex-shrink:0;">{_svg(icon_name, size, color)}</span>'


PRIORITY_STYLES = {
    "CRITICAL_NOW": {"color": "#dc2626", "bg": "#fef2f2", "border": "#fecaca", "label_en": "CRITICAL NOW", "label_da": "KRITISK NU"},
    "IMPORTANT_NEXT": {"color": "#d97706", "bg": "#fffbeb", "border": "#fde68a", "label_en": "IMPORTANT NEXT", "label_da": "VIGTIG NÆSTE"},
    "MONITOR": {"color": "#0891b2", "bg": "#ecfeff", "border": "#a5f3fc", "label_en": "MONITOR", "label_da": "OVERVÅG"},
}

TASK_TYPE_STYLES = {
    "Coordination": {"color": "#7c3aed", "bg": "#f5f3ff", "label_da": "Koordinering"},
    "Design": {"color": "#2563eb", "bg": "#eff6ff", "label_da": "Design"},
    "Bygherre": {"color": "#c026d3", "bg": "#fdf4ff", "label_da": "Bygherre"},
    "Production": {"color": "#059669", "bg": "#ecfdf5", "label_da": "Produktion"},
    "Procurement": {"color": "#d97706", "bg": "#fffbeb", "label_da": "Indkøb"},
    "Milestone": {"color": "#64748b", "bg": "#f8fafc", "label_da": "Milepæl"},
}

PROBLEM_TYPE_ICON_MAP = {
    "Coordination blockage": "link",
    "Design input missing": "pen-tool",
    "Bygherre decision pending": "user",
    "Production delay": "tool",
    "Procurement delay": "package",
}

RESOURCE_TYPE_CONFIG = {
    "coordination_bottleneck": {"icon": "link", "color": "#7c3aed", "bg": "#f5f3ff", "label_en": "Coordination", "label_da": "Koordinering"},
    "design_dependency": {"icon": "pen-tool", "color": "#2563eb", "bg": "#eff6ff", "label_en": "Design", "label_da": "Design"},
    "bygherre_escalation": {"icon": "user", "color": "#c026d3", "bg": "#fdf4ff", "label_en": "Bygherre", "label_da": "Bygherre"},
    "production_manpower": {"icon": "tool", "color": "#059669", "bg": "#ecfdf5", "label_en": "Production", "label_da": "Produktion"},
    "management_attention": {"icon": "clipboard", "color": "#ea580c", "bg": "#fff7ed", "label_en": "Management", "label_da": "Ledelse"},
    "procurement_dependency": {"icon": "package", "color": "#d97706", "bg": "#fffbeb", "label_en": "Procurement", "label_da": "Indkøb"},
}

ACTION_TYPE_ICON_MAP = {
    "coordination": "link",
    "bygherre_decision": "user",
    "design_input": "pen-tool",
    "freeze_downstream": "pause",
    "reassess": "refresh",
    "release_work": "play",
    "escalation": "zap",
    "procurement": "package",
}

FORCEABLE_STYLES = {
    "possible": {"color": "#059669", "bg": "#ecfdf5", "border": "#6ee7b7", "icon": "check-square", "label_en": "POSSIBLE", "label_da": "MULIG"},
    "limited": {"color": "#d97706", "bg": "#fffbeb", "border": "#fde68a", "icon": "alert-triangle", "label_en": "LIMITED", "label_da": "BEGRÆNSET"},
    "not_recommended": {"color": "#dc2626", "bg": "#fef2f2", "border": "#fecaca", "icon": "alert-circle", "label_en": "NOT RECOMMENDED", "label_da": "FRARÅDES"},
}

CONSTRAINT_TYPE_CONFIG = {
    "coordination_dependency": {"icon": "link", "color": "#7c3aed", "label_en": "Coordination", "label_da": "Koordinering"},
    "design_input_required": {"icon": "pen-tool", "color": "#2563eb", "label_en": "Design Input", "label_da": "Designinput"},
    "bygherre_decision_required": {"icon": "user", "color": "#c026d3", "label_en": "Client Decision", "label_da": "Bygherrebeslutning"},
    "procurement_waiting": {"icon": "package", "color": "#d97706", "label_en": "Procurement", "label_da": "Indkøb"},
    "execution_capacity": {"icon": "tool", "color": "#059669", "label_en": "Execution", "label_da": "Udførelse"},
    "milestone_gate": {"icon": "flag", "color": "#64748b", "label_en": "Milestone", "label_da": "Milepæl"},
    "cascading_dependencies": {"icon": "grid", "color": "#ea580c", "label_en": "Cascading", "label_da": "Kaskade"},
}


def _severity_color(days: int) -> dict:
    if days >= 120:
        return {"color": "#dc2626", "bg": "#fef2f2", "border": "#fecaca"}
    if days >= 60:
        return {"color": "#ea580c", "bg": "#fff7ed", "border": "#fed7aa"}
    if days >= 30:
        return {"color": "#d97706", "bg": "#fffbeb", "border": "#fde68a"}
    return {"color": "#0891b2", "bg": "#ecfeff", "border": "#a5f3fc"}


def _render_hero(data: Dict, lang: str) -> str:
    ins = data.get("insight_data", {})
    total = _safe_int(ins.get("total_activities", 0))
    delayed = _safe_int(ins.get("delayed_count", 0))
    critical = _safe_int(ins.get("critical_count", 0))
    important = _safe_int(ins.get("important_count", 0))
    monitor = _safe_int(ins.get("monitor_count", 0))
    root_causes = _safe_int(ins.get("root_cause_count", 0))
    most_overdue = _safe_int(ins.get("most_overdue_days", 0))
    areas = _safe_int(ins.get("areas_affected", 0))
    primary_risk = _e(ins.get("primary_risk", ""))

    if critical == 0 and delayed == 0:
        sc, sbg, sb = "#0d9488", "#f0fdfa", "#99f6e4"
        sl = "Ingen forsinkelser" if lang == "da" else "No Delays"
    elif critical <= 3:
        sc, sbg, sb = "#d97706", "#fffbeb", "#fde68a"
        sl = "Moderat risiko" if lang == "da" else "Moderate Risk"
    elif critical <= 8:
        sc, sbg, sb = "#ea580c", "#fff7ed", "#fed7aa"
        sl = "Alvorlig risiko" if lang == "da" else "Serious Risk"
    else:
        sc, sbg, sb = "#dc2626", "#fef2f2", "#fecaca"
        sl = "Kritisk risiko" if lang == "da" else "Critical Risk"

    pct = min(round((delayed / max(total, 1)) * 100), 100) if total > 0 else 0
    bc = "#0d9488" if pct < 15 else ("#d97706" if pct < 30 else ("#ea580c" if pct < 50 else "#dc2626"))

    cl = "Kritisk" if lang == "da" else "Critical"
    il = "Vigtig" if lang == "da" else "Important"
    ml = "Overvåg" if lang == "da" else "Monitor"

    risk_html = ""
    if primary_risk and primary_risk.lower() not in ("", "none", "n/a"):
        rl = "Primær risiko" if lang == "da" else "Primary Risk"
        risk_html = f'<div style="margin-top:14px;padding:10px 14px;background:#fef2f2;border-radius:8px;border:1px solid #fecaca;"><div style="display:flex;align-items:center;gap:6px;margin-bottom:3px;">{_svg("alert-triangle", 12, "#991b1b")}<span style="font-size:10px;color:#991b1b;text-transform:uppercase;font-weight:700;letter-spacing:0.8px;">{rl}</span></div><div style="font-size:13px;color:#991b1b;font-weight:600;line-height:1.5;">{primary_risk}</div></div>'

    return f'''
<div style="margin:0 0 22px;background:#fff;border-radius:16px;border:1px solid #e2e8f0;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06);">
  <div style="background:linear-gradient(135deg,#f0fdfa,#ecfeff);padding:28px 28px 22px;border-bottom:1px solid #e2e8f0;">
    <div style="display:flex;align-items:center;gap:28px;flex-wrap:wrap;">
      <div style="text-align:center;flex-shrink:0;min-width:110px;">
        <div style="font-size:56px;font-weight:900;color:{sc};line-height:1;">{delayed}</div>
        <div style="font-size:10px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:1.5px;margin-top:4px;">{"FORSINKEDE" if lang == "da" else "DELAYED"}</div>
      </div>
      <div style="flex:1;min-width:220px;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
          <span style="display:inline-block;padding:5px 16px;border-radius:20px;font-size:12px;font-weight:700;color:{sc};background:{sbg};border:1px solid {sb};">{sl}</span>
        </div>
        <div style="margin-bottom:10px;">
          <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
            <span style="font-size:11px;color:#64748b;font-weight:600;">{"Forsinkede af total" if lang == "da" else "Delayed of total"}</span>
            <span style="font-size:12px;color:#1a202c;font-weight:700;">{delayed}/{total} ({pct}%)</span>
          </div>
          <div style="height:10px;background:#e2e8f0;border-radius:5px;overflow:hidden;"><div style="height:100%;width:{min(pct,100)}%;background:linear-gradient(90deg,{bc},{bc}cc);border-radius:5px;"></div></div>
        </div>
        <div style="display:flex;gap:16px;margin-top:14px;flex-wrap:wrap;">
          <div style="display:flex;align-items:center;gap:6px;padding:4px 12px;background:#fef2f2;border-radius:8px;border:1px solid #fecaca;"><span style="width:8px;height:8px;border-radius:50%;background:#dc2626;display:inline-block;"></span><span style="font-size:12px;color:#991b1b;font-weight:700;">{critical}</span><span style="font-size:11px;color:#991b1b;font-weight:600;">{cl}</span></div>
          <div style="display:flex;align-items:center;gap:6px;padding:4px 12px;background:#fffbeb;border-radius:8px;border:1px solid #fde68a;"><span style="width:8px;height:8px;border-radius:50%;background:#d97706;display:inline-block;"></span><span style="font-size:12px;color:#92400e;font-weight:700;">{important}</span><span style="font-size:11px;color:#92400e;font-weight:600;">{il}</span></div>
          <div style="display:flex;align-items:center;gap:6px;padding:4px 12px;background:#ecfeff;border-radius:8px;border:1px solid #a5f3fc;"><span style="width:8px;height:8px;border-radius:50%;background:#0891b2;display:inline-block;"></span><span style="font-size:12px;color:#155e75;font-weight:700;">{monitor}</span><span style="font-size:11px;color:#155e75;font-weight:600;">{ml}</span></div>
        </div>
        {risk_html}
      </div>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(5,1fr);border-top:1px solid #edf2f7;">
    <div style="padding:16px;text-align:center;border-right:1px solid #edf2f7;"><div style="font-size:22px;font-weight:800;color:#1a202c;">{total}</div><div style="font-size:9px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:.8px;margin-top:3px;">{"Aktiviteter" if lang == "da" else "Activities"}</div></div>
    <div style="padding:16px;text-align:center;border-right:1px solid #edf2f7;"><div style="font-size:22px;font-weight:800;color:{sc};">{delayed}</div><div style="font-size:9px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:.8px;margin-top:3px;">{"Forsinkede" if lang == "da" else "Delayed"}</div></div>
    <div style="padding:16px;text-align:center;border-right:1px solid #edf2f7;"><div style="font-size:22px;font-weight:800;color:#dc2626;">{critical}</div><div style="font-size:9px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:.8px;margin-top:3px;">{"Kritiske" if lang == "da" else "Critical"}</div></div>
    <div style="padding:16px;text-align:center;border-right:1px solid #edf2f7;"><div style="font-size:22px;font-weight:800;color:#7c3aed;">{root_causes}</div><div style="font-size:9px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:.8px;margin-top:3px;">{"Grundårsager" if lang == "da" else "Root Causes"}</div></div>
    <div style="padding:16px;text-align:center;"><div style="font-size:22px;font-weight:800;color:#1a202c;">{areas}</div><div style="font-size:9px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:.8px;margin-top:3px;">{"Områder" if lang == "da" else "Areas"}</div></div>
  </div>
</div>'''


def _render_management_conclusion(data: Dict, lang: str) -> str:
    text = _e(data.get("management_conclusion", ""))
    if not text:
        return ""
    label = "Ledelseskonklusion" if lang == "da" else "Management Conclusion"
    sub = "Overordnet vurdering og anbefaling" if lang == "da" else "Executive assessment and recommendation"
    return f'''
<div class="module-card" style="margin:0 0 16px;padding:22px 24px;background:linear-gradient(135deg,#f0fdfa,#ecfeff);border-radius:14px;border:1px solid #99f6e4;border-left:5px solid #0d9488;transition:all .2s;box-shadow:0 1px 3px rgba(0,0,0,.04);">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid #99f6e4;">
    <div style="width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:#0d948812;border:1px solid #0d948822;">{_svg("activity", 18, "#0d9488")}</div>
    <div><h3 style="font-size:16px;font-weight:700;color:#1a202c;margin:0;">{label}</h3><p style="margin:0;font-size:11px;color:#94a3b8;font-weight:500;">{sub}</p></div>
  </div>
  <p style="margin:0;color:#374151;line-height:1.9;font-size:14.5px;font-weight:500;">{text}</p>
</div>'''


def _render_schedule_overview(data: Dict, lang: str) -> str:
    ov = data.get("schedule_overview", {})
    if not ov:
        return ""
    label = "Tidsplanoversigt" if lang == "da" else "Schedule Overview"

    fields = [
        ("clipboard", "Tidsplan" if lang == "da" else "Schedule", _e(ov.get("schedule_name", ""))),
        ("calendar", "Referencedato" if lang == "da" else "Reference Date", _e(ov.get("reference_date", ""))),
        ("bar-chart", "Total aktiviteter" if lang == "da" else "Total Activities", str(ov.get("total_activities", 0))),
        ("alert-circle", "Forsinkede" if lang == "da" else "Delayed", str(ov.get("delayed_count", 0))),
        ("tool", "Områder" if lang == "da" else "Areas", ", ".join(ov.get("areas_covered", []))),
    ]

    fields_html = ""
    for icon_name, name, val in fields:
        fields_html += f'<div style="display:flex;gap:10px;padding:10px 0;border-bottom:1px solid #f1f5f9;align-items:center;">{_icon_box(icon_name, "#64748b", 14)}<span style="font-size:12px;color:#64748b;font-weight:600;min-width:120px;">{name}</span><span style="font-size:13px;color:#1a202c;font-weight:600;">{val}</span></div>'

    return f'''
<div class="module-card" style="margin:0 0 16px;padding:22px 24px;background:#fff;border-radius:14px;border:1px solid #e2e8f0;border-left:5px solid #0d9488;transition:all .2s;box-shadow:0 1px 3px rgba(0,0,0,.04);">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid #f1f5f9;">
    <div style="width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:#0d948812;border:1px solid #0d948822;">{_svg("clock", 18, "#0d9488")}</div>
    <h3 style="font-size:16px;font-weight:700;color:#1a202c;margin:0;">{label}</h3>
  </div>
  {fields_html}
</div>'''


def _render_delayed_table(data: Dict, lang: str) -> str:
    activities = data.get("delayed_activities", [])
    if not activities:
        return ""

    label = "Forsinkede Aktiviteter" if lang == "da" else "Delayed Activities"
    sub = f"{len(activities)} {'aktiviteter fundet' if lang == 'da' else 'activities found'}"

    headers = ["Id", "Opgavenavn", "Startdato", "Slutdato", "Varighed", "% færdigt",
               "Dage Forsinket" if lang == "da" else "Days Overdue",
               "Opgavetype" if lang == "da" else "Task Type",
               "Prioritet" if lang == "da" else "Priority"]

    header_html = ""
    for i, h in enumerate(headers):
        align = "right" if i == 6 else ("center" if i >= 7 else "left")
        header_html += f'<th style="padding:12px 14px;text-align:{align};font-size:11px;font-weight:700;color:#134e4a;text-transform:uppercase;letter-spacing:.8px;white-space:nowrap;border-bottom:2px solid #99f6e4;background:linear-gradient(135deg,#f0fdfa,#ecfeff);">{h}</th>'

    rows_html = ""
    for idx, act in enumerate(activities):
        bg = "#f7fafc" if idx % 2 == 0 else "#ffffff"
        days = _safe_int(act.get("days_overdue", 0))
        sev = _severity_color(days)
        priority = act.get("priority", "MONITOR")
        p_style = PRIORITY_STYLES.get(priority, PRIORITY_STYLES["MONITOR"])
        p_label = p_style[f"label_{lang}"] if f"label_{lang}" in p_style else p_style.get("label_en", priority)
        task_type = act.get("task_type", "Production")
        t_style = TASK_TYPE_STYLES.get(task_type, TASK_TYPE_STYLES["Production"])
        t_label = t_style.get("label_da", task_type) if lang == "da" else task_type

        days_label = f"{days} {'dage' if lang == 'da' else 'days'}"

        cells = [
            f'<span style="font-weight:700;color:#1a202c;font-size:13px;font-family:\'SF Mono\',\'Cascadia Code\',monospace;">{_e(act.get("id",""))}</span>',
            f'<span style="color:#4a5568;font-size:13px;">{_e(act.get("task_name",""))}</span>',
            f'<span style="color:#4a5568;font-size:13px;">{_e(act.get("start_date",""))}</span>',
            f'<span style="color:#4a5568;font-size:13px;">{_e(act.get("end_date",""))}</span>',
            f'<span style="color:#4a5568;font-size:13px;">{_e(act.get("duration",""))}</span>',
            f'<span style="color:#dc2626;font-weight:600;font-size:13px;">{_e(act.get("progress","0%"))}</span>',
            f'<span style="display:inline-block;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:700;color:{sev["color"]};background:{sev["bg"]};border:1px solid {sev["border"]};">{days_label}</span>',
            f'<span style="display:inline-block;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:600;color:{t_style["color"]};background:{t_style["bg"]};white-space:nowrap;">{t_label}</span>',
            f'<span style="display:inline-block;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700;color:{p_style["color"]};background:{p_style["bg"]};border:1px solid {p_style["border"]};white-space:nowrap;">{p_label}</span>',
        ]

        aligns = ["left","left","left","left","left","left","right","center","center"]
        tds = ""
        for ci, (cell, align) in enumerate(zip(cells, aligns)):
            tds += f'<td style="padding:11px 14px;border-bottom:1px solid #edf2f7;vertical-align:middle;text-align:{align};">{cell}</td>'

        rows_html += f'<tr style="background:{bg};transition:background .15s;" onmouseover="this.style.background=\'#edf2f7\'" onmouseout="this.style.background=\'{bg}\'">{tds}</tr>'

    return f'''
<div class="module-card" style="margin:0 0 16px;padding:22px 24px;background:#fff;border-radius:14px;border:1px solid #e2e8f0;border-left:5px solid #0d9488;transition:all .2s;box-shadow:0 1px 3px rgba(0,0,0,.04);">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid #f1f5f9;">
    <div style="width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:#dc262612;border:1px solid #dc262622;">{_svg("alert-circle", 18, "#dc2626")}</div>
    <div><h3 style="font-size:16px;font-weight:700;color:#1a202c;margin:0;">{label}</h3><p style="margin:0;font-size:11px;color:#94a3b8;font-weight:500;">{sub}</p></div>
  </div>
  <div style="overflow-x:auto;border-radius:12px;background:#fff;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,.06);">
    <table style="width:100%;min-width:950px;border-collapse:collapse;"><thead><tr>{header_html}</tr></thead><tbody>{rows_html}</tbody></table>
  </div>
</div>'''


def _render_root_cause_analysis(data: Dict, lang: str) -> str:
    rcs = data.get("root_cause_analysis", [])
    dcs = data.get("downstream_consequences", [])
    if not rcs and not dcs:
        return ""

    label = "Årsagsanalyse" if lang == "da" else "Root Cause Analysis"
    sub = "Grundårsager vs. afledte konsekvenser" if lang == "da" else "Root causes vs. downstream consequences"

    cards_html = ""
    for rc in rcs:
        problem_type = rc.get("problem_type", "")
        icon_name = PROBLEM_TYPE_ICON_MAP.get(problem_type, "search")
        affected = rc.get("affected_task_ids", [])
        affected_text = ", ".join(affected) if affected else ("Ingen" if lang == "da" else "None")

        fields = [
            ("clock", "#dc2626", "Status", f'{rc.get("days_overdue", 0)} {"dage forsinket" if lang == "da" else "days overdue"}, 0%'),
            ("search", "#7c3aed", "Problemtype" if lang == "da" else "Problem Type", _e(problem_type)),
            ("zap", "#d97706", "Hvorfor det er vigtigt" if lang == "da" else "Why It Matters", _e(rc.get("why_it_matters", ""))),
            ("link", "#2563eb", "Nedstrømseffekt" if lang == "da" else "Downstream Impact", _e(rc.get("downstream_impact", ""))),
            ("alert-triangle", "#ea580c", "Konsekvens hvis uløst" if lang == "da" else "If Unresolved", _e(rc.get("consequence_if_unresolved", ""))),
            ("target", "#64748b", "Berørte opgaver" if lang == "da" else "Affected Tasks", affected_text),
        ]

        fields_html = ""
        for f_icon, f_color, f_name, f_val in fields:
            fields_html += f'''<div style="display:flex;gap:10px;padding:10px 0;border-bottom:1px solid #f0fdf4;align-items:flex-start;">
  {_icon_box(f_icon, f_color, 14)}
  <div style="flex:1;min-width:0;"><div style="font-size:11px;font-weight:700;color:{f_color};text-transform:uppercase;letter-spacing:.6px;margin-bottom:3px;">{f_name}</div><div style="font-size:13px;color:#374151;line-height:1.6;">{f_val}</div></div>
</div>'''

        cards_html += f'''<div style="margin:14px 0;background:#fff;border-radius:12px;border:1px solid #99f6e4;border-left:4px solid #0d9488;overflow:hidden;box-shadow:0 1px 3px rgba(13,148,136,.08);">
  <div style="padding:14px 18px;background:linear-gradient(135deg,#f0fdfa,#ecfeff);border-bottom:1px solid #99f6e4;">
    <div style="display:flex;align-items:center;gap:8px;">
      {_svg(icon_name, 14, "#0d9488")}
      <span style="display:inline-block;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700;color:#134e4a;background:#f0fdfa;border:1px solid #99f6e4;font-family:'SF Mono','Cascadia Code',monospace;">ID {_e(rc.get("id",""))}</span>
      <span style="font-size:13px;font-weight:700;color:#134e4a;">{_e(rc.get("task_name",""))}</span>
    </div>
  </div>
  <div style="padding:6px 18px 14px;">{fields_html}</div>
</div>'''

    dc_html = ""
    if dcs:
        dc_label = "Afledte konsekvenser" if lang == "da" else "Downstream Consequences"
        dc_sub = "Løses når grundårsagen er adresseret" if lang == "da" else "Will likely resolve when root cause is addressed"
        items = ""
        for dc in dcs:
            items += f'<div style="padding:8px 14px;border-bottom:1px solid #f1f5f9;font-size:13px;color:#64748b;line-height:1.6;display:flex;align-items:flex-start;gap:8px;">{_svg("arrow-right", 14, "#94a3b8")}<span>ID <strong style="font-family:\'SF Mono\',\'Cascadia Code\',monospace;color:#475569;">{_e(dc.get("id",""))}</strong> ({_e(dc.get("task_name",""))}) — {"blokeret af" if lang == "da" else "blocked by"} ID {_e(dc.get("blocked_by_id",""))}</span></div>'
        dc_html = f'''<div style="margin:20px 0 8px;background:#f8fafc;border-radius:10px;border:1px solid #e2e8f0;overflow:hidden;">
  <div style="padding:12px 16px;background:#f1f5f9;border-bottom:1px solid #e2e8f0;"><h4 style="margin:0;color:#475569;font-size:13px;font-weight:700;">{dc_label}</h4><p style="margin:3px 0 0;color:#94a3b8;font-size:11px;">{dc_sub}</p></div>
  {items}
</div>'''

    return f'''
<div class="module-card" style="margin:0 0 16px;padding:22px 24px;background:#fff;border-radius:14px;border:1px solid #e2e8f0;border-left:5px solid #0d9488;transition:all .2s;box-shadow:0 1px 3px rgba(0,0,0,.04);">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid #f1f5f9;">
    <div style="width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:#7c3aed12;border:1px solid #7c3aed22;">{_svg("search", 18, "#7c3aed")}</div>
    <div><h3 style="font-size:16px;font-weight:700;color:#1a202c;margin:0;">{label}</h3><p style="margin:0;font-size:11px;color:#94a3b8;font-weight:500;">{sub}</p></div>
  </div>
  {cards_html}
  {dc_html}
</div>'''


def _render_priority_actions(data: Dict, lang: str) -> str:
    actions = data.get("priority_actions", [])
    if not actions:
        return ""

    label = "Prioriterede Handlinger" if lang == "da" else "Priority Actions"
    sub = "Prioriteret handlingsrækkefølge" if lang == "da" else "Prioritized action sequence"

    items_html = ""
    for act in actions:
        step = act.get("step", 0)
        action_text = _e(act.get("action", ""))
        a_type = act.get("action_type", "coordination")
        icon_name = ACTION_TYPE_ICON_MAP.get(a_type, "clipboard")

        items_html += f'''<div style="display:flex;gap:14px;padding:14px 0;border-bottom:1px solid #f1f5f9;align-items:flex-start;">
  <div style="display:flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#0d9488,#0891b2);color:white;font-size:14px;font-weight:800;flex-shrink:0;box-shadow:0 2px 4px rgba(13,148,136,.2);">{step}</div>
  <div style="flex:1;padding-top:5px;">
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">{_icon_box(icon_name, "#64748b", 13)}<span style="font-size:10px;color:#64748b;text-transform:uppercase;font-weight:600;letter-spacing:.5px;">{a_type.replace("_"," ")}</span></div>
    <p style="margin:0;font-size:14px;color:#374151;line-height:1.7;font-weight:500;">{action_text}</p>
  </div>
</div>'''

    return f'''
<div class="module-card" style="margin:0 0 16px;padding:22px 24px;background:#fff;border-radius:14px;border:1px solid #e2e8f0;border-left:5px solid #059669;transition:all .2s;box-shadow:0 1px 3px rgba(0,0,0,.04);">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid #f1f5f9;">
    <div style="width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:#05966912;border:1px solid #05966922;">{_svg("check-square", 18, "#059669")}</div>
    <div><h3 style="font-size:16px;font-weight:700;color:#1a202c;margin:0;">{label}</h3><p style="margin:0;font-size:11px;color:#94a3b8;font-weight:500;">{sub}</p></div>
  </div>
  {items_html}
</div>'''


def _render_resource_assessment(data: Dict, lang: str) -> str:
    items = data.get("resource_assessment", [])
    if not items:
        return ""

    label = "Ressourcevurdering" if lang == "da" else "Resource Assessment"
    sub = "Mandskab vs. koordinering vs. beslutning" if lang == "da" else "Manpower vs. coordination vs. decision"

    cards_html = ""
    for item in items:
        r_type = item.get("resource_type", "management_attention")
        r_config = RESOURCE_TYPE_CONFIG.get(r_type, RESOURCE_TYPE_CONFIG["management_attention"])
        r_label = r_config[f"label_{lang}"] if f"label_{lang}" in r_config else r_config.get("label_en", r_type)

        cards_html += f'''<div style="display:flex;gap:12px;padding:14px 16px;margin:8px 0;background:#fff;border-radius:10px;border:1px solid #e2e8f0;align-items:flex-start;transition:all .15s;" onmouseover="this.style.borderColor='#cbd5e1';this.style.boxShadow='0 2px 6px rgba(0,0,0,.04)'" onmouseout="this.style.borderColor='#e2e8f0';this.style.boxShadow='none'">
  <div style="width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;background:{r_config["bg"]};border:1px solid {r_config["color"]}22;flex-shrink:0;">{_svg(r_config["icon"], 16, r_config["color"])}</div>
  <div style="flex:1;min-width:0;">
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
      <span style="font-weight:700;color:#1a202c;font-size:13px;font-family:'SF Mono','Cascadia Code',monospace;">ID {_e(item.get("id",""))}</span>
      <span style="display:inline-block;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;color:{r_config["color"]};background:{r_config["bg"]};">{r_label}</span>
    </div>
    <p style="margin:0 0 4px;color:#475569;font-size:12px;font-weight:600;">{_e(item.get("task_name",""))}</p>
    <p style="margin:0;color:#4a5568;font-size:13px;line-height:1.7;">{_e(item.get("assessment",""))}</p>
  </div>
</div>'''

    return f'''
<div class="module-card" style="margin:0 0 16px;padding:22px 24px;background:#fff;border-radius:14px;border:1px solid #e2e8f0;border-left:5px solid #0d9488;transition:all .2s;box-shadow:0 1px 3px rgba(0,0,0,.04);">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid #f1f5f9;">
    <div style="width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:#d9770612;border:1px solid #d9770622;">{_svg("users", 18, "#d97706")}</div>
    <div><h3 style="font-size:16px;font-weight:700;color:#1a202c;margin:0;">{label}</h3><p style="margin:0;font-size:11px;color:#94a3b8;font-weight:500;">{sub}</p></div>
  </div>
  {cards_html}
</div>'''


def _render_forcing_assessment(data: Dict, lang: str) -> str:
    items = data.get("forcing_assessment", [])
    if not items:
        return ""

    ins = data.get("insight_data", {})
    forceable_count = _safe_int(ins.get("forceable_count", 0))
    not_forceable_count = _safe_int(ins.get("not_forceable_count", 0))

    label = "Forceringsvurdering" if lang == "da" else "Forcing Assessment"
    sub_text = "Kan forsinkelsen accelereres?" if lang == "da" else "Can the delay be accelerated?"
    summary_label = f'{forceable_count} {"kan forceres" if lang == "da" else "forceable"} · {not_forceable_count} {"frarådes" if lang == "da" else "not recommended"}'

    cards_html = ""
    for item in items:
        is_forceable = item.get("is_forceable", "not_recommended")
        f_style = FORCEABLE_STYLES.get(is_forceable, FORCEABLE_STYLES["not_recommended"])
        f_label = f_style[f"label_{lang}"] if f"label_{lang}" in f_style else f_style.get("label_en", is_forceable)

        constraint = item.get("constraint_type", "execution_capacity")
        c_config = CONSTRAINT_TYPE_CONFIG.get(constraint, CONSTRAINT_TYPE_CONFIG["execution_capacity"])
        c_label = c_config[f"label_{lang}"] if f"label_{lang}" in c_config else c_config.get("label_en", constraint)

        coord_cost = item.get("coordination_cost", "medium")
        parallel = item.get("parallelizability", "low")
        speedup = _e(item.get("max_speedup_factor", "1.0x"))
        team_size = _e(item.get("optimal_team_size", "N/A"))
        ponr = _e(item.get("point_of_no_return", ""))

        coord_label = {"low": ("Lav" if lang == "da" else "Low"), "medium": ("Middel" if lang == "da" else "Medium"), "high": ("Høj" if lang == "da" else "High")}.get(coord_cost, coord_cost)
        parallel_label = {"low": ("Lav" if lang == "da" else "Low"), "medium": ("Middel" if lang == "da" else "Medium"), "high": ("Høj" if lang == "da" else "High")}.get(parallel, parallel)

        coord_color = {"low": "#059669", "medium": "#d97706", "high": "#dc2626"}.get(coord_cost, "#64748b")
        parallel_color = {"low": "#dc2626", "medium": "#d97706", "high": "#059669"}.get(parallel, "#64748b")

        reason_label = "Begrundelse" if lang == "da" else "Reason"
        risk_label = "Risiko ved forcering" if lang == "da" else "Risk if Forced"
        rec_label = "Anbefaling" if lang == "da" else "Recommendation"
        ponr_label = "Point of No Return"
        coord_title = "Koordineringsomkostning" if lang == "da" else "Coordination Cost"
        parallel_title = "Paralleliserbarhed" if lang == "da" else "Parallelizability"
        speedup_title = "Maks. speedup" if lang == "da" else "Max Speedup"
        team_title = "Optimal holdstørrelse" if lang == "da" else "Optimal Team Size"

        cards_html += f'''<div style="margin:12px 0;background:#fff;border-radius:12px;border:1px solid {f_style["border"]};border-left:4px solid {f_style["color"]};overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.04);">
  <div style="padding:14px 18px;background:{f_style["bg"]};border-bottom:1px solid {f_style["border"]};">
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
      {_svg(f_style["icon"], 14, f_style["color"])}
      <span style="display:inline-block;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700;color:#134e4a;background:#f0fdfa;border:1px solid #99f6e4;font-family:'SF Mono','Cascadia Code',monospace;">ID {_e(item.get("id",""))}</span>
      <span style="font-size:13px;font-weight:700;color:#1a202c;flex:1;min-width:0;">{_e(item.get("task_name",""))}</span>
      <span style="display:inline-block;padding:3px 12px;border-radius:12px;font-size:11px;font-weight:700;color:{f_style["color"]};background:#fff;border:1px solid {f_style["border"]};white-space:nowrap;">{f_label}</span>
      <span style="display:inline-block;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:600;color:{c_config["color"]};background:#f8fafc;border:1px solid #e2e8f0;white-space:nowrap;">{_svg(c_config["icon"], 10, c_config["color"])} {c_label}</span>
    </div>
  </div>
  <div style="padding:14px 18px;">
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px;">
      <div style="padding:8px 10px;background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;text-align:center;">
        <div style="font-size:9px;color:#94a3b8;text-transform:uppercase;font-weight:700;letter-spacing:.5px;margin-bottom:3px;">{coord_title}</div>
        <div style="font-size:13px;font-weight:700;color:{coord_color};">{coord_label}</div>
      </div>
      <div style="padding:8px 10px;background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;text-align:center;">
        <div style="font-size:9px;color:#94a3b8;text-transform:uppercase;font-weight:700;letter-spacing:.5px;margin-bottom:3px;">{parallel_title}</div>
        <div style="font-size:13px;font-weight:700;color:{parallel_color};">{parallel_label}</div>
      </div>
      <div style="padding:8px 10px;background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;text-align:center;">
        <div style="font-size:9px;color:#94a3b8;text-transform:uppercase;font-weight:700;letter-spacing:.5px;margin-bottom:3px;">{speedup_title}</div>
        <div style="font-size:13px;font-weight:700;color:#0d9488;">{speedup}</div>
      </div>
      <div style="padding:8px 10px;background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;text-align:center;">
        <div style="font-size:9px;color:#94a3b8;text-transform:uppercase;font-weight:700;letter-spacing:.5px;margin-bottom:3px;">{team_title}</div>
        <div style="font-size:13px;font-weight:700;color:#1a202c;">{team_size}</div>
      </div>
    </div>
    <div style="display:flex;flex-direction:column;gap:10px;">
      <div style="padding:10px 14px;background:#f0fdfa;border-radius:8px;border:1px solid #99f6e4;">
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">{_svg("search", 12, "#0d9488")}<span style="font-size:10px;color:#0d9488;text-transform:uppercase;font-weight:700;letter-spacing:.6px;">{reason_label}</span></div>
        <div style="font-size:13px;color:#374151;line-height:1.7;">{_e(item.get("reason",""))}</div>
      </div>
      <div style="padding:10px 14px;background:#fef2f2;border-radius:8px;border:1px solid #fecaca;">
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">{_svg("alert-triangle", 12, "#dc2626")}<span style="font-size:10px;color:#dc2626;text-transform:uppercase;font-weight:700;letter-spacing:.6px;">{risk_label}</span></div>
        <div style="font-size:13px;color:#374151;line-height:1.7;">{_e(item.get("risk_if_forced",""))}</div>
      </div>
      <div style="padding:10px 14px;background:#ecfdf5;border-radius:8px;border:1px solid #6ee7b7;">
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">{_svg("check-square", 12, "#059669")}<span style="font-size:10px;color:#059669;text-transform:uppercase;font-weight:700;letter-spacing:.6px;">{rec_label}</span></div>
        <div style="font-size:13px;color:#374151;line-height:1.7;font-weight:500;">{_e(item.get("recommendation",""))}</div>
      </div>
      <div style="padding:8px 14px;background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;">
        <div style="display:flex;align-items:center;gap:6px;">{_svg("clock", 12, "#64748b")}<span style="font-size:10px;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:.6px;">{ponr_label}</span><span style="font-size:12px;color:#475569;font-weight:600;margin-left:6px;">{ponr}</span></div>
      </div>
    </div>
  </div>
</div>'''

    return f'''
<div class="module-card" style="margin:0 0 16px;padding:22px 24px;background:#fff;border-radius:14px;border:1px solid #e2e8f0;border-left:5px solid #0d9488;transition:all .2s;box-shadow:0 1px 3px rgba(0,0,0,.04);">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;padding-bottom:12px;border-bottom:1px solid #f1f5f9;">
    <div style="width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:#ea580c12;border:1px solid #ea580c22;">{_svg("zap", 18, "#ea580c")}</div>
    <div style="flex:1;"><h3 style="font-size:16px;font-weight:700;color:#1a202c;margin:0;">{label}</h3><p style="margin:0;font-size:11px;color:#94a3b8;font-weight:500;">{sub_text}</p></div>
    <span style="font-size:11px;color:#64748b;font-weight:600;background:#f1f5f9;padding:4px 12px;border-radius:8px;">{summary_label}</span>
  </div>
  {cards_html}
</div>'''


def _render_summary_by_area(data: Dict, lang: str) -> str:
    areas = data.get("summary_by_area", [])
    if not areas:
        return ""

    label = "Oversigt efter Område" if lang == "da" else "Summary by Area"

    items_html = ""
    for area in areas:
        d = area.get("delayed_count", 0)
        c = area.get("critical_count", 0)
        i_count = area.get("important_count", 0)
        m = area.get("monitor_count", 0)
        bar_color = "#dc2626" if c > 0 else ("#d97706" if d > 2 else "#0d9488")

        breakdown_parts = []
        if c > 0:
            breakdown_parts.append(f'{c} {"kritisk" if lang == "da" else "critical"}')
        if i_count > 0:
            breakdown_parts.append(f'{i_count} {"vigtig" if lang == "da" else "important"}')
        if m > 0:
            breakdown_parts.append(f'{m} {"overvåg" if lang == "da" else "monitor"}')
        breakdown = ", ".join(breakdown_parts)

        items_html += f'''<div style="display:flex;gap:14px;padding:14px 16px;margin:6px 0;background:#fff;border-radius:10px;border:1px solid #e2e8f0;border-left:4px solid {bar_color};align-items:flex-start;">
  <div style="text-align:center;flex-shrink:0;min-width:40px;"><div style="font-size:22px;font-weight:800;color:{bar_color};line-height:1;">{d}</div><div style="font-size:9px;color:#94a3b8;text-transform:uppercase;font-weight:600;letter-spacing:.5px;margin-top:2px;">{"forsinket" if lang == "da" else "delayed"}</div></div>
  <div style="flex:1;min-width:0;">
    <div style="font-size:14px;font-weight:700;color:#1a202c;margin-bottom:3px;">{_e(area.get("area",""))}</div>
    <div style="font-size:11px;color:#64748b;margin-bottom:4px;">{breakdown}</div>
    <div style="font-size:13px;color:#4a5568;line-height:1.6;">{_e(area.get("summary",""))}</div>
  </div>
</div>'''

    return f'''
<div class="module-card" style="margin:0 0 16px;padding:22px 24px;background:#fff;border-radius:14px;border:1px solid #e2e8f0;border-left:5px solid #0d9488;transition:all .2s;box-shadow:0 1px 3px rgba(0,0,0,.04);">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid #f1f5f9;">
    <div style="width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:#2563eb12;border:1px solid #2563eb22;">{_svg("grid", 18, "#2563eb")}</div>
    <h3 style="font-size:16px;font-weight:700;color:#1a202c;margin:0;">{label}</h3>
  </div>
  {items_html}
</div>'''


def format_predictive_as_html(raw_input, language: str = "en") -> str:
    if not raw_input:
        return ""

    try:
        if isinstance(raw_input, dict):
            data = raw_input
        elif isinstance(raw_input, str):
            data = json.loads(raw_input)
        else:
            return _fallback_html(str(raw_input))
    except (json.JSONDecodeError, TypeError):
        return _fallback_html(str(raw_input) if raw_input else "")

    try:
        return _build_html(data, language)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Predictive HTML formatter error: {e}")
        return _fallback_html(json.dumps(data, indent=2, ensure_ascii=False))


def _fallback_html(text: str) -> str:
    safe = _e(text)
    return f'<div style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;padding:24px;background:#fff;border-radius:16px;border:1px solid #e2e8f0;"><h2 style="color:#1a202c;margin-bottom:16px;">Nova Insight Report</h2><div style="white-space:pre-wrap;color:#4a5568;line-height:1.7;font-size:13px;">{safe}</div></div>'


def _build_html(data: Dict, lang: str) -> str:
    title = "Nova Insight — Tidsplananalyse" if lang == "da" else "Nova Insight — Schedule Analysis"
    subtitle = "Beslutningsstøtte til projektledere" if lang == "da" else "Decision support for project managers"
    footer = "Genereret af Nova Insight AI" if lang == "da" else "Generated by Nova Insight AI"

    parts = [f'''
<style>
@keyframes novaFadeIn {{ from {{ opacity:0;transform:translateY(10px); }} to {{ opacity:1;transform:translateY(0); }} }}
.nova-report .module-card {{ animation:novaFadeIn .45s ease-out backwards; }}
.nova-report .module-card:nth-child(2) {{ animation-delay:.06s; }}
.nova-report .module-card:nth-child(3) {{ animation-delay:.12s; }}
.nova-report .module-card:nth-child(4) {{ animation-delay:.18s; }}
.nova-report .module-card:nth-child(5) {{ animation-delay:.24s; }}
.nova-report .module-card:nth-child(6) {{ animation-delay:.30s; }}
.nova-report .module-card:nth-child(7) {{ animation-delay:.36s; }}
.nova-report .module-card:nth-child(8) {{ animation-delay:.42s; }}
.nova-report .module-card:nth-child(9) {{ animation-delay:.48s; }}
.nova-report .module-card:hover {{ border-color:#cbd5e1 !important;box-shadow:0 4px 16px rgba(0,0,0,.06) !important; }}
.nova-report table tr:hover {{ background:#edf2f7 !important; }}
.nova-report ::-webkit-scrollbar {{ height:6px; }}
.nova-report ::-webkit-scrollbar-track {{ background:#f1f5f9;border-radius:6px; }}
.nova-report ::-webkit-scrollbar-thumb {{ background:#cbd5e1;border-radius:6px; }}
</style>
<div class="nova-report" style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f8fafc;border-radius:20px;padding:32px;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,.06);">
  <div style="text-align:center;margin-bottom:28px;padding-bottom:24px;border-bottom:2px solid #edf2f7;">
    <div style="display:inline-flex;align-items:center;gap:14px;margin-bottom:10px;">
      <div style="width:44px;height:44px;border-radius:14px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#0d9488,#0891b2);box-shadow:0 4px 12px rgba(13,148,136,.25);">{_svg("clock", 24, "white")}</div>
      <div style="text-align:left;"><h2 style="font-size:22px;font-weight:800;color:#1a202c;margin:0;letter-spacing:-.4px;">{title}</h2><p style="font-size:12px;color:#94a3b8;margin:3px 0 0;letter-spacing:.3px;font-weight:500;">{subtitle}</p></div>
    </div>
  </div>''']

    parts.append(_render_hero(data, lang))
    parts.append(_render_management_conclusion(data, lang))
    parts.append(_render_schedule_overview(data, lang))
    parts.append(_render_delayed_table(data, lang))
    parts.append(_render_root_cause_analysis(data, lang))
    parts.append(_render_priority_actions(data, lang))
    parts.append(_render_resource_assessment(data, lang))
    parts.append(_render_forcing_assessment(data, lang))
    parts.append(_render_summary_by_area(data, lang))

    parts.append(f'''
  <div style="margin-top:12px;padding-top:16px;border-top:2px solid #edf2f7;display:flex;align-items:center;justify-content:center;gap:10px;">
    <div style="width:8px;height:8px;border-radius:50%;background:linear-gradient(135deg,#0d9488,#0891b2);box-shadow:0 0 8px rgba(13,148,136,.3);"></div>
    <span style="font-size:11px;color:#94a3b8;letter-spacing:.5px;font-weight:500;">{footer}</span>
  </div>
</div>''')

    return "\n".join(parts)
