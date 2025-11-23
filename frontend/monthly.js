const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : window.location.origin;
let currentData = [];
let sortColumn = 'date';
let sortDirection = 'desc';
const SESSION_KEY_MONTHLY = 'dashboard_monthly_data';
const tableContainer = document.getElementById('tableContainer');
const tableBody = document.getElementById('tableBody');
const loadingState = document.getElementById('loadingState');
const emptyState = document.getElementById('emptyState');
const errorState = document.getElementById('errorState');
const errorMessage = document.getElementById('errorMessage');
const refreshBtn = document.getElementById('refreshBtn');
const statsContainer = document.getElementById('stats');
document.addEventListener('DOMContentLoaded', () => {
    loadMonthlyData();
    setupSorting();
});
refreshBtn.addEventListener('click', () => {
    loadMonthlyData();
});
async function loadMonthlyData() {
    showLoading();
    try {
        const [statsResponse, dataResponse] = await Promise.all([
            fetch(`${API_BASE_URL}/api/monthly-stats`),
            fetch(`${API_BASE_URL}/api/monthly-data`)
        ]);

        // Parse data first so we can derive stats if the stats endpoint returns empty
        let data = dataResponse.ok ? await dataResponse.json() : [];

        // Fallback op cache
        if ((!data || data.length === 0) && hasCachedMonthly()) {
            data = getCachedMonthly();
        }

        let stats = statsResponse.ok ? await statsResponse.json() : null;
        // Fallback: derive stats from data when the stats call fails or returns zero (possible cold start / tmp file missing)
        if (!stats || !stats.total_records) {
            stats = deriveStatsFromData(data);
        }

        if (!data || data.length === 0) {
            showEmptyState();
            return;
        }
        currentData = data;
        cacheMonthly(currentData);
        renderStats(stats);
        renderTable(data);
        showTable();
    } catch (error) {
        console.error('Error loading monthly data:', error);
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
            <div class="stat-label">Totaal Maanden</div>
            <div class="stat-value">${stats.total_records.toLocaleString()}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Eerste Maand</div>
            <div class="stat-value">${stats.date_range.start || 'N/A'}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Laatste Maand</div>
            <div class="stat-value">${stats.date_range.end || 'N/A'}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Periode</div>
            <div class="stat-value">${calculateYears(stats.date_range.start, stats.date_range.end)}</div>
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
function calculateYears(startDate, endDate) {
    if (!startDate || !endDate) return 'N/A';
    const start = new Date(startDate);
    const end = new Date(endDate);
    const years = ((end - start) / (1000 * 60 * 60 * 24 * 365)).toFixed(1);
    return `${years} jaar`;
}

function cacheMonthly(data) {
    try {
        sessionStorage.setItem(SESSION_KEY_MONTHLY, JSON.stringify(data));
    } catch (_) {
        // ignore
    }
}

function hasCachedMonthly() {
    try {
        return !!sessionStorage.getItem(SESSION_KEY_MONTHLY);
    } catch (_) {
        return false;
    }
}

function getCachedMonthly() {
    try {
        const raw = sessionStorage.getItem(SESSION_KEY_MONTHLY);
        return raw ? JSON.parse(raw) : [];
    } catch (_) {
        return [];
    }
}
function renderTable(data) {
    const sortedData = sortData(data, sortColumn, sortDirection);
    const rows = sortedData.map(row => {
        return `
            <tr>
                <td>${row.date || '-'}</td>
                <td>${formatNumber(row.open)}</td>
                <td>${formatNumber(row.high)}</td>
                <td>${formatNumber(row.low)}</td>
                <td>${formatNumber(row.close)}</td>
                <td>${formatVolume(row.volume)}</td>
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
        let aVal = a[column];
        let bVal = b[column];
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
function formatVolume(value) {
    if (value == null || value === undefined) return '-';
    return value.toLocaleString();
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
