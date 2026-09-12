let currentSession = null;
let pollTimer = null;
let countdownInterval = null;
let suggestionsData = { tenants: [], menus: {}, prices: {} };
let lastSavedOrder = null;

async function initApp() {
    setupQuickNames();
    setupModalHandlers();
    await fetchActiveSession();
    setupFormEventListeners();
}

function parseUtcDate(dateStr) {
    if (!dateStr) return null;
    if (!dateStr.endsWith("Z") && !dateStr.includes("+")) {
        dateStr += "Z";
    }
    return new Date(dateStr);
}

function getSavedUsername() {
    return localStorage.getItem("titip_makan_username") || "";
}

function saveUsername(name) {
    if (name) {
        localStorage.setItem("titip_makan_username", name);
    }
}

async function fetchActiveSession() {
    try {
        const resp = await fetch("/api/v1/sessions/latest");
        const data = await resp.json();

        if (!data) {
            document.getElementById("session-banner").classList.add("hidden");
            document.getElementById("orders-section").classList.add("hidden");
            document.getElementById("no-session-alert").classList.remove("hidden");
            const mobileBar = document.getElementById("mobile-bottom-bar");
            if (mobileBar) mobileBar.classList.add("hidden");
            return;
        }

        currentSession = data;
        document.getElementById("no-session-alert").classList.add("hidden");
        document.getElementById("session-banner").classList.remove("hidden");
        document.getElementById("orders-section").classList.remove("hidden");
        const mobileBar = document.getElementById("mobile-bottom-bar");
        if (mobileBar) mobileBar.classList.remove("hidden");

        document.getElementById("session-title").innerText = data.title;
        const phoneInfo = data.coordinator_phone ? ` (${data.coordinator_phone})` : "";
        document.getElementById("session-coordinator").innerText = `Koordinator: ${data.coordinator_name}${phoneInfo}`;
        document.getElementById("session-vendors").innerText = `Saran Tenant: ${data.vendor_options ? data.vendor_options.join(", ") : "-"}`;
        document.getElementById("payment-info-text").innerText = data.payment_info || "Belum ada detail pembayaran.";

        const statusBadge = document.getElementById("session-status-badge");
        const openModalBtn = document.getElementById("btn-open-order-modal");
        const mobileOpenModalBtn = document.getElementById("btn-mobile-open-order-modal");

        if (data.status === "CLOSED") {
            statusBadge.className = "px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-100 text-rose-700";
            statusBadge.innerText = "SESI DITUTUP";
            if (openModalBtn) {
                openModalBtn.disabled = true;
                openModalBtn.innerHTML = "<span>🔒</span> Ditutup";
                openModalBtn.className = "hidden sm:flex px-4 py-2 bg-slate-300 text-slate-500 font-bold text-xs sm:text-sm rounded-xl cursor-not-allowed items-center justify-center gap-1.5";
            }
            if (mobileOpenModalBtn) {
                mobileOpenModalBtn.disabled = true;
                mobileOpenModalBtn.innerHTML = "<span>🔒</span> Pemesanan Ditutup";
                mobileOpenModalBtn.className = "flex-1 max-w-[240px] py-2.5 px-4 bg-slate-300 text-slate-500 font-bold text-xs rounded-xl cursor-not-allowed flex items-center justify-center gap-1.5";
            }
            document.getElementById("countdown-timer").innerText = "DITUTUP";
        } else {
            statusBadge.className = "px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-700";
            statusBadge.innerText = "MEMBUAT PESANAN";
            if (openModalBtn) {
                openModalBtn.disabled = false;
                openModalBtn.innerHTML = "<span>➕</span> Tambah Pesanan";
                openModalBtn.className = "hidden sm:flex px-4 py-2 bg-emerald-600 hover:bg-emerald-700 active:scale-[0.99] text-white font-bold text-xs sm:text-sm rounded-xl transition shadow-md items-center justify-center gap-1.5";
            }
            if (mobileOpenModalBtn) {
                mobileOpenModalBtn.disabled = false;
                mobileOpenModalBtn.innerHTML = '<span class="text-base leading-none">➕</span> Tambah Pesanan';
                mobileOpenModalBtn.className = "flex-1 max-w-[240px] py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 active:scale-[0.98] text-white font-extrabold text-sm rounded-xl transition shadow-lg flex items-center justify-center gap-2";
            }
            startCountdown(data.cutoff_at);
        }

        await fetchSuggestions();
        await loadOrders();

        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(async () => {
            await loadOrders();
            await fetchSuggestions();
        }, 5000);

    } catch (err) {
        console.error("Gagal memuat sesi:", err);
    }
}

