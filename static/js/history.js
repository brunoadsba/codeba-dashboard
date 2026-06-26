// ============================================================
// CODEBA — Painel de histórico de auditorias
// ============================================================

let currentRunId = null;
let onHistoryLoadCallback = null;

function initHistory(onLoad) {
    onHistoryLoadCallback = onLoad;

    const btnHistory = document.getElementById('btn-history');
    const btnClose = document.getElementById('history-close');
    const overlay = document.getElementById('history-overlay');
    const drawer = document.getElementById('history-drawer');

    if (btnHistory) {
        btnHistory.addEventListener('click', () => openHistoryPanel());
    }
    if (btnClose) {
        btnClose.addEventListener('click', () => closeHistoryPanel());
    }
    if (overlay) {
        overlay.addEventListener('click', () => closeHistoryPanel());
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && drawer && drawer.classList.contains('open')) {
            closeHistoryPanel();
        }
    });
}

function openHistoryPanel() {
    const drawer = document.getElementById('history-drawer');
    const overlay = document.getElementById('history-overlay');
    if (drawer) drawer.classList.add('open');
    if (overlay) overlay.classList.add('open');
    loadHistoryList();
    setTimeout(resizeCharts, 300);
}

function closeHistoryPanel() {
    const drawer = document.getElementById('history-drawer');
    const overlay = document.getElementById('history-overlay');
    if (drawer) drawer.classList.remove('open');
    if (overlay) overlay.classList.remove('open');
    setTimeout(resizeCharts, 300);
}

async function loadHistoryList() {
    const listEl = document.getElementById('history-list');
    if (!listEl) return;

    listEl.replaceChildren();
    const loading = document.createElement('div');
    loading.className = 'history-loading';
    loading.textContent = 'Carregando...';
    listEl.appendChild(loading);

    try {
        const res = await fetch('/api/runs?limit=50');
        const data = await res.json();
        listEl.replaceChildren();

        if (!data.runs || data.runs.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'history-empty';
            empty.textContent = 'Nenhuma auditoria salva ainda.';
            listEl.appendChild(empty);
            return;
        }

        data.runs.forEach(run => {
            listEl.appendChild(createHistoryItem(run));
        });
    } catch (err) {
        listEl.replaceChildren();
        const errEl = document.createElement('div');
        errEl.className = 'history-empty';
        errEl.textContent = 'Erro ao carregar histórico.';
        listEl.appendChild(errEl);
    }
}

function createHistoryItem(run) {
    const item = document.createElement('div');
    item.className = 'history-item' + (run.id === currentRunId ? ' active' : '');
    item.setAttribute('role', 'button');
    item.setAttribute('tabindex', '0');

    const header = document.createElement('div');
    header.className = 'history-item-header';

    const date = document.createElement('span');
    date.className = 'history-item-date';
    date.textContent = formatHistoryDate(run.created_at);
    header.appendChild(date);

    if (run.id === currentRunId) {
        const badge = document.createElement('span');
        badge.className = 'history-active-badge';
        badge.textContent = 'Atual';
        header.appendChild(badge);
    }

    item.appendChild(header);

    const period = document.createElement('div');
    period.className = 'history-item-period';
    if (run.period_start && run.period_end && run.period_start !== run.period_end) {
        period.textContent = `${run.period_start} — ${run.period_end}`;
    } else {
        period.textContent = run.period_start || '—';
    }
    item.appendChild(period);

    const resumo = run.resumo || {};
    const stats = document.createElement('div');
    stats.className = 'history-item-stats';
    stats.textContent = `${resumo.ok || 0} OK · ${resumo.divergencias || 0} div · ${resumo.total_processado || 0} total`;
    item.appendChild(stats);

    const files = document.createElement('div');
    files.className = 'history-item-files';
    files.textContent = (run.file_names || []).join(', ');
    item.appendChild(files);

    const actions = document.createElement('div');
    actions.className = 'history-item-actions';

    const btnLoad = document.createElement('button');
    btnLoad.type = 'button';
    btnLoad.className = 'btn-sm history-btn-load';
    btnLoad.textContent = 'Carregar';
    btnLoad.addEventListener('click', (e) => {
        e.stopPropagation();
        loadHistoryRun(run.id);
    });
    actions.appendChild(btnLoad);

    const btnDelete = document.createElement('button');
    btnDelete.type = 'button';
    btnDelete.className = 'btn-sm history-btn-delete';
    btnDelete.innerHTML = '<i class="ph ph-trash"></i>';
    btnDelete.title = 'Excluir';
    btnDelete.addEventListener('click', (e) => {
        e.stopPropagation();
        deleteHistoryRun(run.id);
    });
    actions.appendChild(btnDelete);

    item.appendChild(actions);

    item.addEventListener('click', () => loadHistoryRun(run.id));
    item.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            loadHistoryRun(run.id);
        }
    });

    return item;
}

function formatHistoryDate(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

async function loadHistoryRun(runId) {
    try {
        const res = await fetch(`/api/runs/${runId}`);
        const data = await res.json();
        if (data.error) {
            if (typeof showError === 'function') showError(data.error);
            return;
        }
        currentRunId = runId;
        resetFilterState();
        if (onHistoryLoadCallback) {
            onHistoryLoadCallback(data);
        }
        closeHistoryPanel();
        const uploadScreen = document.getElementById('upload-screen');
        const dashboardScreen = document.getElementById('dashboard-screen');
        if (uploadScreen) uploadScreen.classList.add('hidden');
        if (dashboardScreen) dashboardScreen.classList.remove('hidden');
    } catch (err) {
        if (typeof showError === 'function') showError('Erro ao carregar auditoria do histórico.');
    }
}

async function deleteHistoryRun(runId) {
    if (!confirm('Excluir esta auditoria do histórico?')) return;
    try {
        const res = await fetch(`/api/runs/${runId}`, { method: 'DELETE' });
        if (!res.ok) {
            const data = await res.json();
            if (typeof showError === 'function') showError(data.error || 'Erro ao excluir.');
            return;
        }
        if (currentRunId === runId) currentRunId = null;
        loadHistoryList();
    } catch (err) {
        if (typeof showError === 'function') showError('Erro ao excluir auditoria.');
    }
}

function setCurrentRunId(runId) {
    currentRunId = runId;
}
