// ============================================================
// CODEBA Dashboard de Auditoria — App v3.0
// Multi-Produto + Conformidade + Destaque de Erro de Placa
// Toda renderização via DOM API segura (sem innerHTML)
// ============================================================

// ── Referências DOM ─────────────────────────────────────────
const body = document.body;
const themeToggle = document.getElementById('theme-toggle');
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const fileList = document.getElementById('file-list');
const btnProcess = document.getElementById('btn-process');
const btnSelectFiles = document.getElementById('btn-select-files');
const loading = document.getElementById('loading');
const loadingText = document.getElementById('loading-text');
const uploadScreen = document.getElementById('upload-screen');
const dashboardScreen = document.getElementById('dashboard-screen');
const errorModal = document.getElementById('error-modal');
const errorModalMessage = document.getElementById('error-modal-message');
const errorModalClose = document.getElementById('error-modal-close');

// Expected file indicators
const expectExcel = document.getElementById('expect-excel');
const expectPdf = document.getElementById('expect-pdf');

// Dashboard elements
const searchInput = document.getElementById('search-placa');
const filterDateInput = document.getElementById('filter-date');
const filterProdutoSelect = document.getElementById('filter-produto');
const btnFilter = document.getElementById('btn-filter');
const btnClearFilter = document.getElementById('btn-clear-filter');
const filterCount = document.getElementById('filter-count');

// Collapsible OK section
const headerOk = document.getElementById('header-ok');
const bodyOk = document.getElementById('body-ok');

let selectedFiles = [];
let globalAuditData = null;
let dateRangePicker = null;

// Extensões permitidas (allow-list — espelha o backend)
const ALLOWED_EXTENSIONS = ['.xlsx', '.xls', '.pdf'];

// ── Mapeamento de Produto → Classe CSS ──────────────────────
function getProductBadgeClass(produto) {
    if (!produto) return 'desconhecido';
    const p = produto.toUpperCase();
    if (p.includes('(DEDUZIDO)')) return 'deduzido';
    if (p.startsWith('AMBÍGUO') || p.startsWith('AMBIGUO')) return 'ambiguo';
    if (p === 'NÃO IDENTIFICADO' || p === 'NAO IDENTIFICADO') return 'desconhecido';
    if (p.includes('LITIO') || p.includes('LÍTIO')) return 'litio';
    if (p.includes('MANGAN') || p.includes('MANGANÊS')) return 'manganes';
    if (p.includes('MILHO')) return 'milho';
    if (p.includes('NIQUEL') || p.includes('NÍQUEL')) return 'niquel';
    if (p.includes('XIDO') || p.includes('MAGNÉSIO') || p.includes('MAGNESIO')) return 'oxido';
    return 'desconhecido';
}

function createProductBadge(produto) {
    const span = document.createElement('span');
    const badgeClass = getProductBadgeClass(produto);
    span.className = 'badge-produto ' + badgeClass;

    const displayName = produto || '—';
    if (produto && produto.includes('(Deduzido)')) {
        const bulb = document.createElement('i');
        bulb.className = 'ph ph-lightbulb';
        bulb.title = 'Produto deduzido pelo histórico da placa';
        span.appendChild(bulb);
        span.appendChild(document.createTextNode(' ' + displayName));
    } else {
        span.textContent = displayName;
    }
    return span;
}

// ── Tema Light/Dark ─────────────────────────────────────────
themeToggle.addEventListener('click', () => {
    body.classList.toggle('light-theme');
    body.classList.toggle('dark-theme');
    const icon = themeToggle.querySelector('i');
    if (body.classList.contains('light-theme')) {
        icon.classList.replace('ph-sun', 'ph-moon');
    } else {
        icon.classList.replace('ph-moon', 'ph-sun');
    }
    if (globalAuditData) {
        const filters = getLegacyFilters();
        const { filteredVolume } = applyFilters(globalAuditData, filters);
        const bucketWeek = shouldBucketByWeek(filteredVolume);
        renderVolumeCharts(aggregateVolume(filteredVolume, bucketWeek));
    }
});

// ── Error Modal (substitui alert()) ─────────────────────────
function showError(message) {
    errorModalMessage.textContent = message;
    errorModal.classList.remove('hidden');
    // Trigger reflow for animation
    void errorModal.offsetWidth;
    errorModal.classList.add('active');
}

function hideError() {
    errorModal.classList.remove('active');
    setTimeout(() => errorModal.classList.add('hidden'), 300);
}

if (errorModalClose) {
    errorModalClose.addEventListener('click', hideError);
}

if (errorModal) {
    errorModal.addEventListener('click', (e) => {
        if (e.target === errorModal) hideError();
    });
}

// ── Upload: Drag & Drop ─────────────────────────────────────
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    handleFiles(e.dataTransfer.files);
});

btnSelectFiles.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
});

// Allow clicking the drop zone itself
dropZone.addEventListener('click', (e) => {
    if (e.target === dropZone || e.target.closest('.drop-icon') || e.target.closest('h3') || e.target.closest('p:not(button)')) {
        fileInput.click();
    }
});

fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
});

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

