/* Professional time-series forecast + this-year bar comparison */

const FORECAST_SERIES = [
    { key: 'research', label: 'Research', color: '#6b0f1a' },
    { key: 'extensions', label: 'Extensions', color: '#8a6d12' },
    { key: 'admin', label: 'Admin Works', color: '#014421' },
];

const _forecastState = {};

function roundForecast(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return 0;
    return Math.round(n * 10) / 10;
}

function applyChartDefaults() {
    if (typeof Chart === 'undefined') return;
    Chart.defaults.font.family = 'Inter, system-ui, sans-serif';
    Chart.defaults.font.size = 11;
    Chart.defaults.color = '#4b5563';
    Chart.defaults.elements.line.tension = 0;
    Chart.defaults.elements.line.borderJoinStyle = 'miter';
    Chart.defaults.elements.line.borderCapStyle = 'butt';
    Chart.defaults.elements.point.radius = 0;
    Chart.defaults.plugins.legend.display = false;
    if (Chart.Filler && typeof Chart.register === 'function') {
        try { Chart.register(Chart.Filler); } catch (_) { /* already registered */ }
    }
}

function buildForecastDatasets(payload, visible) {
    const histYears = payload.years || [];
    const futureYears = payload.future_years || [];
    const histLen = histYears.length;
    const datasets = [];

    FORECAST_SERIES.forEach((series) => {
        if (visible && visible[series.key] === false) return;
        const hist = (payload.historical && payload.historical[series.key]) || [];
        const fc = (payload.forecast && payload.forecast[series.key]) || {};
        const mean = (fc.mean || []).map(roundForecast);

        const histLine = hist.concat(mean.map(() => null));
        if (histLen > 0 && histLine.length) histLine[histLen - 1] = hist[histLen - 1];

        const forecastLine = hist.map(() => null);
        if (histLen > 0) forecastLine[histLen - 1] = hist[histLen - 1];
        mean.forEach((value) => forecastLine.push(value));

        datasets.push({
            label: series.label,
            data: histLine,
            borderColor: series.color,
            backgroundColor: series.color,
            borderWidth: 1.6,
            pointRadius: 0,
            pointHoverRadius: 3,
            pointHitRadius: 8,
            pointBackgroundColor: series.color,
            pointBorderWidth: 0,
            tension: 0,
            spanGaps: false,
            order: 1,
        });
        datasets.push({
            label: series.label + ' forecast',
            data: forecastLine,
            borderColor: series.color,
            backgroundColor: series.color,
            borderWidth: 1.6,
            borderDash: [4, 3],
            pointRadius: 0,
            pointHoverRadius: 3,
            pointHitRadius: 8,
            pointBackgroundColor: series.color,
            tension: 0,
            spanGaps: false,
            order: 2,
        });
    });

    return {
        labels: histYears.concat(futureYears).map(String),
        datasets,
        splitIndex: histLen - 1,
    };
}

const forecastSplitPlugin = {
    id: 'forecastSplit',
    afterDraw(chart) {
        const splitIndex = chart.$splitIndex;
        const { ctx, chartArea, scales } = chart;
        if (splitIndex == null || splitIndex < 0 || !chartArea || !scales.x) return;
        const x = scales.x.getPixelForTick(splitIndex);
        if (!Number.isFinite(x)) return;
        ctx.save();
        ctx.beginPath();
        ctx.setLineDash([2, 3]);
        ctx.strokeStyle = '#9ca3af';
        ctx.lineWidth = 1;
        ctx.moveTo(x, chartArea.top);
        ctx.lineTo(x, chartArea.bottom);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = '#6b7280';
        ctx.font = '500 10px Inter, system-ui, sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText('forecast', Math.min(x + 6, chartArea.right - 52), chartArea.top + 12);
        ctx.restore();
    },
};

function renderForecastLegend(payload, legendId, stateKey) {
    const el = document.getElementById(legendId);
    if (!el) return;
    const state = _forecastState[stateKey];
    const visible = (state && state.visible) || {};
    el.innerHTML = FORECAST_SERIES.map((series) => {
        const off = visible[series.key] === false ? ' is-off' : '';
        return `<button type="button" class="forecast-legend-item${off}" data-series="${series.key}">
            <span class="forecast-legend-swatch" style="border-color:${series.color}"></span>
            ${series.label}
        </button>`;
    }).join('');
    el.querySelectorAll('[data-series]').forEach((btn) => {
        btn.addEventListener('click', () => {
            const key = btn.getAttribute('data-series');
            const current = _forecastState[stateKey];
            if (!current) return;
            current.visible[key] = !current.visible[key];
            redrawForecast(stateKey);
        });
    });
}

