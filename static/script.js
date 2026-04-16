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
    header.innerHTML = `${tbl.name} <span class="tbl-arrow">▶</span>`;

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
        `<span class="schema-col-name">${col.name}</span>` +
        `<span class="schema-col-type">${col.type}</span>`;
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

  const raw = queryEl.value.trim();
  if (!raw) {
    showError('Please enter a relational algebra expression.');
    return;
  }

  setLoading(true);

  try {
    const dbName = dbSelect.value;
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

    // Show query title above results table
    if (queryTitle) queryTitle.textContent = '\u25b6 ' + raw;

    // Show rows
    renderTable(data.rows, data.columns || []);

    resultSec.classList.remove('hidden');

    // Fetch and render expression tree (non-blocking)
    fetchAndRenderTree(raw);

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
      treeContainer.innerHTML = `<div style="color:var(--error);font-size:.8rem;padding:8px">Tree error: ${data.error}</div>`;
      return;
    }
    renderTree(data.tree);
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
function renderTree(root) {
  if (!root) { treeContainer.innerHTML = ''; return; }

  treeContainer.innerHTML = '';

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
        document.querySelectorAll('.tree-node-box').forEach(b => b.classList.remove('node-active'));
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
  treeContainer.appendChild(wrapper);

  // Draw SVG connector lines after layout
  requestAnimationFrame(() => drawLines(root, nodeEls, wrapper));
}

// ── Draw dashed SVG lines between parent and child nodes ─────────────────
function drawLines(root, nodeEls, wrapper) {
  const existing = wrapper.querySelector('.tree-svg');
  if (existing) existing.remove();

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.className = 'tree-svg';
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
    node.preview.forEach(row => {
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

    if (node.rowCount > node.preview.length) {
      const more = document.createElement('div');
      more.className = 'popup-more';
      more.textContent = `… and ${node.rowCount - node.preview.length} more rows`;
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
