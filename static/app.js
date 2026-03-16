/* app.js — Frontend behaviour, API interactions, and state management */

(function () {
  'use strict';

  // ── DOM references ──────────────────────────────────────────────────────
  const dropZone        = document.getElementById('drop-zone');
  const fileInput       = document.getElementById('file-input');
  const fileList        = document.getElementById('file-list');
  const runBtn          = document.getElementById('run-btn');
  const loading         = document.getElementById('loading');
  const errorMsg        = document.getElementById('error-msg');
  const resultsPanel    = document.getElementById('results');
  const filesAnalysed   = document.getElementById('files-analysed');
  const scoreNumber     = document.getElementById('score-number');
  const scoreBar        = document.getElementById('score-bar');
  const investLabel     = document.getElementById('investment-label');
  const companySummary  = document.getElementById('company-summary');
  const mRevenueGrowth  = document.getElementById('m-revenue-growth');
  const mEbitdaMargin   = document.getElementById('m-ebitda-margin');
  const mDebtEquity     = document.getElementById('m-debt-equity');
  const mMarketSize     = document.getElementById('m-market-size');
  const mFoundingYear   = document.getElementById('m-founding-year');
  const mTeamSize       = document.getElementById('m-team-size');
  const risksList       = document.getElementById('risks-list');
  const recommendText   = document.getElementById('recommendation-text');

  // ── State ───────────────────────────────────────────────────────────────
  let selectedFiles = [];

  // ── Helpers ─────────────────────────────────────────────────────────────
  function showError(msg) {
    errorMsg.textContent = msg;
    errorMsg.classList.remove('hidden');
  }

  function hideError() {
    errorMsg.classList.add('hidden');
    errorMsg.textContent = '';
  }

  function fmt(val, suffix = '') {
    if (val === null || val === undefined) return '—';
    return `${val}${suffix}`;
  }

  function fmtPct(val) {
    if (val === null || val === undefined) return '—';
    return `${Number(val).toFixed(1)}%`;
  }

  function fmtBn(val) {
    if (val === null || val === undefined) return '—';
    return `£${Number(val).toFixed(1)}bn`;
  }

  function renderFileList() {
    fileList.innerHTML = '';
    selectedFiles.forEach((file, idx) => {
      const li = document.createElement('li');
      li.className = 'file-item';
      li.innerHTML = `
        <span class="file-item-name">${escHtml(file.name)}</span>
        <button class="file-remove-btn" aria-label="Remove ${escHtml(file.name)}" data-idx="${idx}">✕</button>
      `;
      fileList.appendChild(li);
    });
    runBtn.disabled = selectedFiles.length === 0;
  }

  function escHtml(str) {
    return str.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  function addFiles(fileArray) {
    for (const f of fileArray) {
      // Avoid duplicates by name
      if (!selectedFiles.find(existing => existing.name === f.name)) {
        selectedFiles.push(f);
      }
    }
    renderFileList();
  }

  // ── Drag and drop ────────────────────────────────────────────────────────
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });

  dropZone.addEventListener('dragleave', (e) => {
    if (!dropZone.contains(e.relatedTarget)) {
      dropZone.classList.remove('drag-over');
    }
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    if (e.dataTransfer.files.length) {
      addFiles(Array.from(e.dataTransfer.files));
    }
  });

  dropZone.addEventListener('click', (e) => {
    // Only trigger if not clicking the hidden input directly
    if (e.target !== fileInput) fileInput.click();
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length) {
      addFiles(Array.from(fileInput.files));
      // Reset input so same file can be re-added after removal
      fileInput.value = '';
    }
  });

  // Remove file on button click
  fileList.addEventListener('click', (e) => {
    const btn = e.target.closest('.file-remove-btn');
    if (!btn) return;
    const idx = parseInt(btn.dataset.idx, 10);
    selectedFiles.splice(idx, 1);
    renderFileList();
  });

  // ── Run Analysis ─────────────────────────────────────────────────────────
  runBtn.addEventListener('click', async () => {
    if (!selectedFiles.length) return;

    hideError();
    resultsPanel.classList.add('hidden');
    loading.classList.remove('hidden');
    runBtn.disabled = true;

    const formData = new FormData();
    for (const file of selectedFiles) {
      formData.append('files', file);
    }

    try {
      const res = await fetch('/analyse', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errData.detail || `Server error: ${res.status}`);
      }

      const data = await res.json();
      renderResults(data);
    } catch (err) {
      showError(`Analysis failed: ${err.message}`);
    } finally {
      loading.classList.add('hidden');
      runBtn.disabled = selectedFiles.length === 0;
    }
  });

  // ── Render results ───────────────────────────────────────────────────────
  function renderResults(data) {
    // Files analysed pills
    filesAnalysed.innerHTML = '';
    (data.files_analysed || []).forEach(name => {
      const pill = document.createElement('span');
      pill.className = 'file-pill';
      pill.textContent = `📄 ${name}`;
      filesAnalysed.appendChild(pill);
    });

    // Investment score
    const score = data.investment_score ?? 0;
    const label = data.investment_label ?? '';

    scoreNumber.textContent = score;
    setTimeout(() => {
      scoreBar.style.width = `${score}%`;
    }, 100);

    // Determine colour class from label
    let colorClass = 'pass';
    if (label === 'Consider') colorClass = 'consider';
    else if (label === 'Strong Buy') colorClass = 'buy';

    scoreNumber.className = `score-number score-${colorClass}`;
    scoreBar.className = `score-bar bar-${colorClass}`;
    investLabel.className = `investment-label label-${colorClass}`;
    investLabel.textContent = label;

    // Company summary
    companySummary.textContent = data.company_summary || '—';

    // Financial metrics
    const m = data.financial_metrics || {};
    mRevenueGrowth.textContent = fmtPct(m.revenue_growth_pct);
    mEbitdaMargin.textContent  = fmtPct(m.ebitda_margin);
    mDebtEquity.textContent    = fmt(m.debt_to_equity !== null && m.debt_to_equity !== undefined ? Number(m.debt_to_equity).toFixed(2) : null);
    mMarketSize.textContent    = fmtBn(m.market_size_bn);
    mFoundingYear.textContent  = fmt(m.founding_year);
    mTeamSize.textContent      = fmt(m.team_size);

    // Risks
    risksList.innerHTML = '';
    (data.risks || []).forEach(risk => {
      const li = document.createElement('li');
      li.className = 'risk-item';
      li.innerHTML = `<span class="risk-icon">⚠️</span><span>${escHtml(risk)}</span>`;
      risksList.appendChild(li);
    });

    // Recommendation
    recommendText.textContent = data.recommendation || '—';

    // Show panel with animation
    resultsPanel.classList.remove('hidden');
    resultsPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

})();
