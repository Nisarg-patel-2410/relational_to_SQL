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
  try {
    const resp = await fetch('/tables');
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
    const resp = await fetch('/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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
