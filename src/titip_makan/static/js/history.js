let overviewData = null;
let currentPeriod = "daily";
let chartTrendsInstance = null;
let chartMenusInstance = null;
let chartVendorsInstance = null;

async function initHistory() {
    setupPeriodButtons();
    document.getElementById("btn-refresh-history").addEventListener("click", async () => {
        await loadAnalytics();
        await loadPastSessions();
        showToast("Data analitik diperbarui.", "info");
    });
    await loadAnalytics();
    await loadPastSessions();
}

function setupPeriodButtons() {
    const dailyBtn = document.getElementById("btn-period-daily");
    const weeklyBtn = document.getElementById("btn-period-weekly");
    const monthlyBtn = document.getElementById("btn-period-monthly");

    function setActiveBtn(activeBtn) {
        [dailyBtn, weeklyBtn, monthlyBtn].forEach(b => {
            b.className = "period-btn px-3 py-1.5 rounded-lg text-slate-600 hover:text-slate-900 transition";
        });
        activeBtn.className = "period-btn px-3 py-1.5 rounded-lg bg-white shadow-sm text-indigo-600 font-bold transition";
    }

    dailyBtn.addEventListener("click", () => {
        currentPeriod = "daily";
        setActiveBtn(dailyBtn);
        document.getElementById("table-period-label").innerText = "Harian";
        updateTrendsAndTable();
    });

    weeklyBtn.addEventListener("click", () => {
        currentPeriod = "weekly";
        setActiveBtn(weeklyBtn);
        document.getElementById("table-period-label").innerText = "Mingguan";
        updateTrendsAndTable();
    });

    monthlyBtn.addEventListener("click", () => {
        currentPeriod = "monthly";
        setActiveBtn(monthlyBtn);
        document.getElementById("table-period-label").innerText = "Bulanan";
        updateTrendsAndTable();
    });
}

async function loadAnalytics() {
    try {
        const resp = await fetch("/api/v1/analytics/overview");
        if (!resp.ok) return;
        overviewData = await resp.json();

        // Populate summary cards
        document.getElementById("stat-sessions").innerText = overviewData.total_sessions;
        document.getElementById("stat-orders").innerText = `${overviewData.total_orders} porsi`;
        document.getElementById("stat-spend").innerText = `Rp ${overviewData.total_spend.toLocaleString("id-ID")}`;
        document.getElementById("stat-avg").innerText = `Rp ${Math.round(overviewData.average_order_price).toLocaleString("id-ID")}`;

        // Render charts
        renderTopMenusChart(overviewData.top_menus);
        renderVendorsChart(overviewData.top_vendors);
        updateTrendsAndTable();

    } catch (err) {
        console.error("Gagal memuat analitik:", err);
    }
}

function updateTrendsAndTable() {
    if (!overviewData) return;

    let statsList = [];
    if (currentPeriod === "daily") {
        statsList = overviewData.daily_stats;
    } else if (currentPeriod === "weekly") {
        statsList = overviewData.weekly_stats;
    } else {
        statsList = overviewData.monthly_stats;
    }

    renderTrendsChart(statsList);
    renderPeriodTable(statsList);
}

function renderTrendsChart(statsList) {
    const ctx = document.getElementById("chart-trends").getContext("2d");
    if (chartTrendsInstance) chartTrendsInstance.destroy();

    const labels = statsList.map(s => s.label);
    const orderCounts = statsList.map(s => s.order_count);
    const totalSpends = statsList.map(s => s.total_spend);

    chartTrendsInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels.length ? labels : ['Belum Ada Data'],
            datasets: [
                {
                    label: 'Jumlah Pesanan (Porsi)',
                    data: orderCounts.length ? orderCounts : [0],
                    backgroundColor: 'rgba(99, 102, 241, 0.7)',
                    borderColor: 'rgb(99, 102, 241)',
                    borderWidth: 1,
                    borderRadius: 6,
                    yAxisID: 'yOrders',
                },
                {
                    label: 'Total Belanja (Rp)',
                    data: totalSpends.length ? totalSpends : [0],
                    type: 'line',
                    borderColor: 'rgb(16, 185, 129)',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 3,
                    tension: 0.3,
                    fill: false,
                    yAxisID: 'ySpend',
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                yOrders: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    ticks: { precision: 0 },
                    title: { display: true, text: 'Porsi' }
                },
                ySpend: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    ticks: {
                        callback: (v) => 'Rp ' + (v >= 1000 ? (v / 1000) + 'k' : v)
                    },
                    title: { display: true, text: 'Nominal (Rp)' }
                }
            }
        }
    });
}

