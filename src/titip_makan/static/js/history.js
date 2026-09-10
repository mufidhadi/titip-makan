let overviewData = null;
let currentPeriod = "daily";
let chartTrendsInstance = null;
let chartMenusInstance = null;
let chartVendorsInstance = null;

async function initHistory() {
    setupPeriodButtons();
    
    const pageSizeSelect = document.getElementById("sessions-page-size");
    if (pageSizeSelect) {
        pageSizeSelect.addEventListener("change", (e) => {
            historyPagination.limit = parseInt(e.target.value, 10) || 10;
            historyPagination.page = 1;
            loadPastSessions();
        });
    }

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

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

let historyPagination = {
    page: 1,
    limit: 10,
    total: 0,
    totalPages: 1
};

async function loadPastSessions(targetPage = null) {
    if (targetPage !== null) {
        historyPagination.page = targetPage;
    }

    const container = document.getElementById("past-sessions-container");
    container.innerHTML = `
        <div class="flex items-center justify-center py-10 text-slate-400 gap-2 text-xs">
            <span class="loading loading-spinner loading-sm text-indigo-500"></span> Memuat riwayat sesi...
        </div>
    `;

    try {
        const resp = await fetch(`/api/v1/sessions/history?page=${historyPagination.page}&limit=${historyPagination.limit}`);
        if (!resp.ok) {
            container.innerHTML = `<p class="text-xs text-rose-500 text-center py-6">Gagal memuat riwayat sesi.</p>`;
            return;
        }
        const resJson = await resp.json();

        let sessions = [];
        if (Array.isArray(resJson)) {
            sessions = resJson;
            historyPagination.total = resJson.length;
            historyPagination.totalPages = 1;
        } else {
            sessions = resJson.items || [];
            historyPagination.total = resJson.total || 0;
            historyPagination.page = resJson.page || 1;
            historyPagination.limit = resJson.limit || 10;
            historyPagination.totalPages = resJson.total_pages || 1;
        }

        // Update badge total
        const badge = document.getElementById("sessions-total-badge");
        if (badge) {
            badge.innerText = `Total: ${historyPagination.total} Sesi`;
        }

        container.innerHTML = "";

        if (!sessions || sessions.length === 0) {
            container.innerHTML = `<p class="text-xs text-slate-400 text-center py-6">Belum ada riwayat sesi pada halaman ini.</p>`;
            renderPaginationControls();
            return;
        }

        sessions.forEach(s => {
            const card = document.createElement("div");
            card.className = "p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-3";
            
            const isClosed = s.status === "CLOSED";
            const statusBadge = isClosed
                ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-200 text-slate-700">DITUTUP</span>`
                : `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700">AKTIF</span>`;

            let dateStr = "-";
            if (s.created_at) {
                const d = new Date(s.created_at.endsWith("Z") || s.created_at.includes("+") ? s.created_at : s.created_at + "Z");
                dateStr = d.toLocaleDateString("id-ID", { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
            }

            const orders = s.orders || [];
            const totalOrders = orders.length;
            const totalAmount = orders.reduce((sum, o) => sum + (o.price || 0), 0);
            const paidCount = orders.filter(o => o.payment_status === "PAID" || o.is_paid).length;

            const ordersRows = orders.length > 0
                ? orders.map((o, idx) => {
                    const paymentBadge = (o.payment_status === "PAID" || o.is_paid)
                        ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700">✅ Lunas</span>`
                        : (o.payment_status === "PENDING_CONFIRMATION")
                            ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-700">🟡 Konfirmasi</span>`
                            : `<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-600">⏳ Belum</span>`;
                    const priceText = o.price > 0 ? `Rp ${o.price.toLocaleString("id-ID")}` : `<span class="text-amber-600 italic">Belum di-set</span>`;
                    return `
                        <tr class="hover:bg-slate-50/80 transition">
                            <td class="py-2 px-2.5 font-semibold text-slate-400">${idx + 1}</td>
                            <td class="py-2 px-2.5 font-bold text-slate-800">${escapeHtml(o.user_name)}</td>
                            <td class="py-2 px-2.5">
                                <span class="font-medium text-slate-900">${escapeHtml(o.item_name)}</span>
                                <span class="text-[10px] text-slate-400">(${escapeHtml(o.vendor)})</span>
                            </td>
                            <td class="py-2 px-2.5 text-slate-500 italic text-[11px]">${o.notes ? `"${escapeHtml(o.notes)}"` : '-'}</td>
                            <td class="py-2 px-2.5 font-semibold text-slate-800">${priceText}</td>
                            <td class="py-2 px-2.5 text-right">${paymentBadge}</td>
                        </tr>
                    `;
                }).join("")
                : `<tr><td colspan="6" class="text-center py-4 text-slate-400 text-xs italic">Tidak ada pesanan pada sesi ini.</td></tr>`;

            card.innerHTML = `
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                        <div class="flex items-center gap-2 mb-1 flex-wrap">
                            ${statusBadge}
                            <span class="text-xs font-semibold text-slate-500">Sesi #${s.id}</span>
                            <span class="text-xs text-slate-400">• ${dateStr}</span>
                            <span class="text-xs font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-md">${totalOrders} Pesanan</span>
                            <span class="text-xs font-bold text-slate-800">Rp ${totalAmount.toLocaleString("id-ID")}</span>
                        </div>
                        <h4 class="font-bold text-slate-900 text-sm">${escapeHtml(s.title)}</h4>
                        <p class="text-xs text-slate-500 mt-0.5">
                            Koordinator: <span class="font-medium text-slate-700">${escapeHtml(s.coordinator_name)}</span> ${s.coordinator_phone ? `(${escapeHtml(s.coordinator_phone)})` : ''} • Lunas: <span class="text-emerald-700 font-semibold">${paidCount}/${totalOrders}</span>
                        </p>
                    </div>
                    <div class="flex items-center gap-2">
                        <button onclick="window.toggleSessionOrdersDetail(${s.id})" id="btn-toggle-orders-${s.id}" class="px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-bold rounded-xl transition shadow-sm flex items-center gap-1.5">
                            <span>📦</span> Detail Pesanan (${totalOrders})
                        </button>
                        <button onclick="window.viewSessionRecap(${s.id})" class="px-3 py-1.5 bg-white hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-semibold rounded-xl transition shadow-sm">
                            📋 Salin Rekap
                        </button>
                    </div>
                </div>
                <!-- Collapsible Orders Table -->
                <div id="session-orders-detail-${s.id}" class="hidden pt-2 border-t border-slate-200/80">
                    <div class="overflow-x-auto rounded-xl border border-slate-200 bg-white">
                        <table class="w-full text-left border-collapse text-xs">
                            <thead>
                                <tr class="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
                                    <th class="py-2 px-2.5 w-8">No</th>
                                    <th class="py-2 px-2.5">Pemesan</th>
                                    <th class="py-2 px-2.5">Menu &amp; Tenant</th>
                                    <th class="py-2 px-2.5">Catatan</th>
                                    <th class="py-2 px-2.5">Harga</th>
                                    <th class="py-2 px-2.5 text-right">Status</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-100">
                                ${ordersRows}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
            container.appendChild(card);
        });

        renderPaginationControls();
    } catch (err) {
        console.error("Gagal memuat riwayat sesi:", err);
    }
}

function renderPaginationControls() {
    const infoEl = document.getElementById("pagination-info");
    const buttonsEl = document.getElementById("pagination-buttons");
    if (!infoEl || !buttonsEl) return;

    const { page, limit, total, totalPages } = historyPagination;
    
    if (total === 0) {
        infoEl.innerText = "Tidak ada sesi.";
        buttonsEl.innerHTML = "";
        return;
    }

    const startItem = (page - 1) * limit + 1;
    const endItem = Math.min(page * limit, total);
    infoEl.innerHTML = `Menampilkan <span class="font-bold text-slate-700">${startItem} - ${endItem}</span> dari <span class="font-bold text-slate-700">${total}</span> sesi <span class="text-slate-400 font-normal">(Hal. ${page}/${totalPages})</span>`;

    buttonsEl.innerHTML = "";

    // Prev Button
    const prevBtn = document.createElement("button");
    const isPrevDisabled = page <= 1;
    prevBtn.className = `join-item btn btn-sm px-3 ${isPrevDisabled ? 'btn-disabled bg-slate-50 text-slate-300 border-slate-200' : 'bg-white hover:bg-slate-100 text-slate-700 font-medium border-slate-300'} text-xs border`;
    prevBtn.innerHTML = "« Prev";
    if (!isPrevDisabled) {
        prevBtn.onclick = () => {
            loadPastSessions(page - 1);
            scrollToSessions();
        };
    }
    buttonsEl.appendChild(prevBtn);

    // Numbered Buttons (smart window max 5)
    const maxVisiblePages = 5;
    let startPage = Math.max(1, page - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    if (endPage - startPage + 1 < maxVisiblePages) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    if (startPage > 1) {
        const firstBtn = document.createElement("button");
        firstBtn.className = "join-item btn btn-sm min-w-[36px] px-2 bg-white hover:bg-slate-100 text-slate-700 font-medium text-xs border border-slate-300";
        firstBtn.innerText = "1";
        firstBtn.onclick = () => { loadPastSessions(1); scrollToSessions(); };
        buttonsEl.appendChild(firstBtn);

        if (startPage > 2) {
            const dots = document.createElement("button");
            dots.className = "join-item btn btn-sm min-w-[32px] px-1 btn-disabled bg-white text-slate-400 text-xs border border-slate-300";
            dots.innerText = "...";
            buttonsEl.appendChild(dots);
        }
    }

    for (let p = startPage; p <= endPage; p++) {
        const pageBtn = document.createElement("button");
        const isActive = p === page;
        pageBtn.className = `join-item btn btn-sm min-w-[36px] px-2 ${isActive ? 'btn-active bg-indigo-600 hover:bg-indigo-700 border-indigo-600 text-white font-bold' : 'bg-white hover:bg-slate-100 text-slate-700 font-medium border-slate-300'} text-xs border`;
        pageBtn.innerText = p;
        if (!isActive) {
            pageBtn.onclick = () => {
                loadPastSessions(p);
                scrollToSessions();
            };
        }
        buttonsEl.appendChild(pageBtn);
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            const dots = document.createElement("button");
            dots.className = "join-item btn btn-sm min-w-[32px] px-1 btn-disabled bg-white text-slate-400 text-xs border border-slate-300";
            dots.innerText = "...";
            buttonsEl.appendChild(dots);
        }
        const lastBtn = document.createElement("button");
        lastBtn.className = "join-item btn btn-sm min-w-[36px] px-2 bg-white hover:bg-slate-100 text-slate-700 font-medium text-xs border border-slate-300";
        lastBtn.innerText = totalPages;
        lastBtn.onclick = () => { loadPastSessions(totalPages); scrollToSessions(); };
        buttonsEl.appendChild(lastBtn);
    }

    // Next Button
    const nextBtn = document.createElement("button");
    const isNextDisabled = page >= totalPages;
    nextBtn.className = `join-item btn btn-sm px-3 ${isNextDisabled ? 'btn-disabled bg-slate-50 text-slate-300 border-slate-200' : 'bg-white hover:bg-slate-100 text-slate-700 font-medium border-slate-300'} text-xs border`;
    nextBtn.innerHTML = "Next »";
    if (!isNextDisabled) {
        nextBtn.onclick = () => {
            loadPastSessions(page + 1);
            scrollToSessions();
        };
    }
    buttonsEl.appendChild(nextBtn);
}

function scrollToSessions() {
    const el = document.getElementById("past-sessions-card");
    if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

window.toggleSessionOrdersDetail = function(sessionId) {
    const detail = document.getElementById(`session-orders-detail-${sessionId}`);
    if (!detail) return;
    detail.classList.toggle("hidden");
};

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