function updateUploadState() {
    let hasExcel = selectedFiles.some(f => {
        const e = '.' + f.name.split('.').pop().toLowerCase();
        return e === '.xlsx' || e === '.xls';
    });
    let hasPdf = selectedFiles.some(f => {
        const e = '.' + f.name.split('.').pop().toLowerCase();
        return e === '.pdf';
    });

    if (hasExcel) expectExcel.classList.add('received');
    else expectExcel.classList.remove('received');

    if (hasPdf) expectPdf.classList.add('received');
    else expectPdf.classList.remove('received');

    if (selectedFiles.length > 0) {
        btnProcess.classList.remove('hidden');
    } else {
        btnProcess.classList.add('hidden');
    }
}

function handleFiles(files) {
    for (let file of files) {
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (!ALLOWED_EXTENSIONS.includes(ext)) continue;

        // Evitar anexar o mesmo arquivo duas vezes
        if (selectedFiles.some(f => f.name === file.name && f.size === file.size)) continue;

        selectedFiles.push(file);

        // Determine file type icon and color
        const isExcel = ext === '.xlsx' || ext === '.xls';

        // Build file item element (DOM API segura)
        const el = document.createElement('div');
        el.className = 'file-item';

        const icon = document.createElement('i');
        icon.className = isExcel ? 'ph ph-file-xls' : 'ph ph-file-pdf';
        icon.style.color = isExcel ? 'var(--success)' : 'var(--danger)';

        const nameSpan = document.createElement('span');
        nameSpan.className = 'file-name';
        nameSpan.textContent = file.name;

        const sizeSpan = document.createElement('span');
        sizeSpan.className = 'file-size';
        sizeSpan.textContent = formatFileSize(file.size);

        const removeBtn = document.createElement('i');
        removeBtn.className = 'ph ph-trash file-remove';
        removeBtn.title = 'Remover arquivo';
        removeBtn.style.cursor = 'pointer';
        removeBtn.style.color = 'var(--text-secondary)';
        removeBtn.style.transition = 'color 0.2s';
        
        removeBtn.addEventListener('mouseenter', () => removeBtn.style.color = 'var(--danger)');
        removeBtn.addEventListener('mouseleave', () => removeBtn.style.color = 'var(--text-secondary)');

        removeBtn.addEventListener('click', () => {
            selectedFiles = selectedFiles.filter(f => f !== file);
            el.remove();
            updateUploadState();
        });

        el.appendChild(icon);
        el.appendChild(nameSpan);
        el.appendChild(sizeSpan);
        el.appendChild(removeBtn);
        fileList.appendChild(el);
    }

    updateUploadState();
}

// ── Botão Substituir (voltar para upload) ───────────────────
document.getElementById('btn-replace').addEventListener('click', () => {
    dashboardScreen.classList.add('hidden');
    uploadScreen.classList.remove('hidden');
    selectedFiles = [];
    fileList.replaceChildren();
    btnProcess.classList.add('hidden');
    expectExcel.classList.remove('received');
    expectPdf.classList.remove('received');
    globalAuditData = null;
});

// ── Processar Arquivos ──────────────────────────────────────
btnProcess.addEventListener('click', async () => {
    if (selectedFiles.length === 0) return;

    btnProcess.classList.add('hidden');
    loading.classList.remove('hidden');
    loadingText.textContent = 'Enviando arquivos...';

    const formData = new FormData();
    selectedFiles.forEach(file => formData.append('files', file));

    try {
        loadingText.textContent = 'Processando e conciliando dados...';

        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            showError(data.error);
        } else if (!data.resumo) {
            showError('Resposta inesperada do servidor. Verifique o log.');
        } else {
            globalAuditData = data;
            if (data.run_id) setCurrentRunId(data.run_id);
            trimAvisoDismissed = false;
            resetFilterState();
            populateProductFilter(data);
            renderDashboard(data);
            uploadScreen.classList.add('hidden');
            dashboardScreen.classList.remove('hidden');
        }
    } catch (err) {
        console.error('Erro na requisição:', err.message);
        showError('Ocorreu um erro ao processar os arquivos. Verifique se o servidor está rodando.');
    } finally {
        loading.classList.add('hidden');
        btnProcess.classList.remove('hidden');
    }
});

// ── Populate Product Filter Dropdown ────────────────────────
function populateProductFilter(data) {
    if (!filterProdutoSelect) return;
    // Clear existing options except the first
    while (filterProdutoSelect.options.length > 1) {
        filterProdutoSelect.remove(1);
    }
    const produtos = data.produtos_detectados || [];
    produtos.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p;
        opt.textContent = p;
        filterProdutoSelect.appendChild(opt);
    });
}

// ── Formatadores ────────────────────────────────────────────
const formatKg = (val) => new Intl.NumberFormat('pt-BR', {
    maximumFractionDigits: 0
}).format(val);

const formatPercent = (val) => new Intl.NumberFormat('pt-BR', {
    maximumFractionDigits: 1
}).format(val) + '%';

// ── Animated Counter ────────────────────────────────────────
function animateCounter(element, targetValue, duration = 800) {
    const start = parseInt(element.textContent) || 0;
    const diff = targetValue - start;
    if (diff === 0) {
        element.textContent = targetValue;
        return;
    }
    const startTime = performance.now();

    function step(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        // Ease out cubic
        const eased = 1 - Math.pow(1 - progress, 3);
        element.textContent = Math.round(start + diff * eased);
        if (progress < 1) {
            requestAnimationFrame(step);
        } else {
            element.textContent = targetValue;
        }
    }
    requestAnimationFrame(step);
}