function renderForecastSummary(payload, summaryId) {
    const el = document.getElementById(summaryId);
    if (!el) return;
    const prev = payload.prev_mix || {};
    const mix = payload.mix || {};
    const next = payload.next_year || {};
    const prevYear = payload.previous_year || (payload.current_year - 1);
    const currentYear = payload.current_year || new Date().getFullYear();
    const nextYear = (payload.future_years && payload.future_years[0]) || (currentYear + 1);

    el.innerHTML = `
        <table class="forecast-table">
            <thead>
                <tr>
                    <th></th>
                    <th>${prevYear}</th>
                    <th>${currentYear}</th>
                    <th>${nextYear}</th>
                </tr>
            </thead>
            <tbody>
                ${FORECAST_SERIES.map((series) => {
        const prevVal = roundForecast(prev[series.key]);
        const now = roundForecast(mix[series.key]);
        const nxt = roundForecast(next[series.key]);
        return `<tr>
                        <td><span class="forecast-legend-swatch" style="border-color:${series.color};display:inline-block;vertical-align:middle;margin-right:8px;"></span>${series.label}</td>
                        <td>${prevVal}</td>
                        <td>${now}</td>
                        <td>${nxt}</td>
                    </tr>`;
    }).join('')}
            </tbody>
        </table>`;
}

function renderOutputMix(payload, canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return null;
    applyChartDefaults();
    const prev = payload.prev_mix || {};
    const mix = payload.mix || {};
    const next = payload.next_year || {};
    const prevVals = FORECAST_SERIES.map((series) => roundForecast(prev[series.key]));
    const currentVals = FORECAST_SERIES.map((series) => roundForecast(mix[series.key]));
    const nextVals = FORECAST_SERIES.map((series) => roundForecast(next[series.key]));
    const maxVal = Math.max(1, ...prevVals, ...currentVals, ...nextVals);
    const prevYear = payload.previous_year || ((payload.current_year || 0) - 1);
    const currentYear = payload.current_year || new Date().getFullYear();
    const nextYear = (payload.future_years && payload.future_years[0]) || (currentYear + 1);
    return new Chart(canvas, {
        type: 'bar',
        data: {
            labels: FORECAST_SERIES.map((s) => s.label),
            datasets: [
                {
                    label: String(prevYear),
                    data: prevVals,
                    backgroundColor: 'rgba(255, 255, 255, 0)',
                    borderColor: FORECAST_SERIES.map((s) => s.color),
                    borderWidth: 1.5,
                    barThickness: 10,
                },
                {
                    label: String(currentYear),
                    data: currentVals,
                    backgroundColor: FORECAST_SERIES.map((s) => s.color),
                    borderWidth: 0,
                    barThickness: 10,
                },
                {
                    label: String(nextYear),
                    data: nextVals,
                    backgroundColor: FORECAST_SERIES.map((s) => s.color + '55'),
                    borderColor: FORECAST_SERIES.map((s) => s.color),
                    borderWidth: 1,
                    barThickness: 10,
                },
            ],
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 1500,
                easing: 'easeOutQuart',
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        boxWidth: 10,
                        boxHeight: 10,
                        font: { size: 10 },
                        color: '#6b7280',
                    },
                },
                tooltip: {
                    backgroundColor: '#111827',
                    padding: 8,
                    cornerRadius: 2,
                },
            },
            scales: {
                x: {
                    beginAtZero: true,
                    suggestedMax: maxVal * 1.2,
                    ticks: { precision: 0, color: '#6b7280', font: { size: 10 } },
                    grid: { color: '#eef0f2', drawBorder: false },
                    border: { display: true, color: '#d1d5db' },
                },
                y: {
                    ticks: { color: '#374151', font: { size: 11 } },
                    grid: { display: false },
                    border: { display: true, color: '#d1d5db' },
                },
            },
        },
    });
}

