/* =========================================================
   Relational Algebra Explorer — script.js
   ========================================================= */

// ── Element refs ──────────────────────────────────────────────────────────
const form        = document.getElementById('ra-form');
const queryEl     = document.getElementById('ra-query');
const sqlOut      = document.getElementById('sql-output');
const rowsTable   = document.getElementById('rows-table');
const runBtn      = document.getElementById('run-btn');
const clearBtn    = document.getElementById('clear-btn');
const loadingEl   = document.getElementById('loading');
const errorBanner = document.getElementById('error');
const errorText   = document.getElementById('error-text');
const resultSec   = document.getElementById('result');
const rowCount    = document.getElementById('row-count');
const copySqlBtn  = document.getElementById('copy-sql-btn');
const toast       = document.getElementById('toast');
const dbBadge     = document.getElementById('db-badge');
const tablesList  = document.getElementById('tables-list');
const dbSelect    = document.getElementById('db-select');
const uploadBtn   = document.getElementById('upload-db-btn');
const fileInput   = document.getElementById('db-file-input');
const queryTitle  = document.getElementById('query-title');
const treeContainer = document.getElementById('tree-container');
const nodePopup   = document.getElementById('node-popup');
const popupLabel  = document.getElementById('popup-label');
const popupRowCount = document.getElementById('popup-rowcount');
const popupBody   = document.getElementById('popup-body');
// The popup is position:fixed; keep it out of animated/transformed cards,
// otherwise it is positioned relative to the card instead of the window.
document.body.appendChild(nodePopup);

// ── Helpers ───────────────────────────────────────────────────────────────

function showError(msg) {
  errorText.textContent = msg;
  errorBanner.classList.remove('hidden');
}

function hideError() {
  errorBanner.classList.add('hidden');
}

function setLoading(on) {
  runBtn.disabled = on;
  if (on) {
    loadingEl.classList.remove('hidden');
  } else {
    loadingEl.classList.add('hidden');
  }
}

function showToast(msg) {
  toast.textContent = msg;
  toast.classList.remove('hidden');
  // trigger transition
  requestAnimationFrame(() => {
    requestAnimationFrame(() => toast.classList.add('show'));
  });
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.classList.add('hidden'), 300);
  }, 2000);
}

// ── Symbol palette: insert symbol at caret ───────────────────────────────
document.querySelectorAll('.sym-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const sym = btn.dataset.sym;
    const start = queryEl.selectionStart;
    const end   = queryEl.selectionEnd;
    const val   = queryEl.value;
    queryEl.value = val.slice(0, start) + sym + val.slice(end);
    queryEl.selectionStart = queryEl.selectionEnd = start + sym.length;
    queryEl.focus();
  });
});

// ── Examples: click to fill textarea ─────────────────────────────────────
const examplesList = document.getElementById('examples');
if (examplesList) {
  examplesList.addEventListener('click', ev => {
    const li = ev.target.closest('li');
    if (li && li.dataset.query) {
      queryEl.value = li.dataset.query;
      queryEl.focus();
      hideError();
    }
  });
}

// ── Clear button ──────────────────────────────────────────────────────────
clearBtn.addEventListener('click', () => {
  queryEl.value = '';
  hideError();
  resultSec.classList.add('hidden');
  queryEl.focus();
});

// ── Copy SQL ──────────────────────────────────────────────────────────────
copySqlBtn.addEventListener('click', () => {
  const sql = sqlOut.textContent;
  if (!sql) return;
  navigator.clipboard.writeText(sql).then(() => showToast('Copied to clipboard!'));
});

// ── Load available tables on startup ─────────────────────────────────────
async function loadTables() {
  const dbName = dbSelect.value;
  try {
    const resp = await fetch('/tables', {
      headers: { 'X-DB-Name': dbName }
    });
    if (!resp.ok) return;
    const data = await resp.json();
    tablesList.innerHTML = '';
    if (data.tables && data.tables.length) {
      data.tables.forEach(name => {
        const li = document.createElement('li');
        li.textContent = name;
        tablesList.appendChild(li);
      });
      // show connected badge
      dbBadge.classList.remove('hidden');
    } else {
      tablesList.innerHTML = '<li class="loading-text">No tables found</li>';
    }
  } catch (e) {
    tablesList.innerHTML = '<li class="loading-text">Could not load tables</li>';
  }
}

// ── Database Handling ─────────────────────────────────────────────────────