// ── Determine error badge class ─────────────────────────────
function getErrorBadgeClass(status) {
    if (!status) return 'badge-danger';
    const s = status.toLowerCase();
    if (s.includes('erro de placa')) return 'badge-warning';
    if (s.includes('diferença') || s.includes('peso')) return 'badge-warning';
    if (s.includes('falta no pdf')) return 'badge-danger';
    if (s.includes('falta no excel')) return 'badge-info';
    return 'badge-danger';
}

function getErrorIcon(status) {
    if (!status) return 'ph-warning-circle';
    const s = status.toLowerCase();
    if (s.includes('erro de placa')) return 'ph-identification-card';
    if (s.includes('diferença') || s.includes('peso')) return 'ph-scales';
    if (s.includes('falta no pdf')) return 'ph-file-pdf';
    if (s.includes('falta no excel')) return 'ph-file-xls';
    return 'ph-warning-circle';
}

// ── Create Plate Diff Element (char-by-char highlighting) ───
function createPlateDiff(placa1, placa2, label1, label2) {
    const container = document.createElement('div');
    container.className = 'detail-cell';

    // Row 1: Excel plate
    const row1 = document.createElement('div');
    row1.className = 'detail-values';
    const tag1 = document.createElement('span');
    tag1.className = 'source-tag excel';
    tag1.textContent = label1;
    row1.appendChild(tag1);

    const diff1 = document.createElement('span');
    diff1.className = 'placa-diff';
    for (let i = 0; i < placa1.length; i++) {
        const charSpan = document.createElement('span');
        charSpan.className = (i < placa2.length && placa1[i] !== placa2[i]) ? 'char-diff' : 'char-ok';
        charSpan.textContent = placa1[i];
        diff1.appendChild(charSpan);
    }
    row1.appendChild(diff1);
    container.appendChild(row1);

    // Row 2: PDF plate
    const row2 = document.createElement('div');
    row2.className = 'detail-values';
    const tag2 = document.createElement('span');
    tag2.className = 'source-tag pdf';
    tag2.textContent = label2;
    row2.appendChild(tag2);

    const diff2 = document.createElement('span');
    diff2.className = 'placa-diff';
    for (let i = 0; i < placa2.length; i++) {
        const charSpan = document.createElement('span');
        charSpan.className = (i < placa1.length && placa1[i] !== placa2[i]) ? 'char-diff' : 'char-ok';
        charSpan.textContent = placa2[i];
        diff2.appendChild(charSpan);
    }
    row2.appendChild(diff2);
    container.appendChild(row2);

    return container;
}

// ── Detect period from data ─────────────────────────────────
function detectPeriod(data) {
    const allDates = [];
    (data.ok || []).forEach(i => { if (i.Data) allDates.push(i.Data); });
    (data.divergencias || []).forEach(i => { if (i.Data) allDates.push(i.Data); });

    if (allDates.length === 0) return '—';

    // Parse DD/MM/YYYY
    const parsed = allDates.map(d => {
        const parts = d.split('/');
        if (parts.length === 3) return new Date(parts[2], parts[1] - 1, parts[0]);
        return null;
    }).filter(d => d && !isNaN(d));

    if (parsed.length === 0) return '—';

    parsed.sort((a, b) => a - b);
    const min = parsed[0];
    const max = parsed[parsed.length - 1];

    const fmt = (d) => `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`;

    if (min.getTime() === max.getTime()) return fmt(min) + '/' + min.getFullYear();
    return fmt(min) + ' — ' + fmt(max) + '/' + max.getFullYear();
}

// ── Calculate Product Accuracy ──────────────────────────────
function calculateProductAccuracy(okItems, divItems) {
    const productStats = {};

    okItems.forEach(item => {
        let prod = (item.Produto || '').replace(' (Deduzido)', '');
        if (!prod || prod === 'Não Identificado' || prod.startsWith('Ambíguo')) prod = 'Outros';
        if (!productStats[prod]) productStats[prod] = { ok: 0, div: 0 };
        productStats[prod].ok++;
    });

    divItems.forEach(item => {
        let prod = (item.Produto || '').replace(' (Deduzido)', '');
        if (!prod || prod === 'Não Identificado' || prod.startsWith('Ambíguo')) prod = 'Outros';
        if (!productStats[prod]) productStats[prod] = { ok: 0, div: 0 };
        productStats[prod].div++;
    });

    // Calculate accuracy for each product
    const result = [];
    for (const [product, stats] of Object.entries(productStats)) {
        const total = stats.ok + stats.div;
        const accuracy = total > 0 ? (stats.ok / total) * 100 : 0;
        result.push({ product, ok: stats.ok, div: stats.div, total, accuracy });
    }

    // Sort by total descending
    result.sort((a, b) => b.total - a.total);
    return result;
}

// ── Filter items by product ─────────────────────────────────
function filterByProduct(items, prodFilter) {
    if (!prodFilter) return items;
    return items.filter(item => {
        const p = (item.Produto || '').replace(' (Deduzido)', '');
        return p === prodFilter;
    });
}

// ── Aviso de recorte de período (upload) ───────────────────
let trimAvisoDismissed = false;

