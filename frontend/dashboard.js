const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : window.location.origin;
let currentData = [];
let sortColumn = 'date';
let sortDirection = 'desc';
const tableContainer = document.getElementById('tableContainer');
const tableBody = document.getElementById('tableBody');
const loadingState = document.getElementById('loadingState');
const emptyState = document.getElementById('emptyState');
const errorState = document.getElementById('errorState');
const errorMessage = document.getElementById('errorMessage');
const statsContainer = document.getElementById('stats');
document.addEventListener('DOMContentLoaded', () => {
    loadDashboardData();
    setupSorting();
});
async function loadDashboardData() {
    showLoading();
    try {
        const [statsResponse, dataResponse] = await Promise.all([
            fetch(`${API_BASE_URL}/api/stats`),
            fetch(`${API_BASE_URL}/api/daily-data?limit=60`)
        ]);
        const data = dataResponse.ok ? await dataResponse.json() : [];
        let stats = statsResponse.ok ? await statsResponse.json() : null;

        // Fallback: als stats ontbreekt of 0 meldt, leid af uit data
        if (!stats || !stats.total_records) {
            stats = deriveStatsFromData(data);
        }

        if (!data || data.length === 0) {
            showEmptyState();
            return;
        }
        currentData = data.map(enrichRowWithDerived);
        renderStats(stats);
        renderTable(currentData);
        showTable();
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        showError(`Kon geen verbinding maken met de API. Zorg ervoor dat de backend draait op ${API_BASE_URL}`);
    }
}
function renderStats(stats) {
    if (!stats) {
        statsContainer.innerHTML = '';
        return;
    }
    const html = `
        <div class="stat-card">
            <div class="stat-label">Total Records</div>
            <div class="stat-value">${stats.total_records.toLocaleString()}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">First Date</div>
            <div class="stat-value">${stats.date_range.start || ''}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Last Date</div>
            <div class="stat-value">${stats.date_range.end || ''}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Records Shown</div>
            <div class="stat-value">${currentData.length}</div>
        </div>
    `;
    statsContainer.innerHTML = html;
}

function deriveStatsFromData(data) {
    if (!data || data.length === 0) return null;
    const sorted = [...data].sort((a, b) => new Date(a.date) - new Date(b.date));
    const start = sorted[0]?.date;
    const end = sorted[sorted.length - 1]?.date;
    return {
        total_records: data.length,
        date_range: { start, end }
    };
}

function enrichRowWithDerived(row) {
    const diff = row.high_prev_close_diff;
    const prevClose = (row.high != null && diff != null) ? (row.high - diff) : null;
    const diffPct = (prevClose && prevClose !== 0) ? (diff / prevClose) * 100 : null;
    return {
        ...row,
        high_prev_close_diff: diff,
        high_prev_close_pct: diffPct
    };
}
function renderTable(data) {
    const sortedData = sortData(data, sortColumn, sortDirection);
    const rows = sortedData.map(row => {
        const rsiClass = getRsiClass(row.rsi);
        const diffClass = row.high_prev_close_diff < 0 ? 'diff-negative' : '';
        const pctClass = row.high_prev_close_pct < 0 ? 'diff-negative' : '';
        return `
            <tr>
                <td>${row.date || '-'}</td>
                <td>${formatNumber(row.open)}</td>
                <td>${formatNumber(row.high)}</td>
                <td class="${diffClass}">${formatNumber(row.high_prev_close_diff)}</td>
                <td class="${pctClass}">${formatPercent(row.high_prev_close_pct)}</td>
                <td>${formatNumber(row.low)}</td>
                <td>${formatNumber(row.close)}</td>
                <td>${formatVolume(row.volume)}</td>
                <td class="${rsiClass}">${formatNumber(row.rsi)}</td>
                <td>${formatNumber(row.macd?.line)}</td>
                <td>${formatNumber(row.macd?.signal)}</td>
                <td>${formatNumber(row.macd?.hist)}</td>
            </tr>
        `;
    }).join('');
    tableBody.innerHTML = rows;
}
function setupSorting() {
    const headers = document.querySelectorAll('.sortable');
    headers.forEach(header => {
        header.addEventListener('click', () => {
            const column = header.dataset.column;
            if (column === sortColumn) {
                sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                sortColumn = column;
                sortDirection = 'desc';
            }
            headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
            header.classList.add(sortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
            renderTable(currentData);
        });
    });
}
function sortData(data, column, direction) {
    const sorted = [...data].sort((a, b) => {
        let aVal, bVal;
        if (column.startsWith('macd_')) {
            const macdKey = column.replace('macd_', '');
            aVal = a.macd?.[macdKey];
            bVal = b.macd?.[macdKey];
        } else {
            aVal = a[column];
            bVal = b[column];
        }
        if (aVal == null && bVal == null) return 0;
        if (aVal == null) return 1;
        if (bVal == null) return -1;
        if (typeof aVal === 'string') {
            return direction === 'asc'
                ? aVal.localeCompare(bVal)
                : bVal.localeCompare(aVal);
        } else {
            return direction === 'asc'
                ? aVal - bVal
                : bVal - aVal;
        }
    });
    return sorted;
}
function formatNumber(value) {
    if (value == null || value === undefined) return '-';
    return typeof value === 'number' ? value.toFixed(2) : value;
}

function formatPercent(value) {
    if (value == null || value === undefined || Number.isNaN(value)) return '-';
    return `${value.toFixed(2)}%`;
}
function formatVolume(value) {
    if (value == null || value === undefined) return '-';
    return value.toLocaleString();
}
function getRsiClass(rsi) {
    if (rsi == null) return '';
    if (rsi > 75) return 'rsi-overbought';
    if (rsi < 25) return 'rsi-oversold';
    return '';
}
function showLoading() {
    loadingState.style.display = 'block';
    tableContainer.style.display = 'none';
    emptyState.style.display = 'none';
    errorState.style.display = 'none';
}
function showTable() {
    loadingState.style.display = 'none';
    tableContainer.style.display = 'block';
    emptyState.style.display = 'none';
    errorState.style.display = 'none';
}
function showEmptyState() {
    loadingState.style.display = 'none';
    tableContainer.style.display = 'none';
    emptyState.style.display = 'block';
    errorState.style.display = 'none';
    statsContainer.innerHTML = '';
}
function showError(message) {
    loadingState.style.display = 'none';
    tableContainer.style.display = 'none';
    emptyState.style.display = 'none';
    errorState.style.display = 'block';
    errorMessage.textContent = message;
    statsContainer.innerHTML = '';
}
