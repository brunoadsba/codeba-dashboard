// ============================================================
// CODEBA — Chart.js wrappers
// ============================================================

let stackedChartInstance = null;
let donutChartInstance = null;

function getChartTheme() {
    const style = getComputedStyle(document.body);
    return {
        text: style.getPropertyValue('--text-primary').trim() || '#e2e8f0',
        textSecondary: style.getPropertyValue('--text-secondary').trim() || '#94a3b8',
        grid: style.getPropertyValue('--border').trim() || '#334155',
        surface: style.getPropertyValue('--bg-surface').trim() || '#1e293b',
    };
}

function destroyCharts() {
    if (stackedChartInstance) {
        stackedChartInstance.destroy();
        stackedChartInstance = null;
    }
    if (donutChartInstance) {
        donutChartInstance.destroy();
        donutChartInstance = null;
    }
}

function renderVolumeCharts(aggregated, sectionEl) {
    const stackedCanvas = document.getElementById('chart-volume-stacked');
    const donutCanvas = document.getElementById('chart-volume-donut');
    const totalEl = document.getElementById('volume-total-label');
    const section = sectionEl || document.getElementById('analytics-section');

    if (!stackedCanvas || !donutCanvas) return;

    destroyCharts();

    const { byDateProduct, byProduct, dates, products, totalToneladas, totalViagens } = aggregated;

    if (totalEl) {
        totalEl.textContent = formatChartKg(totalToneladas);
    }

    if (dates.length === 0 || products.length === 0) {
        if (section) section.style.display = 'none';
        return;
    }

    if (section) section.style.display = 'block';

    const theme = getChartTheme();

    const datasets = products.map(prod => ({
        label: prod,
        data: dates.map(d => (byDateProduct[d] && byDateProduct[d][prod]) ? byDateProduct[d][prod].toneladas : 0),
        backgroundColor: getProductColor(prod),
        borderColor: getProductColor(prod),
        borderWidth: 1,
        borderRadius: 2,
        stack: 'volume',
    }));

    stackedChartInstance = new Chart(stackedCanvas, {
        type: 'bar',
        data: { labels: dates, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: theme.text, boxWidth: 12, padding: 12, font: { size: 11 } },
                },
                tooltip: {
                    backgroundColor: theme.surface,
                    titleColor: theme.text,
                    bodyColor: theme.textSecondary,
                    callbacks: {
                        label(ctx) {
                            const viagens = byDateProduct[ctx.label]?.[ctx.dataset.label]?.viagens || 0;
                            return `${ctx.dataset.label}: ${formatChartKg(ctx.parsed.y)} (${formatViagensCount(viagens)})`;
                        },
                    },
                },
            },
            scales: {
                x: {
                    stacked: true,
                    ticks: { color: theme.textSecondary, maxRotation: 45, autoSkip: true, maxTicksLimit: dates.length > 31 ? 15 : 31 },
                    grid: { color: theme.grid },
                },
                y: {
                    stacked: true,
                    ticks: {
                        color: theme.textSecondary,
                        callback: (v) => new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 }).format(v * 1000) + ' kg',
                    },
                    grid: { color: theme.grid },
                    title: { display: true, text: 'Quilogramas (kg)', color: theme.textSecondary, font: { size: 11 } },
                },
            },
        },
    });

    const productLabels = Object.keys(byProduct);
    const productValues = productLabels.map(p => byProduct[p].toneladas);
    const productColors = productLabels.map(p => getProductColor(p));

    donutChartInstance = new Chart(donutCanvas, {
        type: 'doughnut',
        data: {
            labels: productLabels,
            datasets: [{
                data: productValues,
                backgroundColor: productColors,
                borderColor: theme.surface,
                borderWidth: 2,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '62%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: theme.text, boxWidth: 10, padding: 8, font: { size: 10 } },
                },
                tooltip: {
                    backgroundColor: theme.surface,
                    titleColor: theme.text,
                    bodyColor: theme.textSecondary,
                    callbacks: {
                        label(ctx) {
                            const pct = totalToneladas > 0 ? ((ctx.parsed / totalToneladas) * 100).toFixed(1) : 0;
                            return `${ctx.label}: ${formatChartKg(ctx.parsed)} (${pct}%)`;
                        },
                    },
                },
            },
        },
    });

    const subEl = document.getElementById('volume-total-sub');
    if (subEl) {
        subEl.textContent = formatViagensCount(totalViagens);
    }
}

function resizeCharts() {
    if (stackedChartInstance) stackedChartInstance.resize();
    if (donutChartInstance) donutChartInstance.resize();
}