function renderTopMenusChart(topMenus) {
    const ctx = document.getElementById("chart-top-menus").getContext("2d");
    if (chartMenusInstance) chartMenusInstance.destroy();

    const menus = topMenus.slice(0, 10);
    const labels = menus.map(m => m.name);
    const counts = menus.map(m => m.count);

    chartMenusInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels.length ? labels : ['Belum Ada Data'],
            datasets: [{
                label: 'Jumlah Dipesan',
                data: counts.length ? counts : [0],
                backgroundColor: 'rgba(59, 130, 246, 0.75)',
                borderColor: 'rgb(59, 130, 246)',
                borderWidth: 1,
                borderRadius: 6
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { ticks: { precision: 0 } }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

function renderVendorsChart(topVendors) {
    const ctx = document.getElementById("chart-vendors").getContext("2d");
    if (chartVendorsInstance) chartVendorsInstance.destroy();

    const vendors = topVendors.slice(0, 8);
    const labels = vendors.map(v => v.name);
    const totals = vendors.map(v => v.total_amount);

    chartVendorsInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels.length ? labels : ['Belum Ada'],
            datasets: [{
                data: totals.length ? totals : [1],
                backgroundColor: [
                    '#6366f1', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#06b6d4', '#14b8a6', '#f97316'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: (ctx) => `${ctx.label}: Rp ${ctx.raw.toLocaleString("id-ID")}`
                    }
                }
            }
        }
    });
}

function renderPeriodTable(statsList) {
    const tbody = document.getElementById("period-stats-tbody");
    tbody.innerHTML = "";

    if (!statsList || statsList.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center py-6 text-slate-400">Belum ada aktivitas di periode ini.</td></tr>`;
        return;
    }

    statsList.forEach(s => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-50 transition";
        tr.innerHTML = `
            <td class="py-2.5 px-3 font-bold text-slate-800">${s.label}</td>
            <td class="py-2.5 px-3 font-semibold text-indigo-600">${s.order_count} porsi</td>
            <td class="py-2.5 px-3 font-bold text-slate-900">Rp ${s.total_spend.toLocaleString("id-ID")}</td>
            <td class="py-2.5 px-3 text-slate-700">${s.top_menu ? `🍜 <span class="font-medium">${s.top_menu}</span>` : '-'}</td>
            <td class="py-2.5 px-3 text-slate-700">${s.top_spender ? `👑 <span class="font-semibold text-amber-700">${s.top_spender}</span>` : '-'}</td>
        `;
        tbody.appendChild(tr);
    });
}

async function loadPastSessions() {
    try {
        const resp = await fetch("/api/v1/sessions/history");
        if (!resp.ok) return;
        const sessions = await resp.json();

        const container = document.getElementById("past-sessions-container");
        container.innerHTML = "";

        if (!sessions || sessions.length === 0) {
            container.innerHTML = `<p class="text-xs text-slate-400 text-center py-6">Belum ada riwayat sesi yang tercatat.</p>`;
            return;
        }

        sessions.forEach(s => {
            const card = document.createElement("div");
            card.className = "p-4 rounded-xl border border-slate-200 bg-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-3";
            
            const isClosed = s.status === "CLOSED";
            const badge = isClosed
                ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-200 text-slate-700">DITUTUP</span>`
                : `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700">AKTIF</span>`;

            let dateStr = "-";
            if (s.created_at) {
                const d = new Date(s.created_at.endsWith("Z") || s.created_at.includes("+") ? s.created_at : s.created_at + "Z");
                dateStr = d.toLocaleDateString("id-ID", { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
            }

            card.innerHTML = `
                <div>
                    <div class="flex items-center gap-2 mb-1">
                        ${badge}
                        <span class="text-xs font-semibold text-slate-500">Sesi #${s.id}</span>
                        <span class="text-xs text-slate-400">• ${dateStr}</span>
                    </div>
                    <h4 class="font-bold text-slate-900 text-sm">${s.title}</h4>
                    <p class="text-xs text-slate-500 mt-0.5">Koordinator: <span class="font-medium text-slate-700">${s.coordinator_name}</span> ${s.coordinator_phone ? `(${s.coordinator_phone})` : ''}</p>
                </div>
                <div class="flex items-center gap-2">
                    <button onclick="window.viewSessionRecap(${s.id})" class="px-3 py-1.5 bg-white hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-semibold rounded-xl transition shadow-sm">
                        📋 Lihat Rekap
                    </button>
                </div>
            `;
            container.appendChild(card);
        });
    } catch (err) {
        console.error("Gagal memuat riwayat sesi:", err);
    }
}

window.viewSessionRecap = async function(sessionId) {
    try {
        const resp = await fetch(`/api/v1/sessions/${sessionId}/summary`);
        if (!resp.ok) {
            showToast("Gagal mengambil rekap sesi.", "error");
            return;
        }
        const summary = await resp.json();
        if (summary.whatsapp_recap_text) {
            await navigator.clipboard.writeText(summary.whatsapp_recap_text);
            showToast(`Rekap Sesi #${sessionId} disalin ke clipboard!`, "success");
        } else {
            showToast(`Total Sesi #${sessionId}: ${summary.total_orders} pesanan, Rp ${summary.total_amount.toLocaleString("id-ID")}`, "info");
        }
    } catch (e) {
        showToast("Gagal memuat rekap sesi.", "error");
    }
};

document.addEventListener("DOMContentLoaded", initHistory);