async function loadDatabases() {
  try {
    const resp = await fetch('/databases');
    if (!resp.ok) return;
    const data = await resp.json();
    
    // Remember current selection
    const current = dbSelect.value;
    dbSelect.innerHTML = '';
    
    data.databases.forEach(db => {
      const opt = document.createElement('option');
      opt.value = db;
      opt.textContent = db;
      dbSelect.appendChild(opt);
    });
    
    // Restore selection if still exists
    if (data.databases.includes(current)) {
      dbSelect.value = current;
    }
  } catch(e) {
    console.error("Could not load databases");
  }
}

dbSelect.addEventListener('change', () => {
  resultSec.classList.add('hidden');
  hideError();
  lastQuery = '';
  loadTables();
  loadSchema();
});

uploadBtn.addEventListener('click', () => {
  fileInput.click();
});

fileInput.addEventListener('change', async (e) => {
  if (!e.target.files.length) return;
  const file = e.target.files[0];
  
  const formData = new FormData();
  formData.append("file", file);
  
  try {
    const resp = await fetch('/upload-db', {
      method: "POST",
      body: formData
    });
    
    if (resp.ok) {
      showToast("Uploaded successfully!");
      await loadDatabases();
      dbSelect.value = file.name;
      loadTables();
      loadSchema();
    } else {
      const data = await resp.json();
      showError(data.error || "Upload failed");
    }
  } catch (err) {
    showError("Upload failed: " + err.message);
  }
});

// Init
loadDatabases();
loadTables();
loadSchema();

// ── Schema accordion ────────────────────────────────────────────────────
const schemaToggle = document.getElementById('schema-toggle');
const schemaBody   = document.getElementById('schema-body');
const schemaList   = document.getElementById('schema-list');

if (schemaToggle) {
  schemaToggle.addEventListener('click', () => {
    const open = schemaToggle.getAttribute('aria-expanded') === 'true';
    schemaToggle.setAttribute('aria-expanded', open ? 'false' : 'true');
    schemaBody.classList.toggle('collapsed', open);
  });
}

async function loadSchema() {
  const sl = document.getElementById('schema-list');
  if (!sl) return;
  const dbName = dbSelect ? dbSelect.value : 'database.db';
  try {
    const resp = await fetch('/schema', { headers: { 'X-DB-Name': dbName } });
    const data = await resp.json();
    if (data.error || !data.tables) {
      sl.innerHTML = '<div class="loading-text">Schema unavailable</div>';
      return;
    }
    renderSchema(data.tables, sl);
    renderER(data.tables);
  } catch(e) {
    sl.innerHTML = '<div class="loading-text">Failed to load</div>';
  }
}

function renderSchema(tables, sl) {
  if (!sl) sl = document.getElementById('schema-list');
  sl.innerHTML = '';

  if (!tables.length) {
    sl.innerHTML = '<div class="loading-text">No tables found</div>';
    return;
  }
  tables.forEach(tbl => {
    const group = document.createElement('div');
    group.className = 'schema-table-group';

    // Table header row — click inserts table name
    const header = document.createElement('div');
    header.className = 'schema-table-name';
    header.innerHTML = `${esc(tbl.name)} <span class="tbl-arrow">▶</span>`;

    header.addEventListener('click', (e) => {
      // Toggle columns
      cols.classList.toggle('open');
      header.classList.toggle('open');
      // Insert table name into editor on click
      insertAtCursor(queryEl, tbl.name);
    });

    // Columns list
    const cols = document.createElement('div');
    cols.className = 'schema-cols';

    tbl.columns.forEach(col => {
      const item = document.createElement('div');
      item.className = 'schema-col-item';
      item.innerHTML =
        `<span class="schema-col-name">${esc(col.name)}</span>` +
        `<span class="schema-col-type">${esc(col.type)}</span>`;
      item.addEventListener('click', () => insertAtCursor(queryEl, col.name));
      cols.appendChild(item);
    });

    group.appendChild(header);
    group.appendChild(cols);
    sl.appendChild(group);
  });
}


/** Insert text at the current cursor position in a textarea */
function insertAtCursor(el, text) {
  el.focus();
  const start = el.selectionStart;
  const end   = el.selectionEnd;
  el.value = el.value.slice(0, start) + text + el.value.slice(end);
  el.selectionStart = el.selectionEnd = start + text.length;
  el.dispatchEvent(new Event('input'));
}

