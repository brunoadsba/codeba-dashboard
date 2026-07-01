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
    fileInput.value = '';
    trimAvisoDismissed = false;
    discardedAvisoDismissed = false;
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
            discardedAvisoDismissed = false;
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

function fmtKg(val) {
    if (val == null || val === '') return '—';
    const n = Number(val);
    if (isNaN(n)) return '—';
    return n.toLocaleString('pt-BR') + ' kg';
}

function pesosFragment(item) {
    const pb = item['Peso Bruto'];
    const tara = item.Tara;
    const pl = item['Peso Liquido'] != null ? item['Peso Liquido'] : (pb - tara);
    const frag = document.createDocumentFragment();
    
    const container = document.createElement('div');
    container.className = 'pesos-single-line';
    
    function createPesoSpan(val, isLiq = false) {
        const span = document.createElement('span');
        span.className = 'peso-item' + (isLiq ? ' peso-liquido' : '');
        
        const num = document.createElement('span');
        num.textContent = fmtKg(val);
        span.appendChild(num);
        
        return span;
    }
    
    const brutoSpan = createPesoSpan(pb);
    
    const sep1 = document.createElement('span');
    sep1.className = 'peso-separator';
    sep1.textContent = '/';
    
    const taraSpan = createPesoSpan(tara);
    
    const sep2 = document.createElement('span');
    sep2.className = 'peso-separator';
    sep2.textContent = '/';
    
    const liqSpan = createPesoSpan(pl, true);
    
    container.appendChild(brutoSpan);
    container.appendChild(sep1);
    container.appendChild(taraSpan);
    container.appendChild(sep2);
    container.appendChild(liqSpan);
    
    frag.appendChild(container);
    return frag;
}

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
    if (!status) return 'badge-falta-pdf';
    const s = status.toLowerCase();
    if (s.includes('incompleta')) return 'badge-incompleta';
    if (s.includes('erro de placa')) return 'badge-erro-placa';
    if (s.includes('diferença') || s.includes('peso')) return 'badge-diferenca-peso';
    if (s.includes('falta no pdf')) return 'badge-falta-pdf';
    if (s.includes('falta no excel')) return 'badge-falta-excel';
    return 'badge-falta-pdf';
}

function getErrorIcon(status) {
    if (!status) return 'ph-warning-circle';
    const s = status.toLowerCase();
    if (s.includes('incompleta')) return 'ph-warning-octagon';
    if (s.includes('erro de placa')) return 'ph-identification-card';
    if (s.includes('diferença') || s.includes('peso')) return 'ph-scales';
    if (s.includes('falta no pdf')) return 'ph-file-pdf';
    if (s.includes('falta no excel')) return 'ph-file-x';
    return 'ph-warning-circle';
}

// ── Create Plate Diff Element (char-by-char highlighting) ───
function createPlateDiff(placa1, placa2, label1, label2) {
    const container = document.createElement('div');
    container.className = 'plate-diff-container';

    const sourceSpan = document.createElement('span');
    sourceSpan.className = 'plate-source-tag';
    sourceSpan.textContent = `${label1}:`;
    container.appendChild(sourceSpan);

    const diff1 = document.createElement('span');
    diff1.className = 'placa-diff';
    for (let i = 0; i < placa1.length; i++) {
        const charSpan = document.createElement('span');
        charSpan.className = (i < placa2.length && placa1[i] !== placa2[i]) ? 'char-diff' : 'char-ok';
        charSpan.textContent = placa1[i];
        diff1.appendChild(charSpan);
    }
    container.appendChild(diff1);

    const arrowSpan = document.createElement('span');
    arrowSpan.className = 'plate-arrow';
    arrowSpan.textContent = '→';
    container.appendChild(arrowSpan);

    const source2Span = document.createElement('span');
    source2Span.className = 'plate-source-tag';
    source2Span.textContent = `${label2}:`;
    container.appendChild(source2Span);

    const diff2 = document.createElement('span');
    diff2.className = 'placa-diff';
    for (let i = 0; i < placa2.length; i++) {
        const charSpan = document.createElement('span');
        charSpan.className = (i < placa1.length && placa1[i] !== placa2[i]) ? 'char-diff' : 'char-ok';
        charSpan.textContent = placa2[i];
        diff2.appendChild(charSpan);
    }
    container.appendChild(diff2);

    return container;
}