function createTrimItem(parts) {
    const item = document.createElement('p');
    item.className = 'trim-aviso-item';
    parts.forEach(part => {
        if (typeof part === 'string') {
            item.appendChild(document.createTextNode(part));
        } else if (part.em) {
            const em = document.createElement('em');
            em.textContent = part.em;
            item.appendChild(em);
        } else if (part.strong) {
            const strong = document.createElement('strong');
            strong.textContent = part.strong;
            item.appendChild(strong);
        }
    });
    return item;
}

function createDateDetails(datas, label) {
    const details = document.createElement('details');
    details.className = 'trim-aviso-details';
    const summary = document.createElement('summary');
    summary.textContent = label;
    const datesEl = document.createElement('div');
    datesEl.className = 'trim-aviso-dates';
    datesEl.textContent = datas.join(' · ');
    details.appendChild(summary);
    details.appendChild(datesEl);
    return details;
}

function renderTrimAviso(data) {
    const section = document.getElementById('trim-aviso-section');
    const titleEl = document.getElementById('trim-aviso-title');
    const content = document.getElementById('trim-aviso-content');
    if (!section || !content || !titleEl) return;

    const recorte = data && data.avisos && data.avisos.recorte_periodo;
    if (!recorte || trimAvisoDismissed) {
        section.classList.add('hidden');
        return;
    }

    titleEl.textContent = 'Parte dos arquivos não entrou nesta análise';

    content.replaceChildren();

    const periodo = recorte.periodo_utilizado || {};
    if (periodo.inicio && periodo.fim) {
        const periodoLabel = periodo.inicio === periodo.fim
            ? periodo.inicio
            : `${periodo.inicio} a ${periodo.fim}`;
        content.appendChild(createTrimItem([
            'Comparamos somente o período ',
            { strong: periodoLabel },
            ', quando a planilha Excel e o relatório PDF têm pesagens ao mesmo tempo.',
        ]));
    }

    const ex = recorte.excel_ignorados || {};
    if (ex.total > 0) {
        const numDias = (ex.datas || []).length;
        const diasLabel = numDias === 1 ? '1 dia' : `${numDias} dias`;
        content.appendChild(createTrimItem([
            { strong: String(ex.total) },
            ex.total === 1 ? ' linha da planilha Excel ficou de fora' : ' linhas da planilha Excel ficaram de fora',
            ' — o PDF do OpenPort não traz pesagens nesses ',
            { strong: diasLabel },
            '.',
        ]));
        if (numDias > 0) {
            const verLabel = numDias === 1
                ? 'Ver a data ignorada na planilha'
                : `Ver as ${numDias} datas ignoradas na planilha`;
            content.appendChild(createDateDetails(ex.datas, verLabel));
        }
    }

    const pdf = recorte.pdf_ignorados || {};
    if (pdf.total > 0) {
        const numDias = (pdf.datas || []).length;
        const diasLabel = numDias === 1 ? '1 dia' : `${numDias} dias`;
        content.appendChild(createTrimItem([
            { strong: String(pdf.total) },
            pdf.total === 1 ? ' pesagem do PDF ficou de fora' : ' pesagens do PDF ficaram de fora',
            ' — não há registro correspondente na planilha Excel nesses ',
            { strong: diasLabel },
            '.',
        ]));
        if (numDias > 0) {
            const verLabel = numDias === 1
                ? 'Ver a data ignorada no PDF'
                : `Ver as ${numDias} datas ignoradas no PDF`;
            content.appendChild(createDateDetails(pdf.datas, verLabel));
        }
    }

    section.classList.remove('hidden');
}

