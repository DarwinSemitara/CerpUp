/* ══════════════════════════════════════════════════════════════
   CERP Admin - Dashboard Page JavaScript
   ══════════════════════════════════════════════════════════════ */

let pubChart = null;
let tapChartInst = null;

// Current selected year and type for dashboard
let currentDashboardYear = new Date().getFullYear();
let currentResearchType = 'all'; // all, publications, proposal, implementation

let pubDataByYearAndType = {}; // {year: {type: [12 months]}}
let extDataByYear = {}; // Extension data by year

// Fetch real data from API
(async function loadDashboardStats() {
    try {
        const res = await fetch('/api/dashboard/stats-by-year');
        if (res.ok) {
            const stats = await res.json();

            // Populate pubData with all years and types
            pubDataByYearAndType = stats.publications_by_year || {};

            // Populate extension data by year
            extDataByYear = stats.extensions_by_year || {};

            // Set current year as default
            currentDashboardYear = new Date().getFullYear();

            initCharts();
        }
    } catch (e) {
        console.warn('Dashboard stats fetch failed:', e);
        // Initialize with empty data
        currentDashboardYear = new Date().getFullYear();
        pubDataByYearAndType = {};
        extDataByYear = {};
        initCharts();
    }
})();

function initCharts() {
    if (pubChart) {
        pubChart.destroy();
        pubChart = null;
    }
    if (tapChartInst) {
        tapChartInst.destroy();
        tapChartInst = null;
    }

    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    // Get data for current year and previous year, filtered by research type
    const currentYearAllTypes = pubDataByYearAndType[currentDashboardYear] || {};
    const prevYear = currentDashboardYear - 1;
    const prevYearAllTypes = pubDataByYearAndType[prevYear] || {};

    // Filter by research type
    let currentYearData = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    let prevYearData = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];

    if (currentResearchType === 'all') {
        // Sum all types
        Object.keys(currentYearAllTypes).forEach(type => {
            const data = currentYearAllTypes[type] || [];
            for (let i = 0; i < 12; i++) {
                currentYearData[i] += (data[i] || 0);
            }
        });
        Object.keys(prevYearAllTypes).forEach(type => {
            const data = prevYearAllTypes[type] || [];
            for (let i = 0; i < 12; i++) {
                prevYearData[i] += (data[i] || 0);
            }
        });
    } else if (currentResearchType === 'publications') {
        // Get only published types (excludes proposal and implementation)
        const pubTypes = ['oral_poster', 'proceedings', 'monographs', 'journals', 'chapters', 'books'];
        pubTypes.forEach(type => {
            const data = currentYearAllTypes[type] || [];
            for (let i = 0; i < 12; i++) {
                currentYearData[i] += (data[i] || 0);
            }
        });
        pubTypes.forEach(type => {
            const data = prevYearAllTypes[type] || [];
            for (let i = 0; i < 12; i++) {
                prevYearData[i] += (data[i] || 0);
            }
        });
    } else {
        // Get specific type
        currentYearData = currentYearAllTypes[currentResearchType] || [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
        prevYearData = prevYearAllTypes[currentResearchType] || [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    }

    // Update labels
    const pubYearLabel = document.getElementById('pub-year-label');
    const pubPrevYearLabel = document.getElementById('pub-prev-year-label');
    const pubYearBtnLabel = document.getElementById('pub-year-btn-label');
    const extYearLabel = document.getElementById('ext-year-label');

    if (pubYearLabel) pubYearLabel.textContent = currentDashboardYear;
    if (pubPrevYearLabel) pubPrevYearLabel.textContent = prevYear;
    if (pubYearBtnLabel) pubYearBtnLabel.textContent = currentDashboardYear;
    if (extYearLabel) extYearLabel.textContent = currentDashboardYear;

    // ── Line chart ──
    const pubCtx = document.getElementById('publicationsChart');
    if (pubCtx) {
        pubChart = new Chart(pubCtx, {
            type: 'line',
            data: {
                labels: months,
                datasets: [
                    {
                        label: currentDashboardYear.toString(),
                        data: currentYearData,
                        borderColor: '#014421',  // UP Forest Green
                        backgroundColor: 'transparent',
                        borderWidth: 2.5,
                        pointBackgroundColor: '#fff',
                        pointBorderColor: '#014421',  // UP Forest Green
                        pointBorderWidth: 2.5,
                        pointRadius: 6,
                        pointHoverRadius: 8,
                        pointHoverBorderWidth: 3,
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: '#014421',  // UP Forest Green
                        fill: false,
                        tension: 0.4,
                        spanGaps: false,
                    },
                    {
                        label: prevYear.toString(),
                        data: prevYearData,
                        borderColor: '#d1d5db',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        borderDash: [8, 4],
                        pointBackgroundColor: '#fff',
                        pointBorderColor: '#d1d5db',
                        pointBorderWidth: 2,
                        pointRadius: 5,
                        pointHoverRadius: 7,
                        pointHoverBorderWidth: 2.5,
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: '#d1d5db',
                        fill: false,
                        tension: 0.4,
                        spanGaps: false,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(0,0,0,0.85)',
                        padding: 12,
                        cornerRadius: 8,
                        titleFont: { size: 13, weight: '600' },
                        bodyFont: { size: 12 },
                        displayColors: true,
                        boxWidth: 8,
                        boxHeight: 8,
                        boxPadding: 6,
                        callbacks: {
                            title: items => months[items[0].dataIndex],
                            label: ctx => ` ${ctx.dataset.label}: ${ctx.raw} publications`
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        position: 'left',
                        grid: {
                            color: '#f3f4f6',
                            drawBorder: false,
                            lineWidth: 1
                        },
                        ticks: {
                            font: { size: 11, weight: '500' },
                            stepSize: 2,
                            padding: 10,
                            color: '#6b7280'
                        },
                        border: {
                            display: false
                        }
                    },
                    x: {
                        position: 'bottom',
                        grid: {
                            display: false
                        },
                        ticks: {
                            font: { size: 11, weight: '500' },
                            padding: 8,
                            color: '#6b7280'
                        },
                        border: {
                            display: false
                        }
                    }
                },
                elements: {
                    line: {
                        borderJoinStyle: 'round',
                        borderCapStyle: 'round'
                    }
                }
            }
        });
    }

    // ── Pie chart ──
    const tapCtx = document.getElementById('tapChart');
    if (tapCtx) {
        const extData = extDataByYear[currentDashboardYear] || {};

        // Extension types and their display info - UP Forest Green color scheme
        const extensionTypes = [
            { key: 'extensions', label: 'Extension/Community Service', color: '#014421' },  // UP Forest Green
            { key: 'training', label: 'Training', color: '#016428' },  // Lighter green
            { key: 'information_dissemination', label: 'Information Dissemination', color: '#028a38' },  // Medium green
            { key: 'workshop', label: 'Workshop', color: '#03a043' },  // Bright green
            { key: 'symposium', label: 'Symposium', color: '#22c55e' },  // Light bright green
            { key: 'others', label: 'Others', color: '#86efac' }  // Very light green
        ];

        const chartData = [];
        const chartLabels = [];
        const chartColors = [];

        extensionTypes.forEach(type => {
            const count = extData[type.key] || 0;
            if (count > 0) {
                chartData.push(count);
                chartLabels.push(type.label);
                chartColors.push(type.color);
            }
        });

        // If no data, show empty state
        if (chartData.length === 0) {
            chartData.push(1);
            chartLabels.push('No Data');
            chartColors.push('#e5e7eb');
        }

        // Update legend
        const legendContainer = document.getElementById('ext-legend');
        if (legendContainer) {
            if (chartData.length === 1 && chartLabels[0] === 'No Data') {
                legendContainer.innerHTML = '<div class="legend-item"><span style="color:#9ca3af;font-size:0.85rem;">No extensions for this year</span></div>';
            } else {
                legendContainer.innerHTML = extensionTypes.map((type, i) => {
                    const count = extData[type.key] || 0;
                    if (count === 0) return '';
                    return `
                        <div class="legend-item">
                            <div class="legend-dot" style="background:${type.color};"></div>
                            <span>${type.label}</span>
                            <span style="margin-left:auto;font-weight:700;color:#111827;">${count}</span>
                        </div>
                    `;
                }).join('');
            }
        }

        tapChartInst = new Chart(tapCtx, {
            type: 'pie',
            data: {
                labels: chartLabels,
                datasets: [{
                    data: chartData,
                    backgroundColor: chartColors,
                    borderColor: chartColors.map(() => '#fff'),
                    borderWidth: 2,
                    hoverOffset: 4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(0,0,0,0.85)',
                        padding: 12,
                        cornerRadius: 8,
                        titleFont: { size: 13, weight: '600' },
                        bodyFont: { size: 12 },
                        callbacks: {
                            label: ctx => {
                                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                const pct = ((ctx.raw / total) * 100).toFixed(1);
                                return ` ${ctx.label}: ${ctx.raw} (${pct}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    // Build research type dropdown
    buildTypeDropdown();

    // Build year dropdown for publications (2000 to current year)
    const currentYear = new Date().getFullYear();
    const years = [];
    for (let y = currentYear; y >= 2000; y--) {
        years.push(y);
    }
    buildYearDropdown('pub', years);
}

function changePubYear(year) {
    currentDashboardYear = parseInt(year);
    initCharts();
}

function changeResearchType(type) {
    currentResearchType = type;

    // Update label
    const typeLabel = document.getElementById('type-filter-label');
    if (typeLabel) {
        const typeNames = {
            'all': 'All Types',
            'publications': 'Publications Only',
            'proposal': 'Proposals',
            'implementation': 'Implementation'
        };
        typeLabel.textContent = typeNames[type] || 'All Types';
    }

    initCharts();
}

function buildTypeDropdown() {
    const dropdown = document.getElementById('type-year-dropdown');
    if (!dropdown) return;

    const types = [
        { value: 'all', label: 'All Types' },
        { value: 'publications', label: 'Publications Only' },
        { value: 'proposal', label: 'Proposals' },
        { value: 'implementation', label: 'Implementation' }
    ];

    dropdown.innerHTML = types.map(t => {
        return `<div class="year-option" onclick="selectType('${t.value}')">${t.label}</div>`;
    }).join('');
}

function buildYearDropdown(prefix, years) {
    const dropdown = document.getElementById(`${prefix}-year-dropdown`);
    if (!dropdown) return;

    dropdown.innerHTML = years.map(y => {
        return `<div class="year-option" onclick="selectYear_${prefix}(${y})">${y}</div>`;
    }).join('');
}

// Create global functions for type selection
window.selectType = function (type) {
    changeResearchType(type);
    const dropdown = document.getElementById('type-year-dropdown');
    if (dropdown) dropdown.classList.remove('open');
};

// Create global functions for year selection
window.selectYear_pub = function (y) {
    changePubYear(y);
    const dropdown = document.getElementById('pub-year-dropdown');
    if (dropdown) dropdown.classList.remove('open');
};

function toggleYearDropdown(prefix) {
    const dropdown = document.getElementById(`${prefix}-year-dropdown`);
    if (dropdown) {
        dropdown.classList.toggle('open');
    }
}

// Close dropdowns when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.year-selector')) {
        document.querySelectorAll('.year-dropdown').forEach(d => d.classList.remove('open'));
    }
});

// Make toggleYearDropdown globally accessible
window.toggleYearDropdown = toggleYearDropdown;