async function fetchSuggestions() {
    if (!currentSession) return;
    try {
        const resp = await fetch(`/api/v1/sessions/${currentSession.id}/suggestions`);
        if (resp.ok) {
            suggestionsData = await resp.json();
            renderTenantDatalist(suggestionsData.tenants);
            updateMenuDatalist();
        }
    } catch (err) {
        console.error("Gagal memuat saran tenant & menu:", err);
    }
}

function renderTenantDatalist(tenants) {
    const datalist = document.getElementById("datalist-tenants");
    if (!datalist) return;
    datalist.innerHTML = "";
    (tenants || []).forEach(t => {
        const opt = document.createElement("option");
        opt.value = t;
        datalist.appendChild(opt);
    });
}

function formatRupiahLabel(amount) {
    if (!amount) return "";
    return "Rp " + amount.toLocaleString("id-ID");
}

function updateMenuDatalist() {
    const selectedTenant = document.getElementById("input-tenant").value.trim();
    const menuDatalist = document.getElementById("datalist-menus");
    if (!menuDatalist) return;
    menuDatalist.innerHTML = "";

    const addOption = (m) => {
        const opt = document.createElement("option");
        opt.value = m;
        if (suggestionsData.prices && suggestionsData.prices[m]) {
            opt.label = formatRupiahLabel(suggestionsData.prices[m]);
        }
        menuDatalist.appendChild(opt);
    };

    if (selectedTenant && suggestionsData.menus && suggestionsData.menus[selectedTenant]) {
        suggestionsData.menus[selectedTenant].forEach(m => addOption(m));
    } else {
        const allMenus = new Set();
        Object.values(suggestionsData.menus || {}).forEach(arr => {
            arr.forEach(m => allMenus.add(m));
        });
        Array.from(allMenus).sort().forEach(m => addOption(m));
    }
}

function handleMenuInput() {
    const menuInput = document.getElementById("input-menu");
    const tenantInput = document.getElementById("input-tenant");
    const priceInput = document.getElementById("input-price");
    if (!menuInput) return;

    const val = menuInput.value.trim();
    if (!val) return;

    // 1. Auto-fill price if known
    if (priceInput && suggestionsData.prices && suggestionsData.prices[val] !== undefined) {
        priceInput.value = suggestionsData.prices[val];
    }

    // 2. Auto-fill tenant if empty and menu belongs to a known tenant
    if (tenantInput && !tenantInput.value.trim() && suggestionsData.menus) {
        for (const [t, menus] of Object.entries(suggestionsData.menus)) {
            if (menus.includes(val)) {
                tenantInput.value = t;
                updateMenuDatalist();
                break;
            }
        }
    }
}

async function loadOrders() {
    if (!currentSession) return;
    try {
        const resp = await fetch(`/api/v1/sessions/${currentSession.id}/orders`);
        const orders = await resp.json();
        renderOrders(orders);
    } catch (err) {
        console.error("Gagal memuat pesanan:", err);
    }
}

function renderOrders(orders) {
    const countBadge = document.getElementById("orders-count-badge");
    const mobileSummary = document.getElementById("mobile-bar-summary");
    const summaryOrders = document.getElementById("summary-orders-text");
    const summaryAmount = document.getElementById("summary-amount-text");

    const countText = `${orders.length} Pesanan`;
    countBadge.innerText = countText;
    if (mobileSummary) mobileSummary.innerText = countText;
    summaryOrders.innerText = `Total: ${orders.length} porsi`;

    let totalAmount = 0;
    orders.forEach(o => totalAmount += (o.price || 0));
    summaryAmount.innerText = `Total Tagihan: Rp ${totalAmount.toLocaleString("id-ID")}`;

    renderDesktopTable(orders);
    renderMobileCards(orders);
}