// ── Render Dashboard ────────────────────────────────────────
function renderDashboard(data, filters) {
    if (data) globalAuditData = data;
    const currentData = globalAuditData;
    if (!currentData) return;

    const activeFilters = filters || getLegacyFilters();
    const { filteredOk, filteredDiv, filteredVolume } = applyFilters(currentData, activeFilters);

    const totalOk = filteredOk.length;
    const totalDiv = filteredDiv.length;
    const totalProcessado = totalOk + totalDiv;
    const pctOk = totalProcessado > 0 ? (totalOk / totalProcessado) * 100 : 0;
    const pctDiv = totalProcessado > 0 ? (totalDiv / totalProcessado) * 100 : 0;

    // Period (dinâmico conforme filtros)
    const periodText = document.getElementById('period-text');
    periodText.textContent = detectPeriodFromItems(
        filteredOk, filteredDiv, activeFilters.dateStart, activeFilters.dateEnd
    );

    // Timestamp
    const footerTs = document.getElementById('footer-timestamp');
    const now = new Date();
    footerTs.textContent = `${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

    // ── Compliance ring (confiabilidade)
    const confPercent = document.getElementById('confidence-percent');
    const confRing = document.getElementById('compliance-ring');
    const confOkCount = document.getElementById('conf-ok-count');
    const confDivCount = document.getElementById('conf-div-count');
    const confSub = document.getElementById('confidence-sub');

    confPercent.textContent = formatPercent(pctOk);
    if (confSub) {
        confSub.textContent = formatViagensCount(totalProcessado);
    }

    let tier = 'low';
    if (pctOk >= 80) tier = 'high';
    else if (pctOk >= 50) tier = 'medium';

    if (confRing) {
        confRing.className = 'compliance-ring ' + tier;
        requestAnimationFrame(() => {
            confRing.style.setProperty('--ring-pct', pctOk);
        });
    }

    confOkCount.textContent = totalOk;
    confDivCount.textContent = totalDiv;

    renderTrimAviso(currentData);

    // ── Product Conformity Bars
    const productAccuracy = calculateProductAccuracy(filteredOk, filteredDiv);
    renderProductBars(productAccuracy);

    // ── Volume Charts
    let chartVolumeRecords = filteredVolume;
    const limit = activeFilters.chartDaysLimit || 'all';
    if (limit && limit !== 'all') {
        const numDays = parseInt(limit, 10);
        const uniqueDates = [...new Set(filteredVolume.map(r => r.data))].sort((a, b) => {
            const da = parseBrDate(a) || new Date(0);
            const db = parseBrDate(b) || new Date(0);
            return da - db;
        });
        if (uniqueDates.length > numDays) {
            const lastNDates = uniqueDates.slice(-numDays);
            const dateSet = new Set(lastNDates);
            chartVolumeRecords = filteredVolume.filter(r => dateSet.has(r.data));
        }
    }

    const bucketWeek = shouldBucketByWeek(chartVolumeRecords);
    const volumeAgg = aggregateVolume(chartVolumeRecords, bucketWeek);
    renderVolumeCharts(volumeAgg);

    const valVolume = document.getElementById('val-volume');
    const subVolume = document.getElementById('sub-volume');
    if (valVolume) {
        const kgStr = formatChartKg(volumeAgg.totalToneladas).replace(/\s*kg/i, '');
        valVolume.innerHTML = `${kgStr}<span style="font-size: 0.55em; font-weight: 500; color: var(--text-secondary); margin-left: 4px;">kg</span>`;
    }
    if (subVolume) {
        const scopeLabel = activeFilters.volumeScope === 'ok' ? 'OK' : 'Total';
        subVolume.textContent = `${formatViagensCount(volumeAgg.totalViagens)} · ${scopeLabel}`;
    }

    // ── KPI Cards (animated counters)
    animateCounter(document.getElementById('val-total'), totalProcessado);
    animateCounter(document.getElementById('val-ok'), totalOk);
    animateCounter(document.getElementById('val-divergencias'), totalDiv);

    // Sub-info
    document.getElementById('sub-total').textContent = 'conciliadas no período';
    document.getElementById('sub-ok').textContent = totalProcessado > 0 ? formatPercent(pctOk) + ' do total' : '—';
    document.getElementById('sub-div').textContent = totalProcessado > 0 ? formatPercent(pctDiv) + ' do total' : '—';

    // Worst Product KPI
    const kpiWorst = document.getElementById('kpi-worst-product');
    const worstPctEl = document.getElementById('val-worst-pct');
    const worstLabelEl = document.getElementById('label-worst-product');
    const worstSubEl = document.getElementById('sub-worst-product');

    if (productAccuracy.length > 0) {
        // Find worst accuracy (exclude products with 0 total)
        const withData = productAccuracy.filter(p => p.total > 0);
        if (withData.length > 0) {
            const worst = withData.reduce((min, p) => p.accuracy < min.accuracy ? p : min, withData[0]);
            worstPctEl.textContent = formatPercent(worst.accuracy);
            
            if (worst.accuracy >= 100) {
                worstLabelEl.textContent = 'Conformidade';
                worstSubEl.textContent = 'Todos os produtos 100%';
                worstSubEl.className = 'kpi-sub text-success';
                if (kpiWorst) {
                    kpiWorst.classList.remove('accent');
                    kpiWorst.classList.add('success');
                }
            } else {
                worstLabelEl.textContent = 'Menor Acurácia';
                worstSubEl.textContent = `${worst.product} (${worst.div} erro${worst.div !== 1 ? 's' : ''})`;
                worstSubEl.className = 'kpi-sub text-warning';
                if (kpiWorst) {
                    kpiWorst.classList.remove('success');
                    kpiWorst.classList.add('accent');
                }
            }
        } else {
            worstPctEl.textContent = '—';
            worstLabelEl.textContent = 'Menor Acurácia';
            worstSubEl.textContent = 'Sem dados';
            worstSubEl.className = 'kpi-sub text-tertiary';
            if (kpiWorst) {
                kpiWorst.classList.remove('success');
                kpiWorst.classList.add('accent');
            }
        }
    } else {
        worstPctEl.textContent = '—';
        worstLabelEl.textContent = 'Menor Acurácia';
        worstSubEl.textContent = 'Sem dados';
        worstSubEl.className = 'kpi-sub text-tertiary';
        if (kpiWorst) {
            kpiWorst.classList.remove('success');
            kpiWorst.classList.add('accent');
        }
    }

    // Highlight danger card if has divergences
    const kpiDiv = document.getElementById('kpi-divergencias');
    if (totalDiv > 0) {
        kpiDiv.classList.add('has-issues');
    } else {
        kpiDiv.classList.remove('has-issues');
    }

    // Badges
    const badgeDiv = document.getElementById('badge-divergencias');
    // badgeOk removido
    badgeDiv.textContent = totalDiv;
    // badgeOk.textContent removido

    // Pulse animation on divergence badge
    if (totalDiv > 0) {
        badgeDiv.classList.add('pulse');
    } else {
        badgeDiv.classList.remove('pulse');
    }

    // Filter count
    const isFiltered = activeFilters.dateStart || activeFilters.dateEnd || activeFilters.placa || activeFilters.produto;
    const totalAll = (currentData.ok || []).length + (currentData.divergencias || []).length;
    if (isFiltered) {
        filterCount.textContent = `Mostrando ${totalProcessado} de ${totalAll} viagens`;
    } else {
        filterCount.textContent = '';
    }

    // ── Divergências Table
    renderDivergencias(filteredDiv);

    // ── Pesagens OK Table
    // renderOkTable removido
}

// ── Render Product Conformity Chips ─────────────────────────
function renderProductBars(productAccuracy) {
    const container = document.getElementById('product-bars-container');
    const section = document.getElementById('product-conformity');
    if (!container) return;
    container.replaceChildren();

    if (productAccuracy.length === 0) {
        if (section) section.style.display = 'none';
        return;
    }
    if (section) section.style.display = '';

    productAccuracy.forEach((p, idx) => {
        const chip = document.createElement('div');
        const badgeClass = getProductBadgeClass(p.product);
        chip.className = 'product-chip accent-' + badgeClass;
        chip.title = `${p.product}: ${p.ok} OK, ${p.div} divergência(s)`;
        chip.style.animation = `fadeInUp 0.35s var(--ease-out) ${idx * 40}ms forwards`;
        chip.style.opacity = '0';

        const head = document.createElement('div');
        head.className = 'product-chip-head';

        const name = document.createElement('span');
        name.className = 'product-chip-name';
        name.textContent = p.product;
        head.appendChild(name);

        const pct = document.createElement('span');
        pct.className = 'product-chip-pct';
        if (p.accuracy < 50) pct.classList.add('low');
        else if (p.accuracy < 80) pct.classList.add('medium');
        pct.textContent = formatPercent(p.accuracy);
        head.appendChild(pct);

        chip.appendChild(head);

        const bar = document.createElement('div');
        bar.className = 'product-chip-bar';

        const barOk = document.createElement('div');
        barOk.className = 'product-chip-bar-ok';
        bar.appendChild(barOk);

        const barDiv = document.createElement('div');
        barDiv.className = 'product-chip-bar-div';
        bar.appendChild(barDiv);

        chip.appendChild(bar);

        const count = document.createElement('div');
        count.className = 'product-chip-count';
        count.textContent = `${p.total} ${p.total === 1 ? 'viagem' : 'viagens'}`;
        chip.appendChild(count);

        container.appendChild(chip);

        requestAnimationFrame(() => {
            setTimeout(() => {
                const okPct = p.total > 0 ? (p.ok / p.total) * 100 : 0;
                const divPct = p.total > 0 ? (p.div / p.total) * 100 : 0;
                barOk.style.width = okPct + '%';
                barDiv.style.width = divPct + '%';
            }, 80 + idx * 40);
        });
    });
}

// ── Render Divergências ─────────────────────────────────────
function renderDivergencias(items) {
    const tbody = document.getElementById('tbody-divergencias');
    const table = tbody ? tbody.closest('table') : null;
    const thead = table ? table.querySelector('thead') : null;
    tbody.replaceChildren();

    const section = document.getElementById('section-divergencias');

    if (items.length === 0) {
        if (section) section.style.display = 'none';
        return;
    }
    
    if (section) section.style.display = 'block';
    if (thead) thead.classList.remove('hidden');

    items.forEach(item => {
        const tr = document.createElement('tr');

        // Placa
        const tdPlaca = document.createElement('td');
        tdPlaca.className = 'text-left';
        if (item.Status === 'Erro de Placa' && item.Placa_Excel && item.Placa_PDF) {
            tdPlaca.appendChild(createPlateDiff(item.Placa_Excel, item.Placa_PDF, 'EXCEL', 'PDF'));
        } else {
            const placaStrong = document.createElement('strong');
            placaStrong.textContent = item.Placa;
            tdPlaca.appendChild(placaStrong);
        }
        tr.appendChild(tdPlaca);

        // Data
        const tdData = document.createElement('td');
        tdData.className = 'text-center';
        let dataStr = item.Data || '—';
        if (dataStr !== '—' && !dataStr.includes(':')) {
            dataStr = `${dataStr} (Excel)`;
        }
        tdData.textContent = dataStr;
        tr.appendChild(tdData);

        // Produto
        const tdProduto = document.createElement('td');
        tdProduto.className = 'text-left';
        tdProduto.appendChild(createProductBadge(item.Produto || ''));
        tr.appendChild(tdProduto);

        // Tipo do Erro (badge colorido por tipo)
        const tdStatus = document.createElement('td');
        tdStatus.className = 'text-left';
        const spanBadge = document.createElement('span');
        spanBadge.className = 'badge ' + getErrorBadgeClass(item.Status);
        const badgeIcon = document.createElement('i');
        badgeIcon.className = 'ph ' + getErrorIcon(item.Status);
        spanBadge.appendChild(badgeIcon);
        const badgeText = document.createTextNode(' ' + (item.Status || 'Erro'));
        spanBadge.appendChild(badgeText);
        tdStatus.appendChild(spanBadge);
        tr.appendChild(tdStatus);

        // Detalhe
        const tdDetalhe = document.createElement('td');
        tdDetalhe.textContent = item.Detalhe;
        tdDetalhe.className = 'text-left cell-detalhe';
        tr.appendChild(tdDetalhe);

        tbody.appendChild(tr);
    });
}

// ── Empty State ─────────────────────────────────────────────
function renderEmptyState(tbody, colspan, iconClass, title, desc) {
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.colSpan = colspan;

    const wrapper = document.createElement('div');
    wrapper.className = 'empty-state';

    const icon = document.createElement('i');
    icon.className = 'ph ' + iconClass;
    wrapper.appendChild(icon);

    const h4 = document.createElement('div');
    h4.className = 'empty-title';
    h4.textContent = title;
    wrapper.appendChild(h4);

    const p = document.createElement('div');
    p.className = 'empty-desc';
    p.textContent = desc;
    wrapper.appendChild(p);

    td.appendChild(wrapper);
    tr.appendChild(td);
    tbody.appendChild(tr);
}

// ── Filters ─────────────────────────────────────────────────
function getCurrentFilters() {
    return getLegacyFilters();
}

function clearAllFilters() {
    resetFilterState();
    if (filterDateInput) filterDateInput.value = '';
    if (searchInput) searchInput.value = '';
    if (filterProdutoSelect) filterProdutoSelect.value = '';
    if (dateRangePicker) dateRangePicker.clear();
    document.querySelectorAll('.scope-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.scope === 'ok');
    });
    document.querySelectorAll('.limit-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.limit === 'all');
    });
    renderDashboard(null, getLegacyFilters());
}

if (btnFilter) {
    btnFilter.addEventListener('click', () => {
        renderDashboard(null, getLegacyFilters());
    });
}

if (btnClearFilter) {
    btnClearFilter.addEventListener('click', clearAllFilters);
}

// Debounced search
let searchTimeout = null;
if (searchInput) {
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            renderDashboard(null, getCurrentFilters());
        }, 250);
    });
}

// Date input also triggers filter (atalho dia único)
if (filterDateInput) {
    filterDateInput.addEventListener('change', () => {
        const val = filterDateInput.value;
        if (val) {
            filterState.dateStart = val;
            filterState.dateEnd = val;
            if (dateRangePicker) {
                dateRangePicker.setDate([val, val], false);
            }
        }
        renderDashboard(null, getLegacyFilters());
    });
}

// Product filter triggers re-render
if (filterProdutoSelect) {
    filterProdutoSelect.addEventListener('change', () => {
        renderDashboard(null, getCurrentFilters());
    });
}

// ── Fullscreen ──────────────────────────────────────────────
const btnFullscreen = document.getElementById('btn-fullscreen');
if (btnFullscreen) {
    btnFullscreen.addEventListener('click', () => {
        if (document.fullscreenElement) {
            document.exitFullscreen();
        } else {
            document.documentElement.requestFullscreen();
        }
    });

    document.addEventListener('fullscreenchange', () => {
        const icon = btnFullscreen.querySelector('i');
        const textNode = btnFullscreen.childNodes[1];
        if (document.fullscreenElement) {
            icon.className = 'ph ph-arrows-in';
            if (textNode) textNode.textContent = ' Sair';
        } else {
            icon.className = 'ph ph-monitor';
            if (textNode) textNode.textContent = ' Apresentação';
        }
    });
}

// ── Exportar CSV ────────────────────────────────────────────
const btnExport = document.getElementById('btn-export');
if (btnExport) {
    btnExport.addEventListener('click', () => {
        if (!globalAuditData) {
            showError('Nenhum dado para exportar. Processe os arquivos primeiro.');
            return;
        }

        const now = new Date();
        const dateStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;

        let csv = `AUDITORIA CODEBA - Gerado em ${dateStr}\n`;
        csv += `Período: ${detectPeriod(globalAuditData)}\n`;
        csv += `Total: ${(globalAuditData.ok || []).length + (globalAuditData.divergencias || []).length} viagens\n\n`;

        csv += 'DIVERGÊNCIAS\n';
        csv += 'Placa;Data;Produto;Tipo do Erro;Detalhe\n';
        (globalAuditData.divergencias || []).forEach(item => {
            const placa = (item.Placa || '').replace(/;/g, ' ');
            const data = (item.Data || '').replace(/;/g, ' ');
            const produto = (item.Produto || '').replace(/;/g, ' ');
            const status = (item.Status || '').replace(/;/g, ' ');
            const detalhe = (item.Detalhe || '').replace(/;/g, ' ');
            csv += `${placa};${data};${produto};${status};${detalhe}\n`;
        });

        csv += '\nPESAGENS OK\n';
        csv += 'Placa;Data;Produto;Cliente;Peso Bruto (kg);Tara (kg);Peso Liquido (kg);Status\n';
        (globalAuditData.ok || []).forEach(item => {
            const placa = (item.Placa || '').replace(/;/g, ' ');
            const data = (item.Data || '').replace(/;/g, ' ');
            const produto = (item.Produto || '').replace(/;/g, ' ');
            const cliente = (item.Cliente || '').replace(/;/g, ' ');
            const pesoLiquido = item['Peso Liquido'] || (item['Peso Bruto'] - item.Tara);
            csv += `${placa};${data};${produto};${cliente};${item['Peso Bruto']};${item.Tara};${pesoLiquido};OK\n`;
        });

        // BOM UTF-8 para Excel brasileiro
        const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `auditoria_codeba_${dateStr}.csv`;
        link.click();
        URL.revokeObjectURL(url);
    });
}

// ── Gerar Relatório PDF ──────────────────────────────────────
const btnReport = document.getElementById('btn-report');
if (btnReport) {
    btnReport.addEventListener('click', () => {
        if (!globalAuditData) {
            showError('Nenhum dado para exportar. Processe os arquivos primeiro.');
            return;
        }

        const runId = typeof currentRunId !== 'undefined' ? currentRunId : (globalAuditData.run_id || null);
        if (!runId) {
            showError('ID da auditoria não encontrado.');
            return;
        }

        const filters = getLegacyFilters();
        const params = new URLSearchParams();
        if (filters.placa) params.append('placa', filters.placa);
        if (filters.produto) params.append('produto', filters.produto);
        if (filters.dateStart) params.append('date_start', filters.dateStart);
        if (filters.dateEnd) params.append('date_end', filters.dateEnd);

        const url = `/api/runs/${runId}/report?${params.toString()}`;
        const link = document.createElement('a');
        link.href = url;
        link.download = '';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });
}



// ── Date Range (Flatpickr) ──────────────────────────────────
function initDateRangePicker() {
    const periodBadge = document.getElementById('period-badge');
    const popover = document.getElementById('date-range-popover');
    const rangeInput = document.getElementById('date-range-input');

    if (!rangeInput || typeof flatpickr === 'undefined') return;

    dateRangePicker = flatpickr(rangeInput, {
        mode: 'range',
        locale: 'pt',
        dateFormat: 'd/m/Y',
        onClose(selectedDates) {
            if (selectedDates.length === 2) {
                const fmt = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
                filterState.dateStart = fmt(selectedDates[0]);
                filterState.dateEnd = fmt(selectedDates[1]);
                if (filterDateInput) filterDateInput.value = '';
                renderDashboard(null, getLegacyFilters());
            }
        },
    });

    if (periodBadge && popover) {
        periodBadge.addEventListener('click', (e) => {
            e.stopPropagation();
            popover.classList.toggle('hidden');
            const rect = periodBadge.getBoundingClientRect();
            popover.style.top = (rect.bottom + 8) + 'px';
            popover.style.left = Math.max(8, rect.left) + 'px';
        });
        document.addEventListener('click', (e) => {
            if (!popover.contains(e.target) && !periodBadge.contains(e.target)) {
                popover.classList.add('hidden');
            }
        });
    }

    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const preset = btn.dataset.preset;
            const today = new Date();
            const fmt = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

            if (preset === 'all') {
                filterState.dateStart = null;
                filterState.dateEnd = null;
                if (dateRangePicker) dateRangePicker.clear();
                if (filterDateInput) filterDateInput.value = '';
            } else if (preset === 'today') {
                const iso = fmt(today);
                filterState.dateStart = iso;
                filterState.dateEnd = iso;
                if (dateRangePicker) dateRangePicker.setDate([today, today]);
            } else if (preset === '7d') {
                const start = new Date(today);
                start.setDate(start.getDate() - 6);
                filterState.dateStart = fmt(start);
                filterState.dateEnd = fmt(today);
                if (dateRangePicker) dateRangePicker.setDate([start, today]);
            } else if (preset === '30d') {
                const start = new Date(today);
                start.setDate(start.getDate() - 29);
                filterState.dateStart = fmt(start);
                filterState.dateEnd = fmt(today);
                if (dateRangePicker) dateRangePicker.setDate([start, today]);
            }
            renderDashboard(null, getLegacyFilters());
            if (popover) popover.classList.add('hidden');
        });
    });
}

// ── Volume Scope Toggle ─────────────────────────────────────
document.querySelectorAll('.scope-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.scope-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        filterState.volumeScope = btn.dataset.scope;
        renderDashboard(null, getLegacyFilters());
    });
});

// ── Chart Days Limit Toggle ─────────────────────────────────
document.querySelectorAll('.limit-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.limit-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        filterState.chartDaysLimit = btn.dataset.limit;
        renderDashboard(null, getLegacyFilters());
    });
});

// ── History Integration ─────────────────────────────────────
initHistory((data) => {
    globalAuditData = data;
    if (data.run_id) setCurrentRunId(data.run_id);
    trimAvisoDismissed = false;
    populateProductFilter(data);
    clearAllFilters();
});

const trimAvisoDismiss = document.getElementById('trim-aviso-dismiss');
if (trimAvisoDismiss) {
    trimAvisoDismiss.addEventListener('click', () => {
        trimAvisoDismissed = true;
        const section = document.getElementById('trim-aviso-section');
        if (section) section.classList.add('hidden');
    });
}

initDateRangePicker();

// ── Help Drawer Integration ──────────────────────────────────
const btnHelp = document.getElementById('btn-help');
const helpDrawer = document.getElementById('help-drawer');
const helpOverlay = document.getElementById('help-overlay');
const helpClose = document.getElementById('help-close');

if (btnHelp && helpDrawer && helpOverlay) {
    btnHelp.addEventListener('click', () => {
        helpDrawer.classList.add('open');
        helpOverlay.classList.add('open');
    });
}

function closeHelpDrawer() {
    if (helpDrawer) helpDrawer.classList.remove('open');
    if (helpOverlay) helpOverlay.classList.remove('open');
}

if (helpClose) helpClose.addEventListener('click', closeHelpDrawer);
if (helpOverlay) helpOverlay.addEventListener('click', closeHelpDrawer);

window.addEventListener('resize', () => {
    if (typeof resizeCharts === 'function') resizeCharts();
});
