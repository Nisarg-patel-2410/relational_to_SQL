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

    // Show rows
    renderTable(data.rows, data.columns || []);

    resultSec.classList.remove('hidden');

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
    // Clone the SVG currently inside the mermaid div
    const svg = erDiagram.querySelector('svg');
    if (svg) {
      modalBody.innerHTML = '';
      const cloned = svg.cloneNode(true);
      // Remove max height and let it scale
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