function renderDesktopTable(orders) {
    const tbody = document.getElementById("orders-table-body");
    if (!tbody) return;

    if (!orders || orders.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-12 text-slate-400">
                    <p class="text-2xl mb-1">🍜</p>
                    <p class="font-semibold text-slate-600">Belum ada pesanan masuk.</p>
                    <p class="text-xs text-slate-400 mt-0.5">Klik tombol <strong>"Tambah Pesanan"</strong> di atas untuk memulai!</p>
                </td>
            </tr>
        `;
        return;
    }

    const currentUsername = getSavedUsername().toLowerCase();
    const isSessionOpen = currentSession && currentSession.status === "OPEN";

    tbody.innerHTML = "";
    orders.forEach((o, index) => {
        const tr = document.createElement("tr");
        const isMyOrder = currentUsername && o.user_name.toLowerCase() === currentUsername;
        
        tr.className = `hover:bg-slate-50 transition ${isMyOrder ? 'bg-indigo-50/40 border-l-4 border-l-indigo-600' : ''}`;
        if (lastSavedOrder && lastSavedOrder.id === o.id) {
            tr.classList.add("bg-emerald-50", "animate-pulse");
        }

        const paymentStatus = o.payment_status || (o.is_paid ? "PAID" : "UNPAID");
        let paymentBadge = "";
        let claimPaidBtn = "";
        let editBtn = "";
        let cancelBtn = "";

        if (paymentStatus === "PAID" || o.is_paid) {
            paymentBadge = '<span class="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-bold text-[10px]">✅ Lunas</span>';
        } else if (paymentStatus === "PENDING_CONFIRMATION") {
            paymentBadge = '<span class="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-bold text-[10px] animate-pulse">🟡 Menunggu Konfirmasi</span>';
        } else {
            paymentBadge = '<span class="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-semibold text-[10px]">⏳ Belum</span>';
            claimPaidBtn = `<button onclick="window.claimPaid(${o.id})" class="px-2 py-1 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 rounded-lg text-[11px] font-bold transition flex items-center gap-1" title="Tandai sudah transfer/bayar">💳 Sudah Bayar</button>`;
        }

        const priceDisplay = o.price > 0
            ? `<span class="font-semibold text-slate-900">Rp ${o.price.toLocaleString("id-ID")}</span>`
            : `<span class="px-2 py-0.5 rounded-md bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-semibold">⏳ Belum di-set</span>`;

        const notesText = o.notes ? `<span class="text-[11px] text-slate-500 italic">"${o.notes}"</span>` : '-';
        const myBadge = isMyOrder ? `<span class="ml-1 px-1.5 py-0.2 bg-indigo-600 text-white rounded text-[9px] font-bold">Kamu</span>` : "";

        const notifyBtn = `<button onclick="window.notifySpecificOrder('${escapeHtml(o.user_name)}', '${escapeHtml(o.vendor)}', '${escapeHtml(o.item_name)}', '${escapeHtml(o.notes || "")}')" class="px-2 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded-lg text-[11px] font-semibold transition border border-emerald-200" title="Kirim Notif WA">📲 WA</button>`;

        if (paymentStatus === "UNPAID" && isSessionOpen && (isMyOrder || !currentUsername)) {
            editBtn = `<button onclick="window.openEditOrderModal(${o.id}, '${escapeHtml(o.user_name)}', '${escapeHtml(o.vendor)}', '${escapeHtml(o.item_name)}', '${escapeHtml(o.notes || "")}', ${o.price || 0})" class="px-2 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 rounded-lg text-[11px] font-semibold transition ml-1" title="Edit Pesanan">✏️ Edit</button>`;
            cancelBtn = `<button onclick="window.cancelMyOrder(${o.id}, '${escapeHtml(o.user_name)}')" class="px-2 py-1 bg-rose-50 hover:bg-rose-100 text-rose-600 rounded-lg text-[11px] font-semibold transition border border-rose-200 ml-1" title="Batalkan pesanan">✕</button>`;
        }

        tr.innerHTML = `
            <td class="py-3 px-3.5 text-center font-bold text-slate-500">${index + 1}</td>
            <td class="py-3 px-3.5 font-bold text-slate-800">${o.user_name} ${myBadge}</td>
            <td class="py-3 px-3.5 font-semibold text-indigo-700">${o.vendor}</td>
            <td class="py-3 px-3.5 font-medium text-slate-800">${o.item_name}</td>
            <td class="py-3 px-3.5 text-slate-600">${notesText}</td>
            <td class="py-3 px-3.5">${priceDisplay}</td>
            <td class="py-3 px-3.5 text-center">${paymentBadge}</td>
            <td class="py-3 px-3.5 text-right whitespace-nowrap space-x-1">${claimPaidBtn}${notifyBtn}${editBtn}${cancelBtn}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderMobileCards(orders) {
    const container = document.getElementById("orders-cards-container");
    if (!container) return;

    if (!orders || orders.length === 0) {
        container.innerHTML = `
            <div class="text-center py-10 text-slate-400 text-xs bg-white rounded-2xl border border-slate-200 p-6">
                <p class="text-3xl mb-1.5">🍜</p>
                <p class="font-bold text-slate-700 text-sm">Belum ada pesanan masuk</p>
                <p class="text-xs text-slate-400 mt-1">Gunakan tombol <strong>"Tambah Pesanan"</strong> di bawah untuk mulai menitip makan!</p>
            </div>
        `;
        return;
    }

    const currentUsername = getSavedUsername().toLowerCase();
    const isSessionOpen = currentSession && currentSession.status === "OPEN";

    container.innerHTML = "";
    orders.forEach((o, index) => {
        const isMyOrder = currentUsername && o.user_name.toLowerCase() === currentUsername;
        const card = document.createElement("div");
        card.className = `order-card-mobile p-3.5 rounded-2xl border bg-white shadow-sm flex flex-col justify-between gap-2.5 transition ${isMyOrder ? 'border-indigo-300 ring-1 ring-indigo-200 bg-indigo-50/20' : 'border-slate-200'}`;
        if (lastSavedOrder && lastSavedOrder.id === o.id) {
            card.classList.add("ring-2", "ring-emerald-400", "bg-emerald-50/40");
        }

        const paymentStatus = o.payment_status || (o.is_paid ? "PAID" : "UNPAID");
        let paymentBadge = "";
        let claimPaidBtn = "";
        let editBtn = "";
        let cancelBtn = "";

        if (paymentStatus === "PAID" || o.is_paid) {
            paymentBadge = '<span class="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-bold text-[10px]">✅ Lunas</span>';
        } else if (paymentStatus === "PENDING_CONFIRMATION") {
            paymentBadge = '<span class="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-bold text-[10px] animate-pulse">🟡 Menunggu Konfirmasi</span>';
        } else {
            paymentBadge = '<span class="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-semibold text-[10px]">⏳ Belum</span>';
            claimPaidBtn = `<button onclick="window.claimPaid(${o.id})" class="py-1.5 px-2.5 bg-amber-50 hover:bg-amber-100 text-amber-800 rounded-xl text-xs font-bold transition border border-amber-300 flex items-center gap-1">💳 Sudah Bayar</button>`;
        }

        const priceDisplay = o.price > 0
            ? `<span class="font-extrabold text-slate-900 text-sm">Rp ${o.price.toLocaleString("id-ID")}</span>`
            : `<span class="px-2 py-0.5 rounded-md bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-bold">⏳ Belum di-set</span>`;

        const notesText = o.notes ? `<p class="text-xs text-slate-500 italic mt-0.5 bg-slate-50 p-2 rounded-lg border border-slate-100">"${o.notes}"</p>` : "";
        const myBadge = isMyOrder ? `<span class="px-1.5 py-0.2 bg-indigo-600 text-white rounded text-[9px] font-bold uppercase tracking-wider">Kamu</span>` : "";

        if (paymentStatus === "UNPAID" && isSessionOpen && (isMyOrder || !currentUsername)) {
            editBtn = `<button onclick="window.openEditOrderModal(${o.id}, '${escapeHtml(o.user_name)}', '${escapeHtml(o.vendor)}', '${escapeHtml(o.item_name)}', '${escapeHtml(o.notes || "")}', ${o.price || 0})" class="py-1.5 px-2.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-xl text-xs font-bold transition border border-indigo-200 flex items-center gap-1">✏️ Edit</button>`;
            cancelBtn = `<button onclick="window.cancelMyOrder(${o.id}, '${escapeHtml(o.user_name)}')" class="py-1.5 px-2.5 bg-rose-50 hover:bg-rose-100 text-rose-600 rounded-xl text-xs font-bold transition border border-rose-200 flex items-center gap-1" title="Batalkan pesanan">✕ Batal</button>`;
        }

        const notifyBtn = `<button onclick="window.notifySpecificOrder('${escapeHtml(o.user_name)}', '${escapeHtml(o.vendor)}', '${escapeHtml(o.item_name)}', '${escapeHtml(o.notes || "")}')" class="py-1.5 px-2.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded-xl text-xs font-bold transition border border-emerald-200 flex items-center gap-1"><span>📲</span> Notif WA</button>`;

        card.innerHTML = `
            <div class="flex items-start justify-between gap-2">
                <div class="flex items-center gap-2">
                    <span class="w-6 h-6 rounded-full bg-slate-100 text-slate-700 flex items-center justify-center font-extrabold text-[11px] flex-shrink-0">
                        ${index + 1}
                    </span>
                    <div>
                        <span class="font-extrabold text-slate-800 text-sm">${o.user_name}</span>
                        ${myBadge}
                    </div>
                </div>
                <div class="flex items-center gap-1.5">
                    <span class="text-[10px] font-extrabold uppercase tracking-wider text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-md border border-indigo-100">${o.vendor}</span>
                    ${paymentBadge}
                </div>
            </div>

            <div class="pl-8">
                <h4 class="font-bold text-slate-900 text-sm leading-snug">${o.item_name}</h4>
                ${notesText}
            </div>

            <div class="pl-8 pt-1 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 mt-1">
                <div>
                    ${priceDisplay}
                </div>
                <div class="flex flex-wrap items-center gap-1.5">
                    ${claimPaidBtn}
                    ${notifyBtn}
                    ${editBtn}
                    ${cancelBtn}
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/'/g, "\\'");
}

function buildWhatsAppUrl(userName, vendor, itemName, notes) {
    const coordName = currentSession ? currentSession.coordinator_name : "Koordinator";
    let text = `Halo kak ${coordName}, aku ${userName} sudah titip pesanan:\n• *${itemName}* (${vendor})${notes ? `\n• Catatan: ${notes}` : ""}\n\nTolong dicek ya kak, makasih! 🙏`;

    let phone = currentSession && currentSession.coordinator_phone ? currentSession.coordinator_phone.replace(/[^0-9]/g, "") : "";
    if (phone.startsWith("0")) {
        phone = "62" + phone.slice(1);
    }

    if (phone) {
        return `https://wa.me/${phone}?text=${encodeURIComponent(text)}`;
    }
    return `https://wa.me/?text=${encodeURIComponent(text)}`;
}

window.notifySpecificOrder = function(userName, vendor, itemName, notes) {
    const url = buildWhatsAppUrl(userName, vendor, itemName, notes);
    window.open(url, "_blank");
};

window.cancelMyOrder = async function(orderId, userName) {
    if (!confirm(`Batalkan pesanan untuk "${userName}"?`)) return;
    try {
        const resp = await fetch(`/api/v1/orders/${orderId}`, {
            method: "DELETE"
        });
        if (resp.ok) {
            await loadOrders();
            await fetchSuggestions();
            showToast("Pesanan berhasil dibatalkan.", "success");
        } else {
            showToast("Gagal membatalkan pesanan.", "error");
        }
    } catch (err) {
        showToast("Terjadi kesalahan jaringan.", "error");
    }
};

window.claimPaid = async function(orderId) {
    if (!confirm("Tandai pesanan ini sudah kamu bayar lunas? Status akan menunggu konfirmasi Koordinator.")) return;
    try {
        const resp = await fetch(`/api/v1/orders/${orderId}/claim-paid`, {
            method: "POST"
        });
        if (resp.ok) {
            showToast("Berhasil ditandai sudah bayar! Menunggu konfirmasi Koordinator. 👍", "success");
            await loadOrders();
        } else {
            const err = await resp.json();
            showToast(err.detail || "Gagal menandai pembayaran.", "error");
        }
    } catch (e) {
        showToast("Terjadi kesalahan jaringan.", "error");
    }
};

window.openEditOrderModal = function(orderId, userName, vendor, itemName, notes, price) {
    const modal = document.getElementById("modal-order");
    document.getElementById("modal-step-form").classList.remove("hidden");
    document.getElementById("modal-step-success").classList.add("hidden");

    document.getElementById("modal-title").innerHTML = "<span>✏️</span> Edit Pesanan Kamu";
    document.getElementById("edit-order-id").value = orderId;
    document.getElementById("input-username").value = userName;
    document.getElementById("input-tenant").value = vendor;
    document.getElementById("input-menu").value = itemName;
    document.getElementById("input-notes").value = notes || "";
    document.getElementById("input-price").value = price > 0 ? price : "";
    
    const label = document.getElementById("btn-submit-order-label");
    if (label) label.innerText = "Simpan Perubahan";

    modal.classList.remove("hidden");
    modal.classList.add("flex");
    document.getElementById("input-menu").focus();
};

function setupQuickNames() {
    const savedName = getSavedUsername();
    if (savedName) {
        document.getElementById("input-username").value = savedName;
    }

    document.querySelectorAll(".name-tag").forEach(btn => {
        btn.addEventListener("click", () => {
            const name = btn.innerText.trim();
            document.getElementById("input-username").value = name;
            saveUsername(name);
        });
    });
}

function setupModalHandlers() {
    const modal = document.getElementById("modal-order");
    const openBtn = document.getElementById("btn-open-order-modal");
    const mobileOpenBtn = document.getElementById("btn-mobile-open-order-modal");
    const closeBtn = document.getElementById("btn-close-modal");
    const finishBtn = document.getElementById("btn-finish-and-view-table");

    function openModal() {
        if (!currentSession || currentSession.status !== "OPEN") {
            showToast("Sesi pemesanan sudah ditutup!", "warning");
            return;
        }
        document.getElementById("modal-step-form").classList.remove("hidden");
        document.getElementById("modal-step-success").classList.add("hidden");
        
        // Reset modal to create mode
        document.getElementById("modal-title").innerHTML = "<span>🍜</span> Tambah Pesanan Baru";
        document.getElementById("edit-order-id").value = "";
        const label = document.getElementById("btn-submit-order-label");
        if (label) label.innerText = "Simpan Pesanan";
        document.getElementById("input-tenant").value = "";
        document.getElementById("input-menu").value = "";
        document.getElementById("input-notes").value = "";
        document.getElementById("input-price").value = "";

        modal.classList.remove("hidden");
        modal.classList.add("flex");

        const savedName = getSavedUsername();
        if (savedName) {
            document.getElementById("input-username").value = savedName;
            document.getElementById("input-tenant").focus();
        } else {
            document.getElementById("input-username").focus();
        }
    }

    function closeModal() {
        modal.classList.add("hidden");
        modal.classList.remove("flex");
    }

    if (openBtn) openBtn.addEventListener("click", openModal);
    if (mobileOpenBtn) mobileOpenBtn.addEventListener("click", openModal);
    if (closeBtn) closeBtn.addEventListener("click", closeModal);
    if (finishBtn) finishBtn.addEventListener("click", closeModal);

    modal.addEventListener("click", (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && !modal.classList.contains("hidden")) {
            closeModal();
        }
    });
}

function setupFormEventListeners() {
    const tenantInput = document.getElementById("input-tenant");
    tenantInput.addEventListener("input", updateMenuDatalist);
    tenantInput.addEventListener("change", updateMenuDatalist);

    const menuInput = document.getElementById("input-menu");
    menuInput.addEventListener("input", handleMenuInput);
    menuInput.addEventListener("change", handleMenuInput);

    const wheelOpenItemBtn = document.getElementById("wheel-open-item");
    if (wheelOpenItemBtn) {
        wheelOpenItemBtn.addEventListener("click", () => {
            window.MenuWheel.open({
                mode: "item",
                onApply: (candidate) => {
                    const targetTenant = document.getElementById("input-tenant");
                    const targetMenu = document.getElementById("input-menu");
                    const targetPrice = document.getElementById("input-price");

                    targetTenant.value = candidate.vendor;
                    targetMenu.value = candidate.label;
                    targetPrice.value = candidate.price != null ? candidate.price : "";

                    [targetTenant, targetMenu, targetPrice].forEach((el) => {
                        el.dispatchEvent(new Event("input", { bubbles: true }));
                        el.dispatchEvent(new Event("change", { bubbles: true }));
                    });
                }
            });
        });
    }

    const form = document.getElementById("order-form");
    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        if (!currentSession || currentSession.status !== "OPEN") {
            showToast("Sesi pemesanan sudah ditutup atau tidak aktif!", "warning");
            return;
        }

        const username = document.getElementById("input-username").value.trim();
        const tenant = document.getElementById("input-tenant").value.trim();
        const menu = document.getElementById("input-menu").value.trim();
        const notes = document.getElementById("input-notes").value.trim();
        const priceInput = document.getElementById("input-price").value.trim();
        const price = priceInput ? parseInt(priceInput, 10) : 0;

        if (!username) {
            showToast("Harap masukkan nama Anda!", "warning");
            document.getElementById("input-username").focus();
            return;
        }
        if (!tenant) {
            showToast("Harap isi nama tenant / warung!", "warning");
            document.getElementById("input-tenant").focus();
            return;
        }
        if (!menu) {
            showToast("Harap isi menu pesanan!", "warning");
            document.getElementById("input-menu").focus();
            return;
        }

        saveUsername(username);

        const editOrderId = document.getElementById("edit-order-id").value;
        const submitBtn = document.getElementById("btn-submit-order");

        if (editOrderId) {
            submitBtn.disabled = true;
            submitBtn.innerText = "Memperbarui...";
            try {
                const resp = await fetch(`/api/v1/orders/${editOrderId}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        vendor: tenant,
                        item_name: menu,
                        variant: "",
                        notes: notes,
                        price: price
                    })
                });
                if (!resp.ok) {
                    const err = await resp.json();
                    showToast(`Gagal: ${err.detail || "Gagal memperbarui pesanan"}`, "error");
                    return;
                }
                document.getElementById("modal-order").classList.add("hidden");
                document.getElementById("modal-order").classList.remove("flex");
                document.getElementById("edit-order-id").value = "";
                await loadOrders();
                await fetchSuggestions();
                showToast("Pesanan kamu berhasil diperbarui! ✨", "success");
            } catch (err) {
                showToast("Terjadi kesalahan jaringan.", "error");
            } finally {
                submitBtn.disabled = false;
                const label = document.getElementById("btn-submit-order-label");
                if (label) label.innerText = "Simpan Pesanan";
            }
            return;
        }

        submitBtn.disabled = true;
        submitBtn.innerText = "Menyimpan...";

        try {
            const resp = await fetch(`/api/v1/sessions/${currentSession.id}/orders`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_name: username,
                    vendor: tenant,
                    item_name: menu,
                    variant: "",
                    notes: notes,
                    price: price
                })
            });

            if (!resp.ok) {
                const err = await resp.json();
                showToast(`Gagal: ${err.detail || "Gagal menyimpan pesanan"}`, "error");
                return;
            }

            const savedOrder = await resp.json();
            lastSavedOrder = savedOrder;

            document.getElementById("input-menu").value = "";
            document.getElementById("input-notes").value = "";
            document.getElementById("input-price").value = "";

            await loadOrders();
            await fetchSuggestions();

            showSuccessNotificationStep(savedOrder);
            showToast("Pesanan tersimpan! Silakan beri notif ke koordinator.", "success");

        } catch (err) {
            console.error("Error saving order:", err);
            showToast("Terjadi kesalahan jaringan.", "error");
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = "<span>💾</span> Simpan Pesanan";
        }
    });
}

function showSuccessNotificationStep(order) {
    document.getElementById("modal-step-form").classList.add("hidden");
    const successStep = document.getElementById("modal-step-success");
    successStep.classList.remove("hidden");

    const preview = document.getElementById("order-success-preview");
    preview.innerHTML = `
        <div class="flex justify-between border-b border-slate-200 pb-1.5">
            <span class="text-slate-500">Pemesan:</span>
            <span class="font-bold text-slate-800">${order.user_name}</span>
        </div>
        <div class="flex justify-between border-b border-slate-200 pb-1.5">
            <span class="text-slate-500">Tenant &amp; Menu:</span>
            <span class="font-semibold text-indigo-700">${order.vendor} - ${order.item_name}</span>
        </div>
        ${order.notes ? `
        <div class="flex justify-between border-b border-slate-200 pb-1.5">
            <span class="text-slate-500">Catatan:</span>
            <span class="font-medium text-slate-700 italic">"${order.notes}"</span>
        </div>` : ''}
        <div class="flex justify-between pt-1">
            <span class="text-slate-500">Biaya:</span>
            <span class="font-bold text-slate-900">${order.price > 0 ? `Rp ${order.price.toLocaleString("id-ID")}` : 'Belum di-set (Diisi Koordinator)'}</span>
        </div>
    `;

    const waUrl = buildWhatsAppUrl(order.user_name, order.vendor, order.item_name, order.notes);
    const waBtn = document.getElementById("btn-wa-notify-coordinator");
    waBtn.href = waUrl;

    const copyBtn = document.getElementById("btn-copy-wa-msg");
    copyBtn.onclick = async () => {
        const coordName = currentSession ? currentSession.coordinator_name : "Koordinator";
        const text = `Halo kak ${coordName}, aku ${order.user_name} sudah titip pesanan:\n• ${order.item_name} (${order.vendor})${order.notes ? ` (Catatan: ${order.notes})` : ""}. Tolong dicek ya kak!`;
        await navigator.clipboard.writeText(text);
        showToast("Teks notifikasi WhatsApp disalin!", "success");
    };
}

function startCountdown(cutoffIsoString) {
    if (countdownInterval) clearInterval(countdownInterval);

    const timerElem = document.getElementById("countdown-timer");
    if (!cutoffIsoString) {
        timerElem.innerText = "Tanpa Batas";
        return;
    }

    const cutoffDate = parseUtcDate(cutoffIsoString);
    if (!cutoffDate) {
        timerElem.innerText = "Tanpa Batas";
        return;
    }

    const cutoffTime = cutoffDate.getTime();

    function update() {
        const now = new Date().getTime();
        const diff = cutoffTime - now;

        if (diff <= 0) {
            timerElem.innerText = "DITUTUP";
            timerElem.className = "text-base sm:text-lg font-bold text-rose-600";
            if (countdownInterval) clearInterval(countdownInterval);
            fetchActiveSession();
            return;
        }

        const minutes = Math.floor(diff / 60000);
        const seconds = Math.floor((diff % 60000) / 1000);
        timerElem.innerText = `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
    }

    update();
    countdownInterval = setInterval(update, 1000);
}

document.addEventListener("DOMContentLoaded", initApp);