// ── Render result rows as <table> ─────────────────────────────────────────
function renderTable(rows, colNames) {
  rowsTable.innerHTML = '';

  if (!Array.isArray(rows) || rows.length === 0) {
    rowsTable.innerHTML = '<tr><td><em>(no rows returned)</em></td></tr>';
    rowCount.textContent = '0 rows';
    return;
  }

  // Header
  const thead = document.createElement('thead');
  const headerRow = document.createElement('tr');
  const cols = colNames && colNames.length ? colNames : rows[0].map((_, i) => 'col ' + (i + 1));
  cols.forEach(name => {
    const th = document.createElement('th');
    th.textContent = name;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  rowsTable.appendChild(thead);

  // Body
  const tbody = document.createElement('tbody');
  rows.forEach(row => {
    const tr = document.createElement('tr');
    row.forEach(cell => {
      const td = document.createElement('td');
      td.textContent = (cell === null || cell === undefined) ? 'NULL' : cell;
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  rowsTable.appendChild(tbody);

  rowCount.textContent = rows.length + ' row' + (rows.length === 1 ? '' : 's');
}

// ── Form submit: send query to Flask /query ───────────────────────────────
form.addEventListener('submit', async ev => {
  ev.preventDefault();
  hideError();
  resultSec.classList.add('hidden');

  let raw = queryEl.value.trim();
  if (!raw) {
    showError('Please enter a relational algebra expression.');
    return;
  }

  setLoading(true);

  try {
    const dbName = dbSelect.value;

    // SQL typed into the editor → translate it to relational algebra first
    if (/^\s*\(?\s*select\b/i.test(raw)) {
      const tr = await fetch('/sql-to-ra', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-DB-Name': dbName },
        body: JSON.stringify({ sql: raw })
      });
      const td = await tr.json();
      if (td.error) throw new Error('This looks like SQL, but it could not be converted: ' + td.error);
      if (sqlInput) sqlInput.value = raw;
      raw = td.ra;
      queryEl.value = raw;
      showToast('SQL detected: converted to relational algebra');
    }

    const resp = await fetch('/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-DB-Name': dbName
      },
      body: JSON.stringify({ query: raw }),
    });

    let data;
    const ctype = resp.headers.get('content-type') || '';
    if (ctype.includes('application/json')) {
      data = await resp.json();
    } else {
      const txt = await resp.text();
      throw new Error('Unexpected server response: ' + txt.slice(0, 200));
    }

    if (!resp.ok) {
      throw new Error(data.error || ('Server error ' + resp.status));
    }

    if (data.error) {
      throw new Error(data.error);
    }

    // Show SQL
    sqlOut.textContent = data.sql;
    const engOut = document.getElementById('sql-english');
    if (engOut) engOut.textContent = data.explanation || '';

    // Show query title above results table
    if (queryTitle) queryTitle.textContent = '\u25b6 ' + raw;

    // Show rows
    renderTable(data.rows, data.columns || []);

    resultSec.classList.remove('hidden');

    // Fetch and render expression tree (non-blocking)
    fetchAndRenderTree(raw);
    lastQuery = raw;
    resetOptimizer();

  } catch (err) {
    showError(err.message);
  } finally {
    setLoading(false);
  }
});

// ── Auto-resize textarea as user types ───────────────────────────────────
queryEl.addEventListener('input', () => {
  queryEl.style.height = 'auto';
  queryEl.style.height = Math.min(queryEl.scrollHeight, 280) + 'px';
});

// ── ER Diagram Modal ─────────────────────────────────────────────────────
const erDiagram = document.querySelector('.er-diagram');
const erModal = document.getElementById('er-modal');
const modalBody = document.getElementById('modal-er-body');
const closeModal = document.querySelector('.close-modal');

if (erDiagram && erModal) {
  erDiagram.addEventListener('click', () => {
    const svg = erDiagram.querySelector('svg');
    if (svg) {
      modalBody.innerHTML = '';
      const cloned = svg.cloneNode(true);
      cloned.style.maxHeight = '80vh';
      cloned.style.maxWidth = '90vw';
      cloned.style.height = 'auto';
      cloned.style.width = '100%';
      modalBody.appendChild(cloned);
      erModal.classList.remove('hidden');
    }
  });

  closeModal.addEventListener('click', () => {
    erModal.classList.add('hidden');
  });

  erModal.addEventListener('click', (e) => {
    if (e.target === erModal) {
      erModal.classList.add('hidden');
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
//  EXPRESSION TREE RENDERER
// ═══════════════════════════════════════════════════════════════════════════

async function fetchAndRenderTree(rawQuery) {
  if (!treeContainer) return;
  treeContainer.innerHTML = '<div style="color:var(--muted);font-size:.8rem;padding:8px">Building tree…</div>';

  try {
    const dbName = dbSelect ? dbSelect.value : 'database.db';
    const resp = await fetch('/query-tree', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-DB-Name': dbName
      },
      body: JSON.stringify({ query: rawQuery })
    });
    const data = await resp.json();
    if (data.error) {
      treeContainer.innerHTML = `<div style="color:var(--error);font-size:.8rem;padding:8px">Tree error: ${esc(data.error)}</div>`;
      return;
    }
    const els = renderTree(data.tree);
    setupStepper(data.tree, els);
    if (treeCost) treeCost.textContent = data.totalCost != null ? 'est. cost ' + fmtNum(data.totalCost) : '';
  } catch (e) {
    treeContainer.innerHTML = '<div style="color:var(--muted);font-size:.8rem;padding:8px">Could not load tree.</div>';
  }
}

// ── Flatten tree into BFS levels ─────────────────────────────────────────
function treeToLevels(root) {
  const levels = [];
  let current = [root];
  while (current.length) {
    levels.push(current);
    const next = [];
    current.forEach(n => (n.children || []).forEach(c => next.push(c)));
    current = next;
  }
  return levels;  // levels[0] = root, levels[last] = leaves
}

// ── Render tree into #tree-container ─────────────────────────────────────
function renderTree(root, container = treeContainer) {
  if (!root) { container.innerHTML = ''; return new Map(); }

  container.innerHTML = '';

  // Wrapper — we'll insert an SVG overlay for lines
  const wrapper = document.createElement('div');
  wrapper.style.cssText = 'position:relative; display:inline-block; min-width:100%; padding-bottom:8px;';

  // Outer flex column (root at top)
  const col = document.createElement('div');
  col.className = 'tree-levels';
  col.style.flexDirection = 'column'; // root → leaves top-down

  const levels = treeToLevels(root);
  const nodeEls = new Map();      // node object → DOM element

  levels.forEach((level, li) => {
    const row = document.createElement('div');
    row.className = 'tree-level';

    level.forEach(node => {
      const isLeaf = !node.children || node.children.length === 0;
      const el = document.createElement('div');
      el.className = 'tree-node';

      const box = document.createElement('div');
      box.className = 'tree-node-box' + (isLeaf ? ' node-leaf' : '');

      const lbl = document.createElement('div');
      lbl.className = 'tree-node-label';
      lbl.textContent = node.label;
      lbl.title = node.label;

      const rows = document.createElement('div');
      rows.className = 'tree-node-rows';
      rows.textContent = node.rowCount + ' row' + (node.rowCount !== 1 ? 's' : '');

      box.appendChild(lbl);
      box.appendChild(rows);
      if (node.estRows !== null && node.estRows !== undefined) {
        const est = document.createElement('div');
        est.className = 'tree-node-est';
        est.textContent = 'est ' + fmtNum(node.estRows) + ' · cost ' + fmtNum(node.cost);
        est.title = node.formula || '';
        box.appendChild(est);
      }
      el.appendChild(box);
      row.appendChild(el);

      nodeEls.set(node, el);

      // Hover popup
      box.addEventListener('mouseenter', (e) => showNodePopup(e, node));
      box.addEventListener('mousemove',  (e) => positionPopup(e));
      box.addEventListener('mouseleave', hideNodePopup);

      // Click → show this node's result in Query Results panel
      box.addEventListener('click', () => {
        // Remove active from all boxes
        container.querySelectorAll('.tree-node-box').forEach(b => b.classList.remove('node-active'));
        box.classList.add('node-active');

        // Show full result (up to all preview rows we have)
        if (node.columns && node.columns.length > 0) {
          if (queryTitle) {
            queryTitle.textContent = '▶ [Node] ' + node.label;
          }
          renderTable(node.preview || [], node.columns);
          rowCount.textContent = node.rowCount + ' row' + (node.rowCount !== 1 ? 's' : '');
          resultSec.classList.remove('hidden');
          // Scroll to results
          resultSec.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    });

    col.appendChild(row);
  });

  wrapper.appendChild(col);
  container.appendChild(wrapper);

  // Draw SVG connector lines after layout
  requestAnimationFrame(() => drawLines(root, nodeEls, wrapper));
  return nodeEls;
}

// ── Draw dashed SVG lines between parent and child nodes ─────────────────
function drawLines(root, nodeEls, wrapper) {
  const existing = wrapper.querySelector('.tree-svg');
  if (existing) existing.remove();

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'tree-svg');   // className is read-only on SVG elements
  const wRect = wrapper.getBoundingClientRect();

  function connect(parent, child) {
    const pEl = nodeEls.get(parent);
    const cEl = nodeEls.get(child);
    if (!pEl || !cEl) return;

    const pBox = pEl.querySelector('.tree-node-box');
    const cBox = cEl.querySelector('.tree-node-box');
    const pR = pBox.getBoundingClientRect();
    const cR = cBox.getBoundingClientRect();

    const x1 = pR.left + pR.width / 2 - wRect.left;
    const y1 = pR.bottom - wRect.top;
    const x2 = cR.left + cR.width / 2 - wRect.left;
    const y2 = cR.top - wRect.top;

    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', x1);
    line.setAttribute('y1', y1);
    line.setAttribute('x2', x2);
    line.setAttribute('y2', y2);
    svg.appendChild(line);

    (child.children || []).forEach(grandchild => connect(child, grandchild));
  }

  (root.children || []).forEach(child => connect(root, child));

  svg.setAttribute('viewBox', `0 0 ${wRect.width} ${wRect.height}`);
  svg.style.cssText = `position:absolute;top:0;left:0;width:${wRect.width}px;height:${wRect.height}px;pointer-events:none;overflow:visible;`;
  wrapper.appendChild(svg);
}

// ── Node hover popup helpers ──────────────────────────────────────────────
function showNodePopup(e, node) {
  popupLabel.textContent = node.label;
  popupRowCount.textContent = node.rowCount + ' rows';

  popupBody.innerHTML = '';
  if (!node.columns || node.columns.length === 0) {
    popupBody.innerHTML = '<div class="popup-empty">No data available</div>';
  } else if (!node.preview || node.preview.length === 0) {
    popupBody.innerHTML = '<div class="popup-empty">(0 rows)</div>';
  } else {
    const tbl = document.createElement('table');
    tbl.className = 'popup-table';

    const thead = document.createElement('thead');
    const hrow = document.createElement('tr');
    node.columns.forEach(c => {
      const th = document.createElement('th');
      th.textContent = c;
      hrow.appendChild(th);
    });
    thead.appendChild(hrow);
    tbl.appendChild(thead);

    const tbody = document.createElement('tbody');
    node.preview.slice(0, 5).forEach(row => {
      const tr = document.createElement('tr');
      row.forEach(cell => {
        const td = document.createElement('td');
        td.textContent = cell === null ? 'NULL' : cell;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    tbl.appendChild(tbody);
    popupBody.appendChild(tbl);

    if (node.rowCount > Math.min(5, node.preview.length)) {
      const more = document.createElement('div');
      more.className = 'popup-more';
      more.textContent = `… and ${node.rowCount - Math.min(5, node.preview.length)} more rows`;
      popupBody.appendChild(more);
    }
  }

  positionPopup(e);
  nodePopup.classList.remove('hidden');
}

function positionPopup(e) {
  const x = e.clientX + 14;
  const y = e.clientY - 14;
  const popW = nodePopup.offsetWidth || 260;
  const popH = nodePopup.offsetHeight || 200;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  nodePopup.style.left = (x + popW > vw ? vw - popW - 8 : x) + 'px';
  nodePopup.style.top  = (y + popH > vh ? vh - popH - 8 : y) + 'px';
}

function hideNodePopup() {
  nodePopup.classList.add('hidden');
}


/* =========================================================
   Step-through execution, optimizer, SQL → RA
   ========================================================= */

let lastQuery = '';
const treeCost = document.getElementById('tree-cost');

function esc(t) {
  return String(t).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}

function fmtNum(x) {
  if (x === null || x === undefined) return '–';
  if (x >= 100 || Number.isInteger(x)) return Math.round(x).toLocaleString();
  return (Math.round(x * 10) / 10).toString();
}

function buildTable(rows, cols) {
  const tbl = document.createElement('table');
  tbl.className = 'mini-table';
  const head = document.createElement('tr');
  (cols || []).forEach(c => { const th = document.createElement('th'); th.textContent = c; head.appendChild(th); });
  const thead = document.createElement('thead'); thead.appendChild(head); tbl.appendChild(thead);
  const tbody = document.createElement('tbody');
  (rows || []).forEach(r => {
    const tr = document.createElement('tr');
    r.forEach(v => { const td = document.createElement('td'); td.textContent = v === null ? 'NULL' : v; tr.appendChild(td); });
    tbody.appendChild(tr);
  });
  tbl.appendChild(tbody);
  return tbl;
}

// ── Step-through execution ───────────────────────────────────────────────
const stepBar     = document.getElementById('step-bar');
const stepPanel   = document.getElementById('step-panel');
const stepCounter = document.getElementById('step-counter');
const stepPlayBtn = document.getElementById('step-play');
let execSteps = [], stepIdx = -1, playTimer = null;

const STEP_TEXT = [
  ['π', 'Projection: keep only the listed columns and remove duplicate rows.'],
  ['σ', 'Selection: keep only the rows where the condition is true.'],
  ['×', 'Cross join: pair every row on the left with every row on the right.'],
  ['⋈ (Natural', 'Natural join: combine rows that agree on all common columns.'],
  ['⋈', 'Theta join: combine rows from both inputs where the join condition holds.'],
  ['⟕', 'Left outer join: like a join, but every left row is kept (unmatched columns become NULL).'],
  ['⟖', 'Right outer join: like a join, but every right row is kept (unmatched columns become NULL).'],
  ['⟗', 'Full outer join: like a join, but unmatched rows from both sides are kept.'],
  ['∪', 'Union: rows that are in either input (duplicates removed).'],
  ['∩', 'Intersection: rows that are in both inputs.'],
  ['−', 'Difference: rows of the left input that are not in the right input.'],
  ['÷', 'Division: left values that are paired with every row of the right input.'],
  ['ρ', 'Rename: give the relation (and optionally its columns) a new name.'],
  ['γ', 'Grouping: form groups and compute an aggregate for each group.'],
];

function describeStep(node) {
  if (!node.children || node.children.length === 0) return 'Scan: read every row of the base table.';
  const hit = STEP_TEXT.find(([sym]) => node.label.startsWith(sym));
  return hit ? hit[1] : '';
}

function postOrder(n, out = []) {
  (n.children || []).forEach(ch => postOrder(ch, out));
  out.push(n);
  return out;
}

function setupStepper(root, els) {
  stopPlay();
  execSteps = postOrder(root).map(n => ({ node: n, el: els.get(n) }));
  stepIdx = -1;
  stepBar.classList.toggle('hidden', execSteps.length === 0);
  stepPanel.classList.add('hidden');
  updateStepCounter();
}

function updateStepCounter() {
  stepCounter.textContent = stepIdx < 0 ? `${execSteps.length} steps` : `Step ${stepIdx + 1} / ${execSteps.length}`;
}

function goStep(i) {
  if (!execSteps.length) return;
  stepIdx = Math.max(0, Math.min(i, execSteps.length - 1));
  execSteps.forEach((st, j) => {
    const box = st.el && st.el.querySelector('.tree-node-box');
    if (!box) return;
    box.classList.toggle('node-done', j < stepIdx);
    box.classList.toggle('node-active', j === stepIdx);
  });
  const { node } = execSteps[stepIdx];
  const estLine = node.estRows !== null && node.estRows !== undefined
    ? `<span class="metric">estimated <b>${fmtNum(node.estRows)}</b> <span class="formula">${esc(node.formula || '')}</span></span>`
    : '';
  stepPanel.innerHTML = `
    <div class="step-head">
      <span class="step-no">Step ${stepIdx + 1}</span>
      <span class="step-label">${esc(node.label)}</span>
    </div>
    <p class="step-desc">${esc(describeStep(node))}</p>
    <div class="step-metrics">
      <span class="metric">actual <b>${node.rowCount}</b> row${node.rowCount === 1 ? '' : 's'}</span>
      ${estLine}
      ${node.cost != null ? `<span class="metric">cost so far <b>${fmtNum(node.cost)}</b></span>` : ''}
    </div>
    <pre class="sql-pre step-sql">${esc(node.sql || '')}</pre>`;
  const wrap = document.createElement('div');
  wrap.className = 'table-wrap step-table';
  wrap.appendChild(buildTable(node.preview, node.columns));
  if (node.rowCount > (node.preview || []).length) {
    const more = document.createElement('div');
    more.className = 'popup-more';
    more.textContent = `showing ${node.preview.length} of ${node.rowCount} rows`;
    wrap.appendChild(more);
  }
  stepPanel.appendChild(wrap);
  stepPanel.classList.remove('hidden');
  updateStepCounter();
}

function stopPlay() {
  if (playTimer) clearInterval(playTimer);
  playTimer = null;
  if (stepPlayBtn) stepPlayBtn.textContent = '▶ Step through execution';
}

document.getElementById('step-next').addEventListener('click', () => { stopPlay(); goStep(stepIdx + 1); });
document.getElementById('step-prev').addEventListener('click', () => { stopPlay(); goStep(stepIdx - 1); });
document.getElementById('step-first').addEventListener('click', () => { stopPlay(); goStep(0); });
stepPlayBtn.addEventListener('click', () => {
  if (playTimer) { stopPlay(); return; }
  if (stepIdx >= execSteps.length - 1) stepIdx = -1;
  goStep(stepIdx + 1);
  stepPlayBtn.textContent = '⏸ Pause';
  playTimer = setInterval(() => {
    if (stepIdx >= execSteps.length - 1) { stopPlay(); return; }
    goStep(stepIdx + 1);
  }, 1600);
});

// ── Optimizer ────────────────────────────────────────────────────────────
const optBtn = document.getElementById('optimize-btn');
const optOut = document.getElementById('opt-out');
const optErr = document.getElementById('opt-error');

function resetOptimizer() {
  optOut.classList.add('hidden');
  optErr.classList.add('hidden');
}

optBtn.addEventListener('click', async () => {
  const query = lastQuery || queryEl.value.trim();
  if (!query) { optErr.classList.remove('hidden'); document.getElementById('opt-error-text').textContent = 'Run a query first.'; return; }
  optBtn.disabled = true;
  optBtn.textContent = 'Optimizing…';
  optErr.classList.add('hidden');
  try {
    const resp = await fetch('/optimize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-DB-Name': dbSelect.value },
      body: JSON.stringify({ query })
    });
    const data = await resp.json();
    if (data.error) throw new Error(data.error);
    renderOptimizer(data);
  } catch (e) {
    document.getElementById('opt-error-text').textContent = e.message;
    optErr.classList.remove('hidden');
  } finally {
    optBtn.disabled = false;
    optBtn.textContent = 'Optimize this query';
  }
});

function renderOptimizer(d) {
  const before = d.original.cost, after = d.optimized.cost;
  const saved = before ? Math.max(0, (before - after) / before * 100) : 0;
  const max = Math.max(before || 0, after || 0, 1);
  document.getElementById('opt-summary').innerHTML = `
    <div class="cost-row"><span class="cost-name">Original</span>
      <div class="cost-track"><div class="cost-fill" style="width:${(before / max * 100).toFixed(1)}%"></div></div>
      <span class="cost-val">${fmtNum(before)}</span></div>
    <div class="cost-row"><span class="cost-name">Optimized</span>
      <div class="cost-track"><div class="cost-fill good" style="width:${(after / max * 100).toFixed(1)}%"></div></div>
      <span class="cost-val">${fmtNum(after)}</span></div>
    <div class="opt-facts">
      <span class="fact ${saved > 0 ? 'good' : ''}">${saved > 0 ? '▼ ' + saved.toFixed(1) + '% cheaper' : 'No cost change'}</span>
      <span class="fact">${d.steps.length} rewrite${d.steps.length === 1 ? '' : 's'}</span>
      <span class="fact ${d.resultsMatch ? 'good' : 'bad'}">${d.resultsMatch ? '✓ Same ' + d.rowCount + ' result rows' : '✗ Results differ'}</span>
    </div>`;

  const list = document.getElementById('opt-steps');
  list.innerHTML = d.steps.length
    ? d.steps.map(st => `<li><span class="rule-id">${esc(st.id)}</span> <b>${esc(st.rule)}</b>
        <code class="rule-law">${esc(st.law)}</code><div class="rule-detail">${esc(st.detail)}</div></li>`).join('')
    : '<li class="rule-none">No rule applies — this expression is already in its best form for these heuristics.</li>';

  document.getElementById('opt-ra').textContent = d.optimized.ra;
  document.getElementById('opt-cost-before').textContent = 'cost ' + fmtNum(before);
  document.getElementById('opt-cost-after').textContent = 'cost ' + fmtNum(after);
  document.getElementById('opt-sql-before').textContent = d.original.sql;
  document.getElementById('opt-sql-after').textContent = d.optimized.sql;
  optOut.classList.remove('hidden');
  renderTree(d.original.tree, document.getElementById('opt-tree-before'));
  renderTree(d.optimized.tree, document.getElementById('opt-tree-after'));
}

document.getElementById('opt-use').addEventListener('click', () => {
  queryEl.value = document.getElementById('opt-ra').textContent;
  form.requestSubmit();
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

// ── SQL → relational algebra ─────────────────────────────────────────────
const sqlInput   = document.getElementById('sql-input');
const sql2raBtn  = document.getElementById('sql2ra-btn');
const sql2raOut  = document.getElementById('sql2ra-out');
const sql2raErr  = document.getElementById('sql2ra-error');
const sql2raLoad = document.getElementById('sql2ra-loading');

sql2raBtn.addEventListener('click', async () => {
  const sql = sqlInput.value.trim();
  sql2raErr.classList.add('hidden');
  sql2raOut.classList.add('hidden');
  if (!sql) { document.getElementById('sql2ra-error-text').textContent = 'Paste a SQL query first.'; sql2raErr.classList.remove('hidden'); return; }
  sql2raLoad.classList.remove('hidden');
  try {
    const resp = await fetch('/sql-to-ra', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-DB-Name': dbSelect.value },
      body: JSON.stringify({ sql })
    });
    const d = await resp.json();
    if (d.error) throw new Error(d.error);
    document.getElementById('sql2ra-ra').textContent = d.ra;
    document.getElementById('sql2ra-english').textContent = d.explanation || '';
    document.getElementById('sql2ra-sql').textContent = d.generatedSql;
    const rt = d.roundTrip || {};
    const check = document.getElementById('sql2ra-check');
    if (rt.error) {
      check.className = 'check-badge warn';
      check.textContent = 'Could not verify against the database: ' + rt.error;
    } else if (rt.match) {
      check.className = 'check-badge good';
      check.textContent = `✓ Verified: the expression returns the same ${rt.raRows} row${rt.raRows === 1 ? '' : 's'} as your SQL`;
    } else {
      check.className = 'check-badge bad';
      check.textContent = `✗ Results differ (SQL: ${rt.originalRows} rows, expression: ${rt.raRows} rows)`;
    }
    document.getElementById('sql2ra-warnings').innerHTML =
      (d.warnings || []).map(w => `<li>${esc(w)}</li>`).join('');
    sql2raOut.classList.remove('hidden');
  } catch (e) {
    document.getElementById('sql2ra-error-text').textContent = e.message;
    sql2raErr.classList.remove('hidden');
  } finally {
    sql2raLoad.classList.add('hidden');
  }
});

document.getElementById('sql2ra-use').addEventListener('click', () => {
  queryEl.value = document.getElementById('sql2ra-ra').textContent;
  form.requestSubmit();
  window.scrollTo({ top: 0, behavior: 'smooth' });
});


// ── Theme (light / dark) ─────────────────────────────────────────────────
const themeBtn = document.getElementById('theme-toggle');

function currentTheme() {
  const set = document.documentElement.dataset.theme;
  if (set) return set;
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function syncThemeButton() {
  if (themeBtn) themeBtn.textContent = currentTheme() === 'dark' ? '☀' : '☾';
}

if (themeBtn) {
  themeBtn.addEventListener('click', () => {
    const next = currentTheme() === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('ra-theme', next); } catch (e) {}
    syncThemeButton();
    if (lastSchema) renderER(lastSchema);
  });
  syncThemeButton();
}
if (window.matchMedia) {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    syncThemeButton();
    if (lastSchema && !document.documentElement.dataset.theme) renderER(lastSchema);
  });
}

// ── ER diagram drawn from the live schema ────────────────────────────────
let lastSchema = null;
let erCounter = 0;

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function erName(s) {
  return String(s).replace(/[^A-Za-z0-9_]/g, '_') || 'x';
}

function erText(tables) {
  const lines = ['erDiagram'];
  tables.forEach(t => {
    lines.push(`  ${erName(t.name)} {`);
    t.columns.forEach(c => {
      const type = erName((c.type || 'TEXT').split('(')[0]);
      const keys = [];
      if (c.pk) keys.push('PK');
      if ((t.foreignKeys || []).some(fk => fk.from === c.name)) keys.push('FK');
      lines.push(`    ${type} ${erName(c.name)}${keys.length ? ' ' + keys.join(',') : ''}`);
    });
    lines.push('  }');
  });
  tables.forEach(t => (t.foreignKeys || []).forEach(fk => {
    lines.push(`  ${erName(fk.table)} ||--o{ ${erName(t.name)} : "${erName(fk.from)}"`);
  }));
  return lines.join('\n');
}

async function renderER(tables) {
  lastSchema = tables;
  const box = document.getElementById('er-diagram');
  if (!box) return;
  if (typeof mermaid === 'undefined') {
    box.innerHTML = '<div class="loading-text">Diagram library could not load (offline?).</div>';
    return;
  }
  if (!tables || !tables.length) {
    box.innerHTML = '<div class="loading-text">No tables to draw.</div>';
    return;
  }
  mermaid.initialize({
    startOnLoad: false,
    theme: 'base',
    securityLevel: 'strict',
    fontFamily: 'IBM Plex Mono, monospace',
    themeVariables: {
      background: cssVar('--sheet'),
      primaryColor: cssVar('--card'),
      primaryTextColor: cssVar('--ink'),
      primaryBorderColor: cssVar('--ink-soft'),
      secondaryColor: cssVar('--wash'),
      tertiaryColor: cssVar('--sheet'),
      lineColor: cssVar('--accent'),
      textColor: cssVar('--ink'),
      attributeBackgroundColorOdd: cssVar('--sheet'),
      attributeBackgroundColorEven: cssVar('--wash'),
      fontSize: '13px',
    },
  });
  try {
    const { svg } = await mermaid.render('er-svg-' + (++erCounter), erText(tables));
    box.innerHTML = svg;
  } catch (e) {
    box.innerHTML = '<div class="loading-text">Could not draw this schema.</div>';
  }
}