// ── Detect period from data ─────────────────────────────────
function detectPeriod(data) {
    const allDates = [];
    (data.ok || []).forEach(i => { if (i.Data) allDates.push(i.Data); });
    (data.divergencias || []).forEach(i => { if (i.Data) allDates.push(i.Data); });
    (data.notas_informativas || []).forEach(i => { if (i.Data) allDates.push(i.Data); });

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
let discardedAvisoDismissed = false;

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

// ── Aviso de registros descartados (dados inválidos/corrompidos) ───────────────────
function createDiscardedItem(parts) {
    const item = document.createElement('p');
    item.className = 'discarded-aviso-item';
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

function renderDiscardedAviso(data) {
    const section = document.getElementById('discarded-aviso-section');
    const content = document.getElementById('discarded-aviso-content');
    if (!section || !content) return;

    const descartados = data && data.avisos && data.avisos.registros_descartados;
    if (!descartados || discardedAvisoDismissed) {
        section.classList.add('hidden');
        return;
    }

    const excel = descartados.excel || [];
    const pdf = descartados.pdf || [];

    if (excel.length === 0 && pdf.length === 0) {
        section.classList.add('hidden');
        return;
    }

    content.replaceChildren();

    // Excel
    if (excel.length > 0) {
        const itemLabel = excel.length === 1 ? '1 registro da planilha Excel foi descartado' : `${excel.length} registros da planilha Excel foram descartados`;
        content.appendChild(createDiscardedItem([
            { strong: itemLabel },
            ' por conterem dados inconsistentes ou incompletos (por exemplo, placas em branco, datas corrompidas).'
        ]));

        const details = document.createElement('details');
        details.className = 'discarded-aviso-details';
        const summary = document.createElement('summary');
        summary.textContent = excel.length === 1 ? 'Ver registro descartado do Excel' : `Ver os ${excel.length} registros descartados do Excel`;
        details.appendChild(summary);

        const listEl = document.createElement('div');
        listEl.className = 'discarded-aviso-list';
        excel.forEach(item => {
            const line = document.createElement('div');
            line.style.marginBottom = '4px';
            line.appendChild(document.createTextNode(
                `Linha ${item.Linha} (Aba '${item.Aba}'): Placa="${item.Placa || '—'}", Data="${item.Data || '—'}" · Motivo: ${item.Motivo}`
            ));
            listEl.appendChild(line);
        });
        details.appendChild(listEl);
        content.appendChild(details);
    }

    // PDF
    if (pdf.length > 0) {
        const itemLabel = pdf.length === 1 ? '1 registro do relatório PDF foi descartado' : `${pdf.length} registros do relatório PDF foram descartados`;
        content.appendChild(createDiscardedItem([
            { strong: itemLabel },
            ' por conterem dados inconsistentes ou incompletos (por exemplo, placas em branco, datas corrompidas).'
        ]));

        const details = document.createElement('details');
        details.className = 'discarded-aviso-details';
        const summary = document.createElement('summary');
        summary.textContent = pdf.length === 1 ? 'Ver registro descartado do PDF' : `Ver os ${pdf.length} registros descartados do PDF`;
        details.appendChild(summary);

        const listEl = document.createElement('div');
        listEl.className = 'discarded-aviso-list';
        pdf.forEach(item => {
            const line = document.createElement('div');
            line.style.marginBottom = '4px';
            line.appendChild(document.createTextNode(
                `SEV: ${item.SEV || '—'} · Placa: "${item.Placa || '—'}", Data: "${item.Data || '—'}" · Motivo: ${item.Motivo}`
            ));
            listEl.appendChild(line);
        });
        details.appendChild(listEl);
        content.appendChild(details);
    }

    section.classList.remove('hidden');
}

// ── Render Dashboard ────────────────────────────────────────
function renderDashboard(data, filters) {
    if (data) globalAuditData = data;
    const currentData = globalAuditData;
    if (!currentData) return;

    const activeFilters = filters || getLegacyFilters();
    const { filteredOk, filteredDiv, filteredIncompletas, filteredVolume } = applyFilters(currentData, activeFilters);

    const totalOk = filteredOk.length;
    const totalDiv = filteredDiv.length;
    const totalIncompletas = (filteredIncompletas || []).length;
    const totalProcessado = totalOk + totalDiv + totalIncompletas;
    const denom = totalOk + totalDiv;
    const pctOk = denom > 0 ? (totalOk / denom) * 100 : 0;
    const pctDiv = denom > 0 ? (totalDiv / denom) * 100 : 0;

    // Period (dinâmico conforme filtros)
    const periodText = document.getElementById('period-text');
    periodText.textContent = detectPeriodFromItems(
        filteredOk, filteredDiv, activeFilters.dateStart, activeFilters.dateEnd
    );

    // Timestamp
    const footerTs = document.getElementById('footer-timestamp');
    const now = new Date();
    footerTs.textContent = `${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

    // Integrity Hash
    const integrityHashVal = document.getElementById('integrity-hash-val');
    if (integrityHashVal) {
        integrityHashVal.textContent = currentData.integrity_hash || '—';
    }

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
    renderDiscardedAviso(currentData);

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
        valVolume.replaceChildren();
        valVolume.appendChild(document.createTextNode(kgStr));
        const kgSpan = document.createElement('span');
        kgSpan.style.cssText = 'font-size: 0.55em; font-weight: 500; color: var(--text-secondary); margin-left: 4px;';
        kgSpan.textContent = 'kg';
        valVolume.appendChild(kgSpan);
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

    // Highlight danger card if has divergences
    const kpiDiv = document.getElementById('kpi-divergencias');
    if (totalDiv > 0) {
        kpiDiv.classList.add('has-issues');
    } else {
        kpiDiv.classList.remove('has-issues');
    }

    // Badges
    const badgeDiv = document.getElementById('badge-divergencias');
    const badgeIncompletas = document.getElementById('badge-incompletas');
    // badgeOk removido
    badgeDiv.textContent = totalDiv;
    if (badgeIncompletas) {
        badgeIncompletas.textContent = totalIncompletas;
    }
    // badgeOk.textContent removido

    // Pulse animation on divergence badge
    if (totalDiv > 0) {
        badgeDiv.classList.add('pulse');
    } else {
        badgeDiv.classList.remove('pulse');
    }

    // Filter count
    const isFiltered = activeFilters.dateStart || activeFilters.dateEnd || activeFilters.placa || activeFilters.produto;
    const totalAll = (currentData.ok || []).length + (currentData.divergencias || []).length + (currentData.notas_informativas || []).length;
    if (isFiltered) {
        filterCount.textContent = `Mostrando ${totalProcessado} de ${totalAll} viagens`;
    } else {
        filterCount.textContent = '';
    }

    // ── Divergências Table
    renderDivergencias(filteredDiv);

    // ── Pesagens Incompletas Table
    renderIncompletas(filteredIncompletas);

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

    items.forEach((item, idx) => {
        const tr = document.createElement('tr');
        tr.className = 'divergencia-row click-to-expand';
        tr.style.cursor = 'pointer';

        // Ítem
        const tdItem = document.createElement('td');
        tdItem.className = 'text-center col-item-cell';
        const itemSpan = document.createElement('span');
        itemSpan.className = 'item-number';
        itemSpan.textContent = String(idx + 1).padStart(2, '0');
        tdItem.appendChild(itemSpan);
        tr.appendChild(tdItem);

        // SEV
        const tdSev = document.createElement('td');
        tdSev.className = 'text-center col-sev-cell';
        if (item.SEV) {
            const sevSpan = document.createElement('span');
            sevSpan.className = 'sev-value';
            sevSpan.textContent = item.SEV;
            tdSev.appendChild(sevSpan);
        } else {
            tdSev.textContent = '—';
        }
        tr.appendChild(tdSev);

        // Placa
        const tdPlaca = document.createElement('td');
        tdPlaca.className = 'text-center col-placa-cell';
        
        const placaContainer = document.createElement('div');
        placaContainer.className = 'placa-cell-container';
        
        if (item.Status === 'Erro de Placa' && item.Placa_Excel && item.Placa_PDF) {
            // Linha 1: Placa corrigida (informação principal)
            const placaMain = document.createElement('div');
            placaMain.className = 'placa-main';
            placaMain.textContent = item.Placa_PDF;
            placaMain.title = `Original: ${item.Placa_Excel}`;
            placaContainer.appendChild(placaMain);
            
            // Linha 2: Placa original (detalhe sutil)
            const placaOriginal = document.createElement('div');
            placaOriginal.className = 'placa-original';
            placaOriginal.textContent = `Original: ${item.Placa_Excel}`;
            placaContainer.appendChild(placaOriginal);
        } else if (item.Status === 'Falta no Excel') {
            // Placa do PDF (sem correspondência no Excel)
            const placaMain = document.createElement('div');
            placaMain.className = 'placa-highlight';
            placaMain.textContent = item.Placa;
            placaContainer.appendChild(placaMain);
            
            const placaOriginal = document.createElement('div');
            placaOriginal.className = 'placa-original';
            placaOriginal.textContent = 'Fonte: PDF';
            placaContainer.appendChild(placaOriginal);
        } else {
            const placaStrong = document.createElement('strong');
            placaStrong.className = 'placa-highlight';
            placaStrong.textContent = item.Placa;
            placaContainer.appendChild(placaStrong);
        }
        
        tdPlaca.appendChild(placaContainer);
        tr.appendChild(tdPlaca);

        // Data / Hora
        const tdData = document.createElement('td');
        tdData.className = 'text-center col-data-cell';
        if (item.Data) {
            const parts = item.Data.split(' ');
            const dataStr = parts[0];
            const horaStr = parts[1] || '';
            
            const dateDiv = document.createElement('div');
            dateDiv.className = 'date-text';
            dateDiv.textContent = dataStr;
            
            const timeDiv = document.createElement('div');
            timeDiv.className = 'time-text';
            timeDiv.textContent = horaStr;
            
            tdData.appendChild(dateDiv);
            if (horaStr) tdData.appendChild(timeDiv);
        } else {
            tdData.textContent = '—';
        }
        tr.appendChild(tdData);

        // Produto
        const tdProduto = document.createElement('td');
        tdProduto.className = 'text-center col-produto-cell';
        tdProduto.appendChild(createProductBadge(item.Produto || ''));
        tr.appendChild(tdProduto);

        // Pesos (Bruto / Tara / Líquido)
        const tdPesos = document.createElement('td');
        tdPesos.className = 'pesos-cell text-center';
        tdPesos.replaceChildren(pesosFragment(item));
        tr.appendChild(tdPesos);

        // Status
        const tdStatus = document.createElement('td');
        tdStatus.className = 'text-center col-status-cell';
        
        const statusContainer = document.createElement('div');
        statusContainer.className = 'status-cell-container';
        
        const spanBadge = document.createElement('span');
        spanBadge.className = 'badge ' + getErrorBadgeClass(item.Status);
        
        const badgeIcon = document.createElement('i');
        badgeIcon.className = 'ph ' + getErrorIcon(item.Status);
        spanBadge.appendChild(badgeIcon);
        
        const badgeText = document.createTextNode(' ' + (item.Status || 'Erro'));
        spanBadge.appendChild(badgeText);
        statusContainer.appendChild(spanBadge);
        
        const chevronIcon = document.createElement('i');
        chevronIcon.className = 'ph ph-caret-down chevron-icon';
        statusContainer.appendChild(chevronIcon);
        
        tdStatus.appendChild(statusContainer);
        tr.appendChild(tdStatus);

        // Row Click to expand listener
        tr.addEventListener('click', (e) => {
            if (e.target.closest('button') || e.target.closest('a')) {
                return;
            }
            toggleRowExpansion(tr, item);
        });

        tbody.appendChild(tr);
    });
}

// ── Render Pesagens Incompletas ─────────────────────────────
function renderIncompletas(items) {
    const tbody = document.getElementById('tbody-incompletas');
    const table = tbody ? tbody.closest('table') : null;
    const thead = table ? table.querySelector('thead') : null;
    if (!tbody) return;
    tbody.replaceChildren();

    const section = document.getElementById('section-incompletas');

    if (!items || items.length === 0) {
        if (section) section.style.display = 'none';
        return;
    }
    
    if (section) section.style.display = 'block';
    if (thead) thead.classList.remove('hidden');

    items.forEach((item, idx) => {
        const tr = document.createElement('tr');
        tr.className = 'divergencia-row click-to-expand';
        tr.style.cursor = 'pointer';

        // Ítem
        const tdItem = document.createElement('td');
        tdItem.className = 'text-center col-item-cell';
        const itemSpan = document.createElement('span');
        itemSpan.className = 'item-number';
        itemSpan.textContent = String(idx + 1).padStart(2, '0');
        tdItem.appendChild(itemSpan);
        tr.appendChild(tdItem);

        // SEV
        const tdSev = document.createElement('td');
        tdSev.className = 'text-center col-sev-cell';
        if (item.SEV) {
            const sevSpan = document.createElement('span');
            sevSpan.className = 'sev-value';
            sevSpan.textContent = item.SEV;
            tdSev.appendChild(sevSpan);
        } else {
            tdSev.textContent = '—';
        }
        tr.appendChild(tdSev);

        // Placa
        const tdPlaca = document.createElement('td');
        tdPlaca.className = 'text-center col-placa-cell';
        
        const placaContainer = document.createElement('div');
        placaContainer.className = 'placa-cell-container';
        
        const placaStrong = document.createElement('strong');
        placaStrong.className = 'placa-highlight';
        placaStrong.textContent = item.Placa;
        placaContainer.appendChild(placaStrong);
        
        tdPlaca.appendChild(placaContainer);
        tr.appendChild(tdPlaca);

        // Data / Hora
        const tdData = document.createElement('td');
        tdData.className = 'text-center col-data-cell';
        if (item.Data) {
            const parts = item.Data.split(' ');
            const dataStr = parts[0];
            const horaStr = parts[1] || '';
            
            const dateDiv = document.createElement('div');
            dateDiv.className = 'date-text';
            dateDiv.textContent = dataStr;
            
            const timeDiv = document.createElement('div');
            timeDiv.className = 'time-text';
            timeDiv.textContent = horaStr;
            
            tdData.appendChild(dateDiv);
            if (horaStr) tdData.appendChild(timeDiv);
        } else {
            tdData.textContent = '—';
        }
        tr.appendChild(tdData);

        // Produto
        const tdProduto = document.createElement('td');
        tdProduto.className = 'text-center col-produto-cell';
        tdProduto.appendChild(createProductBadge(item.Produto || ''));
        tr.appendChild(tdProduto);

        // Pesos (Bruto / Tara / Líquido)
        const tdPesos = document.createElement('td');
        tdPesos.className = 'pesos-cell text-center';
        tdPesos.replaceChildren(pesosFragment(item));
        tr.appendChild(tdPesos);

        // Status
        const tdStatus = document.createElement('td');
        tdStatus.className = 'text-center col-status-cell';
        
        const statusContainer = document.createElement('div');
        statusContainer.className = 'status-cell-container';
        
        const spanBadge = document.createElement('span');
        spanBadge.className = 'badge ' + getErrorBadgeClass(item.Status);
        
        const badgeIcon = document.createElement('i');
        badgeIcon.className = 'ph ' + getErrorIcon(item.Status);
        spanBadge.appendChild(badgeIcon);
        
        const badgeText = document.createTextNode(' ' + (item.Status || 'Incompleta'));
        spanBadge.appendChild(badgeText);
        statusContainer.appendChild(spanBadge);
        
        const chevronIcon = document.createElement('i');
        chevronIcon.className = 'ph ph-caret-down chevron-icon';
        statusContainer.appendChild(chevronIcon);
        
        tdStatus.appendChild(statusContainer);
        tr.appendChild(tdStatus);

        // Row Click to expand listener
        tr.addEventListener('click', (e) => {
            if (e.target.closest('button') || e.target.closest('a')) {
                return;
            }
            toggleRowExpansion(tr, item);
        });

        tbody.appendChild(tr);
    });
}

// ── Toggle Row Expansion ────────────────────────────────────
function toggleRowExpansion(tr, item) {
    const nextTr = tr.nextElementSibling;
    const isExpanded = nextTr && nextTr.classList.contains('detail-row');
    const chevronIcon = tr.querySelector('.chevron-icon');
    
    if (isExpanded) {
        nextTr.remove();
        tr.classList.remove('expanded');
        if (chevronIcon) {
            chevronIcon.className = 'ph ph-caret-down chevron-icon';
        }
    } else {
        // Collapse other open detail rows for cleanliness
        const openDetailRows = document.querySelectorAll('.detail-row');
        openDetailRows.forEach(row => {
            const prev = row.previousElementSibling;
            if (prev) prev.classList.remove('expanded');
            const icon = prev ? prev.querySelector('.chevron-icon') : null;
            if (icon) icon.className = 'ph ph-caret-down chevron-icon';
            row.remove();
        });

        tr.classList.add('expanded');
        if (chevronIcon) {
            chevronIcon.className = 'ph ph-caret-up chevron-icon';
        }
        
        const detailTr = document.createElement('tr');
        detailTr.className = 'detail-row';
        
        const detailTd = document.createElement('td');
        detailTd.colSpan = 7;
        
        detailTd.appendChild(renderDetailPanel(item, tr));
        detailTr.appendChild(detailTd);
        tr.after(detailTr);
    }
}

// ── Render Expandable Detail Panel ──────────────────────────
function renderDetailPanel(item, tr) {
    const container = document.createElement('div');
    container.className = 'detail-panel-container fade-in';
    
    const grid = document.createElement('div');
    grid.className = 'detail-panel-grid';
    
    // --- CARD DE ERRO (Vermelho) ---
    const errorCard = document.createElement('div');
    errorCard.className = 'detail-card card-error';
    
    const errorHeader = document.createElement('div');
    errorHeader.className = 'card-title-header text-danger';
    
    const errorIcon = document.createElement('i');
    errorIcon.className = 'ph ph-warning-octagon';
    errorHeader.appendChild(errorIcon);
    
    const errorTitle = document.createElement('span');
    errorTitle.textContent = item.linha_erro_data ? ' ERRO DE DATA NO EXCEL' : ' ERRO DETECTADO';
    errorHeader.appendChild(errorTitle);
    errorCard.appendChild(errorHeader);
    
    const errorDesc = document.createElement('p');
    errorDesc.className = 'card-description';
    if (item.linha_erro_data) {
        errorDesc.appendChild(document.createTextNode('Registro presente no PDF '));
        const strong1 = document.createElement('strong');
        strong1.textContent = 'sem correspondência';
        errorDesc.appendChild(strong1);
        errorDesc.appendChild(document.createTextNode(' na planilha. Possível erro de digitação — encontrado registro com mesma placa e pesos na '));
        const strong2 = document.createElement('strong');
        strong2.textContent = 'Linha ' + item.linha_erro_data;
        errorDesc.appendChild(strong2);
        errorDesc.appendChild(document.createTextNode(' da aba '));
        const strong3 = document.createElement('strong');
        strong3.textContent = item.aba_erro_data || 'Plan5';
        errorDesc.appendChild(strong3);
        errorDesc.appendChild(document.createTextNode('.'));
    } else if (item.Status === 'Erro de Placa' && item.Placa_Excel && item.Placa_PDF) {
        errorDesc.appendChild(document.createTextNode('Placa '));
        const strongExcel = document.createElement('strong');
        strongExcel.textContent = `'${item.Placa_Excel}'`;
        errorDesc.appendChild(strongExcel);
        errorDesc.appendChild(document.createTextNode(' não confere. Corrigida para '));
        const strongPdf = document.createElement('strong');
        strongPdf.textContent = `'${item.Placa_PDF}'`;
        errorDesc.appendChild(strongPdf);
        errorDesc.appendChild(document.createTextNode('.'));
    } else {
        errorDesc.textContent = item.Detalhe || 'Registro presente no PDF sem correspondência na planilha.';
    }
    errorCard.appendChild(errorDesc);
    
    // Error Properties
    const errorProps = document.createElement('div');
    errorProps.className = 'detail-props-list';
    
    function addProp(list, label, val, valClass = '') {
        const row = document.createElement('div');
        row.className = 'prop-row';
        const lblSpan = document.createElement('span');
        lblSpan.className = 'prop-label';
        lblSpan.textContent = label;
        const valSpan = document.createElement('span');
        valSpan.className = 'prop-value ' + valClass;
        valSpan.textContent = val;
        row.appendChild(lblSpan);
        row.appendChild(valSpan);
        list.appendChild(row);
    }
    
    if (item.linha_erro_data) {
        addProp(errorProps, 'Arquivo', item.arquivo_erro_data || '—');
        addProp(errorProps, 'Aba', item.aba_erro_data || '—');
        addProp(errorProps, 'Linha', item.linha_erro_data);
        addProp(errorProps, 'Data no Excel', item.data_errada_excel || '—', 'text-danger');
        addProp(errorProps, 'Data no PDF', item.Data ? item.Data.split(' ')[0] : '—', 'text-success');
    } else if (item.Status === 'Erro de Placa') {
        addProp(errorProps, 'Placa no Excel', item.Placa_Excel || '—');
        addProp(errorProps, 'Placa no PDF', item.Placa_PDF || '—');
    } else {
        addProp(errorProps, 'Placa', item.Placa || '—');
        addProp(errorProps, 'Data / Hora', item.Data || '—');
        addProp(errorProps, 'Produto', item.Produto || '—');
    }
    errorCard.appendChild(errorProps);
    grid.appendChild(errorCard);
    
    // --- CARD DE CONTEXTO (Verde) ---
    const contextCard = document.createElement('div');
    contextCard.className = 'detail-card card-context';
    
    const contextHeader = document.createElement('div');
    contextHeader.className = 'card-title-header text-success';
    
    const contextIcon = document.createElement('i');
    contextIcon.className = 'ph ph-info';
    contextHeader.appendChild(contextIcon);
    
    const contextTitle = document.createElement('span');
    contextTitle.textContent = ' CONTEXTO DA PLACA';
    contextHeader.appendChild(contextTitle);
    contextCard.appendChild(contextHeader);
    
    const viagensOk = item.viagens_ok_no_dia || 0;
    const isErroPlaca = item.Status === 'Erro de Placa' && item.Placa_Excel && item.Placa_PDF;
    const hasZeroTrips = isErroPlaca && viagensOk === 0;
    
    const contextDesc = document.createElement('p');
    contextDesc.className = 'card-description';
    contextDesc.appendChild(document.createTextNode('A placa '));
    const strongPlaca = document.createElement('strong');
    strongPlaca.textContent = item.Placa;
    contextDesc.appendChild(strongPlaca);
    contextDesc.appendChild(document.createTextNode(' possui '));
    const strongCount = document.createElement('strong');
    strongCount.textContent = viagensOk + ' ' + (viagensOk === 1 ? 'viagem' : 'viagens');
    contextDesc.appendChild(strongCount);
    
    if (hasZeroTrips) {
        const warnBadge = document.createElement('span');
        warnBadge.className = 'badge-inline-warning';
        warnBadge.innerHTML = '<i class="ph ph-warning"></i> Sem vínculo';
        contextDesc.appendChild(document.createTextNode(' '));
        contextDesc.appendChild(warnBadge);
    }
    
    contextDesc.appendChild(document.createTextNode(' registrada e validada neste dia.'));
    contextCard.appendChild(contextDesc);
    
    // Context Properties
    const contextProps = document.createElement('div');
    contextProps.className = 'detail-props-list';
    
    let diffDaysText = '—';
    if (item.linha_erro_data && item.data_errada_excel && item.Data) {
        const parseDateBR = (str) => {
            if (!str) return null;
            const datePart = str.split(' ')[0];
            const parts = datePart.split('/');
            if (parts.length < 3) return null;
            return new Date(parts[2], parts[1] - 1, parts[0]);
        };
        const d1 = parseDateBR(item.Data);
        const d2 = parseDateBR(item.data_errada_excel);
        if (d1 && d2) {
            const diffTime = Math.abs(d1 - d2);
            const days = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            diffDaysText = `${days} dias`;
        }
    }
    
    addProp(contextProps, 'Viagens OK no dia', viagensOk);
    addProp(contextProps, 'Produto esperado', item.Produto ? item.Produto.replace(' (Deduzido)', '') : '—');
    addProp(contextProps, 'Diferença de data', diffDaysText);
    
    contextCard.appendChild(contextProps);
    grid.appendChild(contextCard);
    
    container.appendChild(grid);
    
    // --- AÇÕES ---
    const actionsWrapper = document.createElement('div');
    actionsWrapper.className = 'detail-actions-wrapper';
    
    // Botão principal: Corrigir Placa (apenas para Erro de Placa)
    if (isErroPlaca) {
        const btnCorrigirPlaca = document.createElement('button');
        btnCorrigirPlaca.className = 'btn-detail-action btn-primary';
        btnCorrigirPlaca.title = 'Funcionalidade em desenvolvimento';
        btnCorrigirPlaca.innerHTML = '<i class="ph ph-check-circle"></i> Corrigir Placa';
        btnCorrigirPlaca.addEventListener('click', (e) => {
            e.stopPropagation();
            handleNotImplemented('Corrigir Placa');
        });
        actionsWrapper.appendChild(btnCorrigirPlaca);
        
        // Botão: Ignorar e manter original
        const btnIgnorar = document.createElement('button');
        btnIgnorar.className = 'btn-detail-action btn-outline';
        btnIgnorar.title = 'Funcionalidade em desenvolvimento';
        btnIgnorar.innerHTML = '<i class="ph ph-x"></i> Ignorar';
        btnIgnorar.addEventListener('click', (e) => {
            e.stopPropagation();
            handleNotImplemented('Ignorar');
        });
        actionsWrapper.appendChild(btnIgnorar);
        
        // Botão: Cadastrar viagem (quando 0 viagens)
        if (hasZeroTrips) {
            const btnCadastrar = document.createElement('button');
            btnCadastrar.className = 'btn-detail-action btn-small';
            btnCadastrar.title = 'Funcionalidade em desenvolvimento';
            btnCadastrar.innerHTML = '<i class="ph ph-plus"></i> Cadastrar viagem';
            btnCadastrar.addEventListener('click', (e) => {
                e.stopPropagation();
                handleNotImplemented('Cadastrar viagem', 'modal');
            });
            actionsWrapper.appendChild(btnCadastrar);
        }
    } else {
        // Botão para outros tipos de erro (data, etc.)
        const btnCorrect = document.createElement('button');
        btnCorrect.className = 'btn-detail-action btn-primary';
        btnCorrect.title = 'Funcionalidade em desenvolvimento';
        btnCorrect.innerHTML = '<i class="ph ph-pencil-simple"></i> Corrigir';
        btnCorrect.addEventListener('click', (e) => {
            e.stopPropagation();
            handleNotImplemented('Corrigir');
        });
        actionsWrapper.appendChild(btnCorrect);
    }
    
    // Botão: Marcar como revisado (neutro, à direita)
    const btnReview = document.createElement('button');
    btnReview.className = 'btn-detail-action btn-ghost';
    const isRevisado = tr.classList.contains('revisado');
    btnReview.innerHTML = isRevisado ? '<i class="ph ph-arrow-u-up-left"></i> Reabrir' : '<i class="ph ph-check"></i> Revisado';
    btnReview.addEventListener('click', (e) => {
        e.stopPropagation();
        tr.classList.toggle('revisado');
        const nowRevisado = tr.classList.contains('revisado');
        btnReview.innerHTML = nowRevisado ? '<i class="ph ph-arrow-u-up-left"></i> Reabrir' : '<i class="ph ph-check"></i> Revisado';
        
        const statusTd = tr.querySelector('.col-status-cell');
        if (statusTd) {
            if (nowRevisado) {
                statusTd.dataset.originalHtml = statusTd.innerHTML;
                statusTd.innerHTML = `
                    <div class="status-cell-container">
                        <span class="badge badge-revisado"><i class="ph ph-check-circle"></i> Revisado</span>
                        <i class="ph ph-caret-down chevron-icon"></i>
                    </div>
                `;
            } else {
                statusTd.innerHTML = statusTd.dataset.originalHtml || statusTd.innerHTML;
            }
        }
        
        showToast(nowRevisado ? 'Divergência marcada como revisada.' : 'Divergência reaberta.', nowRevisado ? 'success' : 'info');
        
        setTimeout(() => {
            if (nowRevisado) {
                toggleRowExpansion(tr, item);
            }
        }, 450);
    });
    actionsWrapper.appendChild(btnReview);
    
    // Botão: Abrir no Excel (apenas para erros de data)
    if (item.linha_erro_data) {
        const btnExcel = document.createElement('button');
        btnExcel.className = 'btn-detail-action btn-outline';
        btnExcel.title = 'Funcionalidade em desenvolvimento';
        btnExcel.innerHTML = '<i class="ph ph-table"></i> Abrir no Excel';
        btnExcel.addEventListener('click', (e) => {
            e.stopPropagation();
            handleNotImplemented('Abrir no Excel');
        });
        actionsWrapper.appendChild(btnExcel);
    }
    
    const btnCollapse = document.createElement('button');
    btnCollapse.className = 'btn-detail-collapse';
    btnCollapse.innerHTML = '<i class="ph ph-caret-up"></i>';
    btnCollapse.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleRowExpansion(tr, item);
    });
    actionsWrapper.appendChild(btnCollapse);
    
    container.appendChild(actionsWrapper);
    return container;
}

// ── Show Toast Notification Helper ──────────────────────────
function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast toast-${type} fade-in`;
    
    let icon = 'ph-info';
    if (type === 'success') icon = 'ph-check-circle';
    else if (type === 'warning') icon = 'ph-warning';
    
    toast.innerHTML = `<i class="ph ${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// ── Feature Not Implemented Handler ──────────────────────────
const featureModal = document.getElementById('feature-modal');
const featureModalTitle = document.getElementById('feature-modal-title');
const featureModalMessage = document.getElementById('feature-modal-message');
const featureModalClose = document.getElementById('feature-modal-close');

function showFeatureModal(title, message) {
    if (!featureModal) return;
    featureModalTitle.textContent = title;
    featureModalMessage.textContent = message;
    featureModal.classList.remove('hidden');
    void featureModal.offsetWidth;
    featureModal.classList.add('active');
}

function hideFeatureModal() {
    if (!featureModal) return;
    featureModal.classList.remove('active');
    setTimeout(() => featureModal.classList.add('hidden'), 300);
}

if (featureModalClose) {
    featureModalClose.addEventListener('click', hideFeatureModal);
}
if (featureModal) {
    featureModal.addEventListener('click', (e) => {
        if (e.target === featureModal) hideFeatureModal();
    });
}

function handleNotImplemented(actionName, mode = 'toast') {
    if (mode === 'modal') {
        showFeatureModal(
            'Funcionalidade em Desenvolvimento',
            `A ação "${actionName}" está em nosso roadmap e será lançada em breve.`
        );
    } else {
        showToast(`"${actionName}" será liberada na próxima versão.`, 'warning');
    }
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
        csv += `Total: ${(globalAuditData.ok || []).length + (globalAuditData.divergencias || []).length + (globalAuditData.notas_informativas || []).length} viagens\n\n`;

        csv += 'DIVERGÊNCIAS\n';
        csv += 'Ítem;SEV;Placa;Data;Produto;Peso Bruto (kg);Tara (kg);Peso Líquido (kg);Tipo do Erro;Detalhe\n';
        (globalAuditData.divergencias || []).forEach((item, idx) => {
            const itemNum = String(idx + 1).padStart(2, '0');
            const placa = (item.Placa || '').replace(/;/g, ' ');
            const data = (item.Data || '').replace(/;/g, ' ');
            const produto = (item.Produto || '').replace(/;/g, ' ');
            const status = (item.Status || '').replace(/;/g, ' ');
            const detalhe = (item.Detalhe || '').replace(/;/g, ' ');
            const sev = (item.SEV || '').replace(/;/g, ' ');
            const plVal = item['Peso Liquido'] != null ? item['Peso Liquido'] : (item['Peso Bruto'] - item.Tara);
            csv += `${itemNum};${sev};${placa};${data};${produto};${item['Peso Bruto']};${item.Tara};${plVal};${status};${detalhe}\n`;
        });

        csv += '\nPESAGENS INCOMPLETAS (OPENPORT)\n';
        csv += 'Ítem;SEV;Placa;Data;Produto;Peso Bruto (kg);Tara (kg);Peso Líquido (kg);Tipo do Erro;Detalhe\n';
        (globalAuditData.notas_informativas || []).forEach((item, idx) => {
            const itemNum = String(idx + 1).padStart(2, '0');
            const placa = (item.Placa || '').replace(/;/g, ' ');
            const data = (item.Data || '').replace(/;/g, ' ');
            const produto = (item.Produto || '').replace(/;/g, ' ');
            const status = (item.Status || '').replace(/;/g, ' ');
            const detalhe = (item.Detalhe || '').replace(/;/g, ' ');
            const sev = (item.SEV || '').replace(/;/g, ' ');
            const plVal = item['Peso Liquido'] != null ? item['Peso Liquido'] : (item['Peso Bruto'] - item.Tara);
            csv += `${itemNum};${sev};${placa};${data};${produto};${item['Peso Bruto']};${item.Tara};${plVal};${status};${detalhe}\n`;
        });

        csv += '\nPESAGENS OK\n';
        csv += 'Ítem;SEV;Placa;Data;Produto;Cliente;Peso Bruto (kg);Tara (kg);Peso Liquido (kg);Status\n';
        (globalAuditData.ok || []).forEach(item => {
            const placa = (item.Placa || '').replace(/;/g, ' ');
            const data = (item.Data || '').replace(/;/g, ' ');
            const produto = (item.Produto || '').replace(/;/g, ' ');
            const sev = (item.SEV || '').replace(/;/g, ' ');
            const cliente = (item.Cliente || '').replace(/;/g, ' ');
            const pesoLiquido = item['Peso Liquido'] || (item['Peso Bruto'] - item.Tara);
            csv += `${item['Ítem'] || ''};${sev};${placa};${data};${produto};${cliente};${item['Peso Bruto']};${item.Tara};${pesoLiquido};OK\n`;
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
    discardedAvisoDismissed = false;
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

const discardedAvisoDismiss = document.getElementById('discarded-aviso-dismiss');
if (discardedAvisoDismiss) {
    discardedAvisoDismiss.addEventListener('click', () => {
        discardedAvisoDismissed = true;
        const section = document.getElementById('discarded-aviso-section');
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
