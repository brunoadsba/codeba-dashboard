// ============================================================
// CODEBA — Analytics helpers (filtros, agregação de volume)
// ============================================================

const filterState = {
    dateStart: null,
    dateEnd: null,
    placa: '',
    produto: '',
    volumeScope: 'ok',
};

const PRODUCT_COLORS = {
    'LITIO': '#a78bfa',
    'LÍTIO': '#a78bfa',
    'MANGANES': '#f59e0b',
    'MANGANÊS': '#f59e0b',
    'MILHO': '#eab308',
    'NIQUEL': '#64748b',
    'NÍQUEL': '#64748b',
    'ÓXIDO DE MAGNÉSIO': '#38bdf8',
    'OXIDO DE MAGNESIO': '#38bdf8',
    'Outros': '#94a3b8',
};

function parseBrDate(str) {
    if (!str) return null;
    const parts = str.split('/');
    if (parts.length !== 3) return null;
    const d = new Date(parseInt(parts[2], 10), parseInt(parts[1], 10) - 1, parseInt(parts[0], 10));
    return isNaN(d.getTime()) ? null : d;
}

function parseIsoDate(str) {
    if (!str) return null;
    const parts = str.split('-');
    if (parts.length !== 3) return null;
    const d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
    return isNaN(d.getTime()) ? null : d;
}

