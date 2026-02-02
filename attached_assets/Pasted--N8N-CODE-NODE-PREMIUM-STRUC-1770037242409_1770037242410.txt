// =================================================================
// N8N CODE NODE: PREMIUM STRUCTURED THREE-SECTION HTML CONVERTER
// Parses: TABLES → SUMMARY_OF_CHANGES → PROJECT_HEALTH
// Features: Grouped tasks by category, premium styling, professional icons
// =================================================================

const agentOutput = $input.first().json.output || $input.first().json.text || "";

// =================================================================
// PROFESSIONAL SVG ICONS
// =================================================================
const SVG_ICONS = {
  projectHealth: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" fill="currentColor" opacity="0.2"/>
    <path d="M12 6v6l4 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    <circle cx="12" cy="12" r="3" fill="currentColor"/>
  </svg>`,
  pulse: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M22 12h-4l-3 9L9 3l-3 9H2" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`,
  chart: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="3" y="3" width="18" height="18" rx="2" fill="currentColor" opacity="0.15"/>
    <path d="M7 17V13M12 17V7M17 17V11" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
  </svg>`,
  shield: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" fill="currentColor" opacity="0.15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M9 12l2 2 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`,
  summary: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="3" y="3" width="18" height="18" rx="2" fill="currentColor" opacity="0.15"/>
    <path d="M7 8h10M7 12h10M7 16h6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
  </svg>`,
  table: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" stroke-width="2"/>
    <path d="M3 9h18M3 15h18M9 3v18" stroke="currentColor" stroke-width="2"/>
  </svg>`,
  download: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
    <polyline points="7 10 12 15 17 10"/>
    <line x1="12" y1="15" x2="12" y2="3"/>
  </svg>`,
  added: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="10" fill="#10b981" opacity="0.15"/>
    <path d="M12 8v8M8 12h8" stroke="#10b981" stroke-width="2.5" stroke-linecap="round"/>
  </svg>`,
  removed: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="10" fill="#ef4444" opacity="0.15"/>
    <path d="M8 12h8" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round"/>
  </svg>`,
  moved: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="10" fill="#f59e0b" opacity="0.15"/>
    <path d="M8 12h8M12 8l4 4-4 4" stroke="#f59e0b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`,
  delayed: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="10" fill="#ef4444" opacity="0.15"/>
    <path d="M12 6v6l3 3" stroke="#ef4444" stroke-width="2" stroke-linecap="round"/>
  </svg>`,
  accelerated: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="10" fill="#10b981" opacity="0.15"/>
    <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" transform="scale(0.6) translate(8,8)"/>
  </svg>`,
  critical: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 2L2 22h20L12 2z" fill="#f59e0b" opacity="0.15"/>
    <path d="M12 9v4M12 17h.01" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round"/>
  </svg>`,
  risks: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="10" fill="#ef4444" opacity="0.15"/>
    <path d="M12 8v4M12 16h.01" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round"/>
  </svg>`,
  default: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="3" y="3" width="18" height="18" rx="2" fill="#06b6d4" opacity="0.15"/>
    <path d="M9 9h6M9 12h6M9 15h4" stroke="#06b6d4" stroke-width="2" stroke-linecap="round"/>
  </svg>`
};

// =================================================================
// SECTION DETECTION - PARSE THREE MANDATORY SECTIONS
// =================================================================
function parseStructuredResponse(markdown) {
  if (!markdown || typeof markdown !== 'string') {
    return { 
      tablesSection: '', 
      summarySection: '', 
      healthSection: '',
      healthData: null,
      rawText: markdown 
    };
  }

  const summaryPatterns = [
    /^##\s*SUMMARY_OF_CHANGES\s*$/im,
    /^##\s*OPSUMMERING_AF_ÆNDRINGER\s*$/im,
    /^##\s*Summary\s+of\s+Changes/im,
    /^##\s*Opsummering\s+af\s+Ændringer/im
  ];
  
  const healthPatterns = [
    /^##\s*PROJECT_HEALTH\s*$/im,
    /^##\s*PROJEKTSUNDHED\s*$/im,
    /^##\s*Project\s+Health/im,
    /^##\s*Projektsundhed/im
  ];

  let summaryStart = -1;
  let healthStart = -1;

  for (const pattern of summaryPatterns) {
    const match = markdown.match(pattern);
    if (match) {
      summaryStart = markdown.indexOf(match[0]);
      break;
    }
  }

  for (const pattern of healthPatterns) {
    const match = markdown.match(pattern);
    if (match) {
      healthStart = markdown.indexOf(match[0]);
      break;
    }
  }

  let tablesSection = '';
  let summarySection = '';
  let healthSection = '';

  if (summaryStart === -1 && healthStart === -1) {
    tablesSection = markdown;
  } else if (summaryStart !== -1 && healthStart !== -1) {
    if (summaryStart < healthStart) {
      tablesSection = markdown.substring(0, summaryStart).trim();
      summarySection = markdown.substring(summaryStart, healthStart).trim();
      healthSection = markdown.substring(healthStart).trim();
    } else {
      tablesSection = markdown.substring(0, healthStart).trim();
      healthSection = markdown.substring(healthStart, summaryStart).trim();
      summarySection = markdown.substring(summaryStart).trim();
    }
  } else if (summaryStart !== -1) {
    tablesSection = markdown.substring(0, summaryStart).trim();
    summarySection = markdown.substring(summaryStart).trim();
  } else if (healthStart !== -1) {
    tablesSection = markdown.substring(0, healthStart).trim();
    healthSection = markdown.substring(healthStart).trim();
  }

  let healthData = null;
  const healthDataMatch = healthSection.match(/<!--HEALTH_DATA:(.*?)-->/s);
  if (healthDataMatch) {
    try {
      healthData = JSON.parse(healthDataMatch[1]);
      healthSection = healthSection.replace(/<!--HEALTH_DATA:.*?-->/s, '').trim();
    } catch (e) {}
  }

  return { tablesSection, summarySection, healthSection, healthData, rawText: markdown };
}

// =================================================================
// PARSE MARKDOWN TABLES WITH ROW GROUPING BY CATEGORY
// =================================================================
function parseMarkdownTables(markdown) {
  if (!markdown || typeof markdown !== 'string') {
    return { tables: [], textSections: [], groupedData: null };
  }

  const hasTable = markdown.includes('|') && 
    markdown.split('\n').some(line => 
      line.trim().startsWith('|') && line.trim().endsWith('|')
    );

  if (!hasTable) {
    return { tables: [], textSections: [{ type: 'text', content: markdown }], groupedData: null };
  }

  const tables = [];
  const lines = markdown.split('\n');
  let currentTable = null;
  let tableIdCounter = 0;

  const flushTable = () => {
    if (currentTable && currentTable.rows.length > 0) {
      tables.push(currentTable);
      currentTable = null;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    const isSeparatorLine = line.startsWith('|') && line.endsWith('|') && 
                            line.replace(/[\|\-\s:]/g, '').length === 0;
    const isTableRow = line.startsWith('|') && line.endsWith('|') && !isSeparatorLine;
    
    const nextLines = lines.slice(i + 1, i + 4).join('\n');
    const nextHasTable = nextLines.includes('|') && 
                         nextLines.split('\n').some(l => l.trim().startsWith('|') && l.trim().endsWith('|'));

    if (isSeparatorLine) continue;
    
    if (isTableRow) {
      if (!currentTable) {
        currentTable = {
          title: 'Comparison Results',
          headers: [],
          rows: [],
          type: 'default',
          id: 'tbl' + tableIdCounter++ + 'x' + Math.floor(Math.random() * 10000)
        };
      }
      
      const cells = line.replace(/^\||\|$/g, '').split('|').map(c => c.trim());
      
      if (currentTable.headers.length === 0) {
        currentTable.headers = cells;
      } else {
        // Detect row category from content
        const rowCategory = detectRowCategory(cells);
        currentTable.rows.push({ cells, category: rowCategory });
      }
    }
    else if (line && nextHasTable && !line.startsWith('#') && !line.startsWith('*') && !line.startsWith('-')) {
      flushTable();
      currentTable = {
        title: line,
        headers: [],
        rows: [],
        type: detectTableType(line),
        id: 'tbl' + tableIdCounter++ + 'x' + Math.floor(Math.random() * 10000)
      };
    }
    else {
      flushTable();
    }
  }

  flushTable();

  // Group all rows by category for unified display
  const groupedData = groupRowsByCategory(tables);

  return { tables, textSections: [], groupedData };
}

function detectTableType(title) {
  const lower = title.toLowerCase();
  if (lower.includes('added') || lower.includes('tilføjet')) return 'added';
  if (lower.includes('removed') || lower.includes('fjernet')) return 'removed';
  if (lower.includes('moved') || lower.includes('flyttet') || lower.includes('modified') || lower.includes('ændret')) return 'moved';
  if (lower.includes('delayed') || lower.includes('forsinket')) return 'delayed';
  if (lower.includes('accelerated') || lower.includes('earlier') || lower.includes('fremskyndet')) return 'accelerated';
  if (lower.includes('critical') || lower.includes('kritisk')) return 'critical';
  if (lower.includes('risk') || lower.includes('risiko')) return 'risks';
  return 'default';
}

function detectRowCategory(cells) {
  const cellText = cells.join(' ').toLowerCase();
  if (cellText.includes('not present in new') || cellText.includes('removed') || cellText.includes('fjernet')) return 'removed';
  if (cellText.includes('not present in old') || cellText.includes('added') || cellText.includes('new') || cellText.includes('tilføjet')) return 'added';
  if (cellText.includes('moved') || cellText.includes('modified') || cellText.includes('rescheduled') || cellText.includes('flyttet') || cellText.includes('ændret')) return 'moved';
  if (cellText.includes('delayed') || cellText.includes('later') || cellText.includes('forsinket') || cellText.includes('senere')) return 'delayed';
  if (cellText.includes('earlier') || cellText.includes('accelerated') || cellText.includes('tidligere') || cellText.includes('fremskyndet')) return 'accelerated';
  if (cellText.includes('critical') || cellText.includes('kritisk')) return 'critical';
  if (cellText.includes('risk') || cellText.includes('risiko')) return 'risks';
  return 'default';
}

function groupRowsByCategory(tables) {
  if (tables.length === 0) return null;
  
  const groups = {
    removed: { rows: [], label: 'Removed Tasks', labelDa: 'Fjernede Opgaver', color: '#ef4444', bgColor: 'rgba(239, 68, 68, 0.08)' },
    added: { rows: [], label: 'Added Tasks', labelDa: 'Tilføjede Opgaver', color: '#10b981', bgColor: 'rgba(16, 185, 129, 0.08)' },
    moved: { rows: [], label: 'Modified / Moved Tasks', labelDa: 'Ændrede / Flyttede Opgaver', color: '#f59e0b', bgColor: 'rgba(245, 158, 11, 0.08)' },
    delayed: { rows: [], label: 'Delayed Tasks', labelDa: 'Forsinkede Opgaver', color: '#ef4444', bgColor: 'rgba(239, 68, 68, 0.06)' },
    accelerated: { rows: [], label: 'Accelerated Tasks', labelDa: 'Fremskyndede Opgaver', color: '#10b981', bgColor: 'rgba(16, 185, 129, 0.06)' },
    critical: { rows: [], label: 'Critical Path', labelDa: 'Kritisk Vej', color: '#f59e0b', bgColor: 'rgba(245, 158, 11, 0.06)' },
    risks: { rows: [], label: 'Risks', labelDa: 'Risici', color: '#ef4444', bgColor: 'rgba(239, 68, 68, 0.06)' },
    default: { rows: [], label: 'Other Tasks', labelDa: 'Andre Opgaver', color: '#06b6d4', bgColor: 'rgba(6, 182, 212, 0.06)' }
  };
  
  // Get unified headers from first table
  const headers = tables[0]?.headers || [];
  
  // Collect all rows into groups
  tables.forEach(table => {
    table.rows.forEach(row => {
      const category = row.category || 'default';
      if (groups[category]) {
        groups[category].rows.push(row.cells);
      } else {
        groups.default.rows.push(row.cells);
      }
    });
  });
  
  return { groups, headers };
}

// =================================================================
// GENERATE PREMIUM GROUPED TABLE HTML
// =================================================================
function generateGroupedTableHtml(groupedData) {
  if (!groupedData || !groupedData.headers || groupedData.headers.length === 0) {
    return '';
  }

  const { groups, headers } = groupedData;
  const tableId = 'unified_' + Math.floor(Math.random() * 100000);
  const dateStr = new Date().toISOString().split('T')[0];
  
  // Count total tasks
  let totalTasks = 0;
  Object.values(groups).forEach(g => totalTasks += g.rows.length);
  
  if (totalTasks === 0) return '';

  const escapeHtml = (text) => {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  };

  const getStatusBadge = (cellValue) => {
    if (!cellValue) return '<span style="color: #94a3b8;">—</span>';
    const lower = cellValue.toLowerCase().trim();
    if (lower === '—' || lower === '-' || lower === 'n/a' || lower === '') return '<span style="color: #94a3b8;">—</span>';
    if (lower.includes('added') || lower.includes('new') || lower.includes('earlier') || lower.includes('tidligere') || lower.includes('tilføjet')) 
      return `<span style="display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 600; background: rgba(16, 185, 129, 0.12); color: #059669; border: 1px solid rgba(16, 185, 129, 0.2);">${escapeHtml(cellValue)}</span>`;
    if (lower.includes('removed') || lower.includes('later') || lower.includes('senere') || lower.includes('delayed') || lower.includes('forsinket') || lower.includes('fjernet')) 
      return `<span style="display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 600; background: rgba(239, 68, 68, 0.12); color: #dc2626; border: 1px solid rgba(239, 68, 68, 0.2);">${escapeHtml(cellValue)}</span>`;
    if (lower.includes('moved') || lower.includes('modified') || lower.includes('changed') || lower.includes('ændret') || lower.includes('flyttet')) 
      return `<span style="display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 600; background: rgba(245, 158, 11, 0.12); color: #d97706; border: 1px solid rgba(245, 158, 11, 0.2);">${escapeHtml(cellValue)}</span>`;
    return `<span style="display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 600; background: rgba(100, 116, 139, 0.1); color: #475569; border: 1px solid rgba(100, 116, 139, 0.15);">${escapeHtml(cellValue)}</span>`;
  };

  const isBadgeColumn = (headerName) => {
    const lower = headerName.toLowerCase();
    return lower.includes('status') || lower.includes('difference') || lower.includes('forskel') || lower.includes('change') || lower === 'ændring';
  };
  
  const isWeekColumn = (headerName) => {
    const lower = headerName.toLowerCase();
    return lower.includes('week') || lower.includes('uge') || lower === '#';
  };

  // Collect all data for CSV export
  let allRows = [];
  Object.entries(groups).forEach(([category, group]) => {
    if (group.rows.length > 0) {
      group.rows.forEach(row => allRows.push(row));
    }
  });

  const inlineJs = `
    (function(){
      try {
        var d = document.getElementById('csvData_${tableId}');
        var f = document.getElementById('csvFilename_${tableId}');
        if(!d||!f) return;
        var j = decodeURIComponent(escape(atob(d.textContent)));
        var dt = JSON.parse(j);
        var fn = f.textContent;
        var csv = dt.map(function(r){
          return r.map(function(c){
            var v = String(c||'');
            if(v.search(/[,\\"\\n]/)!==-1) v = '"'+v.replace(/"/g,'""')+'"';
            return v;
          }).join(',');
        }).join('\\n');
        var b = new Blob(['\\uFEFF'+csv],{type:'text/csv;charset=utf-8;'});
        var u = URL.createObjectURL(b);
        var l = document.createElement('a');
        l.href = u;
        l.download = fn;
        document.body.appendChild(l);
        l.click();
        document.body.removeChild(l);
        URL.revokeObjectURL(u);
      } catch(e){ alert('CSV Error: '+e.message); }
    })()
  `.replace(/\s+/g, ' ');

  let html = `
<div class="comparison-table-container" style="margin-bottom: 32px;">
  <!-- Header Section -->
  <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; flex-wrap: wrap; gap: 16px;">
    <div style="display: flex; align-items: center; gap: 14px;">
      <div style="width: 52px; height: 52px; border-radius: 16px; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #06b6d4, #0891b2); box-shadow: 0 8px 24px rgba(6, 182, 212, 0.3);">
        <span style="color: white;">${SVG_ICONS.table}</span>
      </div>
      <div>
        <h3 style="font-size: 24px; font-weight: 800; color: #0f172a; margin: 0; letter-spacing: -0.5px;">Comparison Results</h3>
        <p style="font-size: 14px; color: #64748b; margin: 4px 0 0 0;">${totalTasks} tasks analyzed</p>
      </div>
    </div>
    
    <button type="button"
            onclick="${inlineJs}"
            style="display: inline-flex; align-items: center; gap: 10px; padding: 14px 28px; border-radius: 14px; font-weight: 600; font-size: 14px; color: white; background: linear-gradient(135deg, #00D6D6, #00B8B8); border: none; cursor: pointer; box-shadow: 0 6px 20px rgba(0, 214, 214, 0.35); transition: all 0.3s ease;"
            onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 10px 30px rgba(0, 214, 214, 0.45)';"
            onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 6px 20px rgba(0, 214, 214, 0.35)';">
      ${SVG_ICONS.download}
      <span>Export to CSV</span>
    </button>
  </div>

  <!-- Hidden CSV Data -->
  <div id="csvData_${tableId}" style="display:none;">${btoa(unescape(encodeURIComponent(JSON.stringify([headers, ...allRows]))))}</div>
  <div id="csvFilename_${tableId}" style="display:none;">comparison_results_${dateStr}.csv</div>

  <!-- Table Container -->
  <div style="position: relative; overflow: hidden; border-radius: 20px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08), 0 0 0 1px rgba(0, 214, 214, 0.15); background: #ffffff;">
    
    <div class="table-scroll" style="overflow-x: auto;">
      <table style="width: 100%; min-width: 700px; border-collapse: separate; border-spacing: 0;">
        <!-- Premium Header -->
        <thead>
          <tr style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%);">`;

  headers.forEach((header, idx) => {
    const isLast = idx === headers.length - 1;
    html += `
            <th style="padding: 18px 20px; text-align: left; font-size: 11px; font-weight: 700; color: rgba(255,255,255,0.95); text-transform: uppercase; letter-spacing: 1.2px; ${!isLast ? 'border-right: 1px solid rgba(255,255,255,0.08);' : ''} white-space: nowrap; position: relative;">
              ${escapeHtml(header)}
              <div style="position: absolute; bottom: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #00D6D6, #06b6d4);"></div>
            </th>`;
  });

  html += `
          </tr>
        </thead>
        <tbody>`;

  // Render each category group
  const categoryOrder = ['removed', 'added', 'delayed', 'accelerated', 'moved', 'critical', 'risks', 'default'];
  
  categoryOrder.forEach(category => {
    const group = groups[category];
    if (group && group.rows.length > 0) {
      // Category separator row
      html += `
          <tr class="category-header" style="background: ${group.bgColor};">
            <td colspan="${headers.length}" style="padding: 14px 20px; border-bottom: 2px solid ${group.color}30;">
              <div style="display: flex; align-items: center; gap: 10px;">
                <span style="color: ${group.color};">${SVG_ICONS[category] || SVG_ICONS.default}</span>
                <span style="font-size: 14px; font-weight: 700; color: ${group.color}; text-transform: uppercase; letter-spacing: 0.8px;">${group.label}</span>
                <span style="padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; background: ${group.color}20; color: ${group.color};">${group.rows.length}</span>
              </div>
            </td>
          </tr>`;
      
      // Data rows for this category
      group.rows.forEach((row, rowIdx) => {
        const rowBg = rowIdx % 2 === 0 ? '#ffffff' : 'rgba(248, 250, 252, 0.8)';
        html += `
          <tr class="data-row" style="background: ${rowBg}; border-left: 4px solid transparent; transition: all 0.2s ease;">`;
        
        row.forEach((cell, cellIdx) => {
          const headerName = headers[cellIdx] || '';
          const isLast = cellIdx === row.length - 1;
          let cellContent = '';
          
          if (cellIdx === 0) {
            cellContent = `<span style="color: #1e293b; font-weight: 600;">${escapeHtml(cell || 'N/A')}</span>`;
          }
          else if (isBadgeColumn(headerName)) {
            cellContent = getStatusBadge(cell);
          }
          else if (isWeekColumn(headerName)) {
            if (!cell || cell === '—' || cell === '-') {
              cellContent = '<span style="color: #94a3b8;">—</span>';
            } else {
              cellContent = `<span style="display: inline-block; padding: 6px 14px; border-radius: 8px; font-weight: 600; background: linear-gradient(135deg, #e0f7f7, #d1fae5); color: #0e7490; font-size: 13px; border: 1px solid rgba(6, 182, 212, 0.2);">${escapeHtml(cell)}</span>`;
            }
          }
          else {
            cellContent = `<span style="color: #475569; font-size: 14px;">${escapeHtml(cell || 'N/A')}</span>`;
          }
          
          html += `
            <td style="padding: 16px 20px; font-size: 14px; ${!isLast ? 'border-right: 1px solid #f1f5f9;' : ''} border-bottom: 1px solid #f1f5f9; vertical-align: middle;">${cellContent}</td>`;
        });
        
        html += `
          </tr>`;
      });
    }
  });

  html += `
        </tbody>
      </table>
    </div>

    <!-- Footer -->
    <div style="padding: 16px 24px; border-top: 1px solid rgba(0, 214, 214, 0.1); background: linear-gradient(135deg, rgba(240, 253, 250, 0.8), rgba(224, 247, 247, 0.6)); display: flex; justify-content: space-between; align-items: center;">
      <div style="display: flex; align-items: center; gap: 16px;">
        <span style="font-size: 14px; color: #475569; font-weight: 500;">Total: ${totalTasks} tasks</span>
      </div>
      <span style="font-size: 12px; color: #94a3b8;">Generated: ${new Date().toLocaleString()}</span>
    </div>
  </div>
</div>

<style>
  .comparison-table-container .data-row:hover {
    background: rgba(0, 214, 214, 0.06) !important;
    border-left: 4px solid #00D6D6 !important;
  }
  .comparison-table-container .data-row {
    cursor: default;
  }
  .comparison-table-container .table-scroll::-webkit-scrollbar {
    height: 10px;
  }
  .comparison-table-container .table-scroll::-webkit-scrollbar-track {
    background: rgba(0, 214, 214, 0.05);
    border-radius: 10px;
  }
  .comparison-table-container .table-scroll::-webkit-scrollbar-thumb {
    background: linear-gradient(135deg, #00D6D6, #00B8B8);
    border-radius: 10px;
  }
</style>`;

  return html;
}

// =================================================================
// GENERATE HTML FOR SUMMARY SECTION (SECTION 2)
// =================================================================
function generateSummaryHtml(summaryContent) {
  if (!summaryContent || !summaryContent.trim()) return '';
  
  const escapeHtml = (text) => {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  };

  const lines = summaryContent.split('\n');
  let processedLines = [];
  let listItems = [];

  const flushList = () => {
    if (listItems.length > 0) {
      processedLines.push('<ul style="margin: 12px 0; padding-left: 0; color: #334155; list-style: none;">');
      listItems.forEach(item => {
        processedLines.push(`<li style="margin: 10px 0; line-height: 1.6; padding-left: 24px; position: relative;"><span style="position: absolute; left: 0; color: #8b5cf6; font-size: 18px;">•</span>${item}</li>`);
      });
      processedLines.push('</ul>');
      listItems = [];
    }
  };

  for (let line of lines) {
    const trimmedLine = line.trim();
    
    if (!trimmedLine || trimmedLine === '---' || trimmedLine === '***') {
      flushList();
      continue;
    }
    
    if (trimmedLine.match(/^##\s*(SUMMARY_OF_CHANGES|OPSUMMERING_AF_ÆNDRINGER|Summary|Opsummering)/i)) {
      flushList();
      const isEnglish = trimmedLine.toLowerCase().includes('summary');
      const headerText = isEnglish ? 'Summary of Changes' : 'Opsummering af Ændringer';
      processedLines.push(`
        <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 24px;">
          <div style="width: 52px; height: 52px; border-radius: 16px; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #8b5cf6, #7c3aed); box-shadow: 0 8px 24px rgba(139, 92, 246, 0.3);">
            <span style="color: white;">${SVG_ICONS.summary}</span>
          </div>
          <h2 style="font-size: 24px; font-weight: 800; color: #0f172a; margin: 0; letter-spacing: -0.5px;">${headerText}</h2>
        </div>
      `);
      continue;
    }
    
    const boldHeaderMatch = trimmedLine.match(/^\*\*([^*]+):\*\*$/) || trimmedLine.match(/^\*\*([^*]+)\*\*$/);
    if (boldHeaderMatch) {
      flushList();
      const headerText = boldHeaderMatch[1].replace(/:$/, '');
      processedLines.push(`
        <h3 style="font-size: 15px; font-weight: 700; color: #7c3aed; margin: 24px 0 12px 0; padding-bottom: 8px; border-bottom: 2px solid rgba(139, 92, 246, 0.15); text-transform: uppercase; letter-spacing: 0.5px;">${escapeHtml(headerText)}</h3>
      `);
      continue;
    }
    
    if (trimmedLine.startsWith('• ') || trimmedLine.startsWith('* ') || trimmedLine.startsWith('- ')) {
      let itemText = trimmedLine.substring(2);
      itemText = itemText.replace(/\*\*([^*]+)\*\*/g, '<strong style="color: #6d28d9; font-weight: 600;">$1</strong>');
      listItems.push(itemText);
      continue;
    }
    
    flushList();
    let paragraphText = escapeHtml(trimmedLine);
    paragraphText = paragraphText.replace(/\*\*([^*]+)\*\*/g, '<strong style="color: #6d28d9; font-weight: 600;">$1</strong>');
    processedLines.push(`<p style="margin: 12px 0; color: #334155; line-height: 1.7; font-size: 15px;">${paragraphText}</p>`);
  }
  
  flushList();

  return `
    <div class="summary-section" style="margin: 32px 0; padding: 28px; background: linear-gradient(135deg, rgba(139, 92, 246, 0.06), rgba(124, 58, 237, 0.02)); border-radius: 20px; box-shadow: 0 4px 24px rgba(139, 92, 246, 0.08), 0 0 0 1px rgba(139, 92, 246, 0.1);">
      ${processedLines.join('\n')}
    </div>
  `;
}

// =================================================================
// GENERATE HTML FOR PROJECT HEALTH SECTION (SECTION 3)
// =================================================================
function generateHealthHtml(healthContent, healthData) {
  if (!healthContent || !healthContent.trim()) return '';
  
  const escapeHtml = (text) => {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  };

  let status = 'stable';
  let statusColor = '#10b981';
  let statusBg = 'rgba(16, 185, 129, 0.12)';
  let statusBorder = 'rgba(16, 185, 129, 0.25)';
  let statusLabel = 'Stable';

  if (healthData && healthData.status) {
    status = healthData.status;
  } else if (healthContent.toLowerCase().includes('high risk') || healthContent.toLowerCase().includes('høj risiko')) {
    status = 'high_risk';
  } else if (healthContent.toLowerCase().includes('attention') || healthContent.toLowerCase().includes('opmærksomhed')) {
    status = 'attention';
  }

  if (status === 'high_risk') {
    statusColor = '#ef4444';
    statusBg = 'rgba(239, 68, 68, 0.12)';
    statusBorder = 'rgba(239, 68, 68, 0.25)';
    statusLabel = healthContent.includes('Høj') ? 'Høj Risiko' : 'High Risk';
  } else if (status === 'attention') {
    statusColor = '#f59e0b';
    statusBg = 'rgba(245, 158, 11, 0.12)';
    statusBorder = 'rgba(245, 158, 11, 0.25)';
    statusLabel = healthContent.includes('Opmærksomhed') ? 'Kræver Opmærksomhed' : 'Attention Needed';
  } else {
    statusLabel = healthContent.includes('Stabil') ? 'Stabil' : 'Stable';
  }

  const lines = healthContent.split('\n');
  let processedLines = [];
  let listItems = [];

  const flushList = () => {
    if (listItems.length > 0) {
      processedLines.push('<ul style="margin: 12px 0; padding-left: 0; color: #334155; list-style: none;">');
      listItems.forEach(item => {
        processedLines.push(`<li style="margin: 10px 0; line-height: 1.6; padding-left: 24px; position: relative;"><span style="position: absolute; left: 0; color: ${statusColor}; font-size: 18px;">•</span>${item}</li>`);
      });
      processedLines.push('</ul>');
      listItems = [];
    }
  };

  for (let line of lines) {
    const trimmedLine = line.trim();
    
    if (!trimmedLine || trimmedLine === '---') {
      flushList();
      continue;
    }
    
    if (trimmedLine.match(/^##\s*(PROJECT_HEALTH|PROJEKTSUNDHED|Project\s+Health|Projektsundhed)/i)) {
      flushList();
      const isEnglish = trimmedLine.toLowerCase().includes('project');
      const headerText = isEnglish ? 'Project Health' : 'Projektsundhed';
      processedLines.push(`
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 28px; flex-wrap: wrap; gap: 20px;">
          <div style="display: flex; align-items: center; gap: 14px;">
            <div style="width: 52px; height: 52px; border-radius: 16px; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, ${statusColor}, ${statusColor}cc); box-shadow: 0 8px 24px ${statusColor}40;">
              <span style="color: white;">${SVG_ICONS.pulse}</span>
            </div>
            <h2 style="font-size: 24px; font-weight: 800; color: #0f172a; margin: 0; letter-spacing: -0.5px;">${headerText}</h2>
          </div>
          <div style="display: flex; align-items: center; gap: 12px; padding: 12px 24px; border-radius: 50px; background: ${statusBg}; border: 2px solid ${statusBorder};">
            <div style="width: 12px; height: 12px; border-radius: 50%; background: ${statusColor}; box-shadow: 0 0 8px ${statusColor}80;"></div>
            <span style="font-size: 15px; font-weight: 700; color: ${statusColor};">${statusLabel}</span>
          </div>
        </div>
      `);
      continue;
    }
    
    if (trimmedLine.match(/^\*\*Status:\*\*/i)) continue;
    
    const boldHeaderMatch = trimmedLine.match(/^\*\*([^*]+):\*\*$/) || trimmedLine.match(/^\*\*([^*]+)\*\*$/);
    if (boldHeaderMatch) {
      flushList();
      const headerText = boldHeaderMatch[1].replace(/:$/, '');
      processedLines.push(`
        <h3 style="font-size: 15px; font-weight: 700; color: ${statusColor}; margin: 24px 0 12px 0; padding-bottom: 8px; border-bottom: 2px solid ${statusColor}20; text-transform: uppercase; letter-spacing: 0.5px;">${escapeHtml(headerText)}</h3>
      `);
      continue;
    }
    
    if (trimmedLine.startsWith('• ') || trimmedLine.startsWith('* ') || trimmedLine.startsWith('- ')) {
      let itemText = trimmedLine.substring(2);
      itemText = itemText.replace(/\*\*([^*]+)\*\*/g, '<strong style="font-weight: 600;">$1</strong>');
      listItems.push(itemText);
      continue;
    }
    
    flushList();
    let paragraphText = escapeHtml(trimmedLine);
    paragraphText = paragraphText.replace(/\*\*([^*]+)\*\*/g, '<strong style="font-weight: 600;">$1</strong>');
    processedLines.push(`<p style="margin: 12px 0; color: #334155; line-height: 1.7; font-size: 15px;">${paragraphText}</p>`);
  }
  
  flushList();

  let metricsHtml = '';
  if (healthData) {
    metricsHtml = `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 12px; margin-top: 24px; padding-top: 24px; border-top: 2px solid ${statusColor}15;">
        ${healthData.delayed_count !== undefined ? `
          <div style="text-align: center; padding: 16px 12px; background: linear-gradient(135deg, rgba(239, 68, 68, 0.08), rgba(239, 68, 68, 0.03)); border-radius: 14px; border: 1px solid rgba(239, 68, 68, 0.12);">
            <div style="font-size: 28px; font-weight: 800; color: #ef4444; letter-spacing: -1px;">${healthData.delayed_count}</div>
            <div style="font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: 0.8px; margin-top: 4px; font-weight: 600;">Delayed</div>
          </div>
        ` : ''}
        ${healthData.accelerated_count !== undefined ? `
          <div style="text-align: center; padding: 16px 12px; background: linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(16, 185, 129, 0.03)); border-radius: 14px; border: 1px solid rgba(16, 185, 129, 0.12);">
            <div style="font-size: 28px; font-weight: 800; color: #10b981; letter-spacing: -1px;">${healthData.accelerated_count}</div>
            <div style="font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: 0.8px; margin-top: 4px; font-weight: 600;">Accelerated</div>
          </div>
        ` : ''}
        ${healthData.added_count !== undefined ? `
          <div style="text-align: center; padding: 16px 12px; background: linear-gradient(135deg, rgba(6, 182, 212, 0.08), rgba(6, 182, 212, 0.03)); border-radius: 14px; border: 1px solid rgba(6, 182, 212, 0.12);">
            <div style="font-size: 28px; font-weight: 800; color: #06b6d4; letter-spacing: -1px;">${healthData.added_count}</div>
            <div style="font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: 0.8px; margin-top: 4px; font-weight: 600;">Added</div>
          </div>
        ` : ''}
        ${healthData.removed_count !== undefined ? `
          <div style="text-align: center; padding: 16px 12px; background: linear-gradient(135deg, rgba(245, 158, 11, 0.08), rgba(245, 158, 11, 0.03)); border-radius: 14px; border: 1px solid rgba(245, 158, 11, 0.12);">
            <div style="font-size: 28px; font-weight: 800; color: #f59e0b; letter-spacing: -1px;">${healthData.removed_count}</div>
            <div style="font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: 0.8px; margin-top: 4px; font-weight: 600;">Removed</div>
          </div>
        ` : ''}
        ${healthData.impact_score !== undefined ? `
          <div style="text-align: center; padding: 16px 12px; background: linear-gradient(135deg, ${statusBg}, ${statusColor}05); border-radius: 14px; border: 1px solid ${statusBorder};">
            <div style="font-size: 28px; font-weight: 800; color: ${statusColor}; letter-spacing: -1px;">${healthData.impact_score}</div>
            <div style="font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: 0.8px; margin-top: 4px; font-weight: 600;">Impact</div>
          </div>
        ` : ''}
      </div>
    `;
  }

  return `
    <div class="health-section" style="margin: 32px 0; padding: 28px; background: linear-gradient(135deg, ${statusBg}, ${statusColor}04); border-radius: 20px; box-shadow: 0 4px 24px ${statusColor}10, 0 0 0 1px ${statusBorder};">
      ${processedLines.join('\n')}
      ${metricsHtml}
    </div>
  `;
}

// =================================================================
// MAIN EXECUTION
// =================================================================
const structured = parseStructuredResponse(agentOutput);
const tablesParsed = parseMarkdownTables(structured.tablesSection);

if (!tablesParsed.groupedData && !structured.summarySection && !structured.healthSection) {
  return [{
    json: {
      output: agentOutput,
      isHtmlTable: false,
      tableCount: 0,
      hasSummary: false,
      hasHealth: false
    }
  }];
}

let fullHtml = `
<div style="font-family: 'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, system-ui, sans-serif; padding: 24px; background: linear-gradient(160deg, #f8fafc 0%, #e0f7f7 40%, #f0fdfa 100%); border-radius: 24px; min-height: 200px;">
`;

// SECTION 1: Grouped Comparison Tables
if (tablesParsed.groupedData) {
  fullHtml += generateGroupedTableHtml(tablesParsed.groupedData);
}

// SECTION 2: Summary of Changes
if (structured.summarySection) {
  fullHtml += generateSummaryHtml(structured.summarySection);
}

// SECTION 3: Project Health
if (structured.healthSection) {
  fullHtml += generateHealthHtml(structured.healthSection, structured.healthData);
}

fullHtml += `
</div>`;

return [{
  json: {
    output: fullHtml,
    isHtmlTable: true,
    tableCount: tablesParsed.tables.length,
    hasSummary: !!structured.summarySection,
    hasHealth: !!structured.healthSection,
    healthData: structured.healthData,
    originalOutput: agentOutput
  }
}];