function renderForecastChart(payload, canvasId, visible) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return null;
    applyChartDefaults();
    const built = buildForecastDatasets(payload, visible);
    const chart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: built.labels,
            datasets: built.datasets,
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 2000,
                easing: 'easeInOutQuart',
                onProgress: function (animation) {
                    const chartInstance = animation.chart;
                    const ctx = chartInstance.ctx;
                    ctx.save();
                    // Enable line drawing animation
                    const datasets = chartInstance.data.datasets;
                    datasets.forEach((dataset, i) => {
                        const meta = chartInstance.getDatasetMeta(i);
                        if (!meta.hidden && meta.data.length > 0) {
                            // Animate the line being drawn
                            const progress = animation.currentStep / animation.numSteps;
                            if (dataset.borderDash) {
                                // Animate dash offset for forecast lines
                                ctx.setLineDash(dataset.borderDash);
                                ctx.lineDashOffset = 10 * (1 - progress);
                            }
                        }
                    });
                    ctx.restore();
                },
            },
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: false },
                filler: { propagate: false },
                tooltip: {
                    backgroundColor: '#111827',
                    padding: 8,
                    cornerRadius: 2,
                    titleFont: { size: 11, weight: '600' },
                    bodyFont: { size: 11 },
                    displayColors: true,
                    boxWidth: 8,
                    boxHeight: 2,
                    filter: (item) => Boolean(item.raw || item.raw === 0),
                    callbacks: {
                        label: (ctx) => {
                            if (ctx.raw === null || ctx.raw === undefined) return null;
                            return ` ${ctx.dataset.label}: ${ctx.raw}`;
                        },
                    },
                },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { precision: 0, color: '#6b7280', font: { size: 10 }, padding: 6 },
                    grid: { color: '#eef0f2', drawBorder: false },
                    border: { display: true, color: '#d1d5db' },
                    title: {
                        display: true,
                        text: 'Count',
                        color: '#6b7280',
                        font: { size: 10, weight: '500' },
                    },
                },
                x: {
                    ticks: { color: '#6b7280', font: { size: 10 }, padding: 4 },
                    grid: { display: false },
                    border: { display: true, color: '#d1d5db' },
                    title: {
                        display: true,
                        text: 'Year',
                        color: '#6b7280',
                        font: { size: 10, weight: '500' },
                    },
                },
            },
        },
        plugins: [forecastSplitPlugin],
    });
    chart.$splitIndex = built.splitIndex;
    return chart;
}

function redrawForecast(stateKey) {
    const state = _forecastState[stateKey];
    if (!state || !state.payload) return;
    if (state.lineChart) {
        state.lineChart.destroy();
        state.lineChart = null;
    }
    state.lineChart = renderForecastChart(state.payload, state.lineCanvasId, state.visible);
    renderForecastLegend(state.payload, state.lineLegendId, stateKey);
}

async function loadDashboardForecast(options) {
    const {
        lineCanvasId,
        mixCanvasId,
        legendId,
        summaryId,
        subtitleId,
        lineLegendId,
        scope,
    } = options;
    const lineChartRef = options.lineChartRef || { current: null };
    const mixChartRef = options.mixChartRef || { current: null };
    const subtitle = document.getElementById(subtitleId);
    const summary = document.getElementById(summaryId);
    const stateKey = lineCanvasId || 'forecast';

    // Show loading state
    if (subtitle) subtitle.textContent = 'Loading forecast data...';
    if (summary) summary.innerHTML = '<div class="forecast-stat-note" style="text-align:center;padding:20px;color:#9ca3af;"><div class="spinner" style="width:20px;height:20px;border:2px solid #e5e7eb;border-top-color:#6b0f1a;border-radius:50%;animation:spin 0.6s linear infinite;margin:0 auto 8px;"></div>Loading...</div>';

    try {
        const url = scope === 'member' ? '/api/dashboard/forecast?scope=member' : '/api/dashboard/forecast';
        const res = await fetch(url);
        if (!res.ok) throw new Error('Forecast request failed');
        const payload = await res.json();
        if (payload.error) throw new Error(payload.error);

        if (lineChartRef.current) {
            lineChartRef.current.destroy();
            lineChartRef.current = null;
        }
        if (mixChartRef.current) {
            mixChartRef.current.destroy();
            mixChartRef.current = null;
        }

        const visible = {};
        FORECAST_SERIES.forEach((s) => { visible[s.key] = true; });
        const lineChart = renderForecastChart(payload, lineCanvasId, visible);
        const mixChart = renderOutputMix(payload, mixCanvasId);
        lineChartRef.current = lineChart;
        mixChartRef.current = mixChart;

        _forecastState[stateKey] = {
            payload,
            visible,
            lineCanvasId,
            lineLegendId: lineLegendId || legendId,
            lineChart,
            mixChart,
        };

        renderForecastSummary(payload, summaryId);
        renderForecastLegend(payload, lineLegendId || legendId, stateKey);
        if (subtitle) {
            const demo = payload.demo ? 'Sample series · ' : '';
            const models = Object.values(payload.models || {});
            const usesArima = models.some((m) => String(m).startsWith('ARIMA'));
            subtitle.textContent = `${demo}Annual counts, ${payload.horizon || 3}-year ${usesArima ? 'ARIMA' : 'trend'} projection`;
        }
        return payload;
    } catch (err) {
        console.warn('Forecast load failed:', err);
        if (subtitle) subtitle.textContent = 'Could not load forecast. Try refreshing.';
        if (summary) summary.innerHTML = '<div class="forecast-stat-note">Forecast unavailable</div>';
        return null;
    }
}