function brDateToIso(brDate) {
    const d = parseBrDate(brDate);
    if (!d) return null;
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function isoToBrDate(iso) {
    const d = parseIsoDate(iso);
    if (!d) return null;
    return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`;
}

function isDateInRange(brDate, dateStart, dateEnd) {
    const d = parseBrDate(brDate);
    if (!d) return false;
    if (dateStart) {
        const start = parseIsoDate(dateStart);
        if (start && d < start) return false;
    }
    if (dateEnd) {
        const end = parseIsoDate(dateEnd);
        if (end) {
            const endDay = new Date(end.getFullYear(), end.getMonth(), end.getDate(), 23, 59, 59);
            if (d > endDay) return false;
        }
    }
    return true;
}

function normalizeProductName(prod) {
    if (!prod) return 'Outros';
    const clean = prod.replace(' (Deduzido)', '').trim();
    if (!clean || clean === 'Não Identificado' || clean.startsWith('Ambíguo')) return 'Outros';
    return clean;
}

function getProductColor(produto) {
    const key = normalizeProductName(produto);
    if (PRODUCT_COLORS[key]) return PRODUCT_COLORS[key];
    const upper = key.toUpperCase();
    for (const [k, v] of Object.entries(PRODUCT_COLORS)) {
        if (upper.includes(k) || k.includes(upper)) return v;
    }
    return PRODUCT_COLORS.Outros;
}

function applyFilters(data, filters = filterState) {
    let filteredOk = data.ok || [];
    let filteredDiv = data.divergencias || [];
    let volumeRecords = (data.volume && data.volume.records) ? [...data.volume.records] : [];

    if (filters.dateStart || filters.dateEnd) {
        filteredOk = filteredOk.filter(i => isDateInRange(i.Data, filters.dateStart, filters.dateEnd));
        filteredDiv = filteredDiv.filter(i => isDateInRange(i.Data, filters.dateStart, filters.dateEnd));
        volumeRecords = volumeRecords.filter(r => isDateInRange(r.data, filters.dateStart, filters.dateEnd));
    } else if (filters.date) {
        const [y, m, d] = filters.date.split('-');
        if (y && m && d) {
            const brDate = `${d}/${m}/${y}`;
            filteredOk = filteredOk.filter(i => i.Data === brDate);
            filteredDiv = filteredDiv.filter(i => i.Data === brDate);
            volumeRecords = volumeRecords.filter(r => r.data === brDate);
        }
    }

    if (filters.placa) {
        const q = filters.placa.toUpperCase().replace(/[^A-Z0-9]/g, '');
        if (q.length > 0) {
            filteredOk = filteredOk.filter(i => (i.Placa || '').toUpperCase().includes(q));
            filteredDiv = filteredDiv.filter(i => (i.Placa || '').toUpperCase().includes(q));
            volumeRecords = volumeRecords.filter(r => (r.placa || '').toUpperCase().includes(q));
        }
    }

    if (filters.produto) {
        filteredOk = filteredOk.filter(i => normalizeProductName(i.Produto) === filters.produto);
        filteredDiv = filteredDiv.filter(i => normalizeProductName(i.Produto) === filters.produto);
        volumeRecords = volumeRecords.filter(r => r.produto === filters.produto);
    }

    if (filters.volumeScope === 'ok') {
        volumeRecords = volumeRecords.filter(r => r.is_ok);
    }

    return { filteredOk, filteredDiv, filteredVolume: volumeRecords };
}

function aggregateVolume(records, bucketByWeek = false) {
    const byDateProduct = {};
    const byProduct = {};
    let totalToneladas = 0;
    let totalViagens = 0;

    records.forEach(r => {
        let dateKey = r.data;
        if (bucketByWeek) {
            const d = parseBrDate(r.data);
            if (d) {
                const jan1 = new Date(d.getFullYear(), 0, 1);
                const week = Math.ceil(((d - jan1) / 86400000 + jan1.getDay() + 1) / 7);
                dateKey = `S${week}/${d.getFullYear()}`;
            }
        }
        if (!byDateProduct[dateKey]) byDateProduct[dateKey] = {};
        if (!byDateProduct[dateKey][r.produto]) {
            byDateProduct[dateKey][r.produto] = { toneladas: 0, viagens: 0 };
        }
        byDateProduct[dateKey][r.produto].toneladas += r.toneladas;
        byDateProduct[dateKey][r.produto].viagens += r.viagens || 1;

        if (!byProduct[r.produto]) byProduct[r.produto] = { toneladas: 0, viagens: 0 };
        byProduct[r.produto].toneladas += r.toneladas;
        byProduct[r.produto].viagens += r.viagens || 1;

        totalToneladas += r.toneladas;
        totalViagens += r.viagens || 1;
    });

    const dates = Object.keys(byDateProduct).sort((a, b) => {
        const da = parseBrDate(a) || new Date(0);
        const db = parseBrDate(b) || new Date(0);
        if (a.startsWith('S') && b.startsWith('S')) return a.localeCompare(b);
        return da - db;
    });

    const products = [...new Set(records.map(r => r.produto))].sort();

    return { byDateProduct, byProduct, dates, products, totalToneladas, totalViagens };
}

function shouldBucketByWeek(records) {
    const dates = records.map(r => parseBrDate(r.data)).filter(Boolean);
    if (dates.length < 2) return false;
    dates.sort((a, b) => a - b);
    const diffDays = (dates[dates.length - 1] - dates[0]) / 86400000;
    return diffDays > 90;
}

function detectPeriodFromItems(okItems, divItems, dateStart, dateEnd) {
    if (dateStart && dateEnd) {
        const startBr = isoToBrDate(dateStart);
        const endBr = isoToBrDate(dateEnd);
        if (startBr === endBr) return startBr;
        const fmt = (iso) => {
            const d = parseIsoDate(iso);
            return d ? `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}` : '';
        };
        const y = parseIsoDate(dateEnd)?.getFullYear() || '';
        return `${fmt(dateStart)} — ${fmt(dateEnd)}/${y}`;
    }
    if (dateStart) return isoToBrDate(dateStart);
    const allDates = [];
    okItems.forEach(i => { if (i.Data) allDates.push(i.Data); });
    divItems.forEach(i => { if (i.Data) allDates.push(i.Data); });
    if (allDates.length === 0) return '—';
    const parsed = allDates.map(parseBrDate).filter(d => d && !isNaN(d));
    if (parsed.length === 0) return '—';
    parsed.sort((a, b) => a - b);
    const min = parsed[0];
    const max = parsed[parsed.length - 1];
    const fmt = (d) => `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`;
    if (min.getTime() === max.getTime()) return fmt(min) + '/' + min.getFullYear();
    return fmt(min) + ' — ' + fmt(max) + '/' + max.getFullYear();
}

const formatTons = (val) => new Intl.NumberFormat('pt-BR', {
    maximumFractionDigits: 1,
    minimumFractionDigits: 0,
}).format(val) + ' t';

function formatViagensCount(n) {
    return `${n} viagem${n !== 1 ? 's' : ''}`;
}

function resetFilterState() {
    filterState.dateStart = null;
    filterState.dateEnd = null;
    filterState.placa = '';
    filterState.produto = '';
    filterState.volumeScope = 'ok';
}

function syncFilterStateFromInputs() {
    const searchInput = document.getElementById('search-placa');
    const filterProdutoSelect = document.getElementById('filter-produto');
    if (searchInput) filterState.placa = searchInput.value;
    if (filterProdutoSelect) filterState.produto = filterProdutoSelect.value;
}

function getLegacyFilters() {
    syncFilterStateFromInputs();
    return {
        dateStart: filterState.dateStart,
        dateEnd: filterState.dateEnd,
        placa: filterState.placa,
        produto: filterState.produto,
        volumeScope: filterState.volumeScope,
    };
}
