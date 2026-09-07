let currentSession = null;
let pollTimer = null;
let countdownInterval = null;
let suggestionsData = { tenants: [], menus: {}, variants: {} };
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
            return;
        }

        currentSession = data;
        document.getElementById("no-session-alert").classList.add("hidden");
        document.getElementById("session-banner").classList.remove("hidden");
        document.getElementById("orders-section").classList.remove("hidden");

        document.getElementById("session-title").innerText = data.title;
        const phoneInfo = data.coordinator_phone ? ` (${data.coordinator_phone})` : "";
        document.getElementById("session-coordinator").innerText = `Koordinator: ${data.coordinator_name}${phoneInfo}`;
        document.getElementById("session-vendors").innerText = `Saran Tenant: ${data.vendor_options ? data.vendor_options.join(", ") : "-"}`;
        document.getElementById("payment-info-text").innerText = data.payment_info || "Belum ada detail pembayaran.";

        const statusBadge = document.getElementById("session-status-badge");
        const openModalBtn = document.getElementById("btn-open-order-modal");

        if (data.status === "CLOSED") {
            statusBadge.className = "px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-700";
            statusBadge.innerText = "SESI DITUTUP";
            openModalBtn.disabled = true;
            openModalBtn.innerHTML = "<span>🔒</span> Pemesanan Ditutup";
            openModalBtn.className = "w-full sm:w-auto px-5 py-2.5 bg-slate-300 text-slate-500 font-semibold rounded-xl text-sm cursor-not-allowed flex items-center justify-center gap-2";
            document.getElementById("countdown-timer").innerText = "DITUTUP";
        } else {
            statusBadge.className = "px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700";
            statusBadge.innerText = "MEMBUAT PESANAN";
            openModalBtn.disabled = false;
            openModalBtn.innerHTML = '<span class="text-base">➕</span> Tambah Pesanan';
            openModalBtn.className = "w-full sm:w-auto px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 active:scale-[0.99] text-white font-bold text-sm rounded-xl transition shadow-md flex items-center justify-center gap-2";
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
            updateMenuAndVariantDatalists();
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

function updateMenuAndVariantDatalists() {
    const selectedTenant = document.getElementById("input-tenant").value.trim();
    const menuDatalist = document.getElementById("datalist-menus");
    const variantDatalist = document.getElementById("datalist-variants");

    if (!menuDatalist || !variantDatalist) return;

    menuDatalist.innerHTML = "";
    variantDatalist.innerHTML = "";

    // If tenant selected has menus in suggestionsData
    if (selectedTenant && suggestionsData.menus && suggestionsData.menus[selectedTenant]) {
        suggestionsData.menus[selectedTenant].forEach(m => {
            const opt = document.createElement("option");
            opt.value = m;
            menuDatalist.appendChild(opt);
        });
    } else {
        // Collect all distinct menus across all tenants
        const allMenus = new Set();
        Object.values(suggestionsData.menus || {}).forEach(arr => {
            arr.forEach(m => allMenus.add(m));
        });
        allMenus.forEach(m => {
            const opt = document.createElement("option");
            opt.value = m;
            menuDatalist.appendChild(opt);
        });
    }

    // Variants
    if (selectedTenant && suggestionsData.variants && suggestionsData.variants[selectedTenant]) {
        suggestionsData.variants[selectedTenant].forEach(v => {
            const opt = document.createElement("option");
            opt.value = v;
            variantDatalist.appendChild(opt);
        });
    } else {
        const allVariants = new Set(["Pangsit Rebus", "Pangsit Goreng", "Polos", "Pedas Sedang", "Tidak Pedas", "Level 1", "Level 2"]);
        allVariants.forEach(v => {
            const opt = document.createElement("option");
            opt.value = v;
            variantDatalist.appendChild(opt);
        });
    }
}

async function loadOrders() {
    if (!currentSession) return;
    try {
        const resp = await fetch(`/api/v1/sessions/${currentSession.id}/orders`);
        const orders = await resp.json();
        renderOrdersTable(orders);
    } catch (err) {
        console.error("Gagal memuat pesanan:", err);
    }
}

function renderOrdersTable(orders) {
    const tbody = document.getElementById("orders-table-body");
    const countBadge = document.getElementById("orders-count-badge");
    const summaryOrders = document.getElementById("summary-orders-text");
    const summaryAmount = document.getElementById("summary-amount-text");

    countBadge.innerText = `${orders.length} Pesanan`;
    summaryOrders.innerText = `Total: ${orders.length} porsi`;

    let totalAmount = 0;
    orders.forEach(o => totalAmount += (o.price || 0));
    summaryAmount.innerText = `Total Tagihan: Rp ${totalAmount.toLocaleString("id-ID")}`;

    if (!orders || orders.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-12 text-slate-400">
                    <p class="text-2xl mb-1">🍜</p>
                    <p class="font-semibold text-slate-600">Belum ada pesanan masuk.</p>
                    <p class="text-xs text-slate-400 mt-0.5">Klik tombol <strong>"Tambah Pesanan"</strong> di atas untuk memulai titipan!</p>
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

        const paymentBadge = o.is_paid
            ? '<span class="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-semibold text-[10px]">✅ Lunas</span>'
            : '<span class="px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 font-semibold text-[10px]">⏳ Belum</span>';

        const priceDisplay = o.price > 0
            ? `<span class="font-semibold text-slate-900">Rp ${o.price.toLocaleString("id-ID")}</span>`
            : `<span class="px-2 py-0.5 rounded-md bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-semibold">⏳ Belum di-set</span>`;

        const variantBadge = o.variant
            ? `<span class="bg-indigo-100 text-indigo-700 font-medium px-1.5 py-0.5 rounded text-[10px] mr-1">${o.variant}</span>`
            : "";

        const notesText = o.notes ? `<p class="text-[11px] text-slate-500 italic mt-0.5">"${o.notes}"</p>` : "";

        const myBadge = isMyOrder ? `<span class="ml-1 px-1.5 py-0.2 bg-indigo-600 text-white rounded text-[9px] font-bold">Kamu</span>` : "";

        const notifyBtn = `<button onclick="window.notifySpecificOrder('${escapeHtml(o.user_name)}', '${escapeHtml(o.vendor)}', '${escapeHtml(o.item_name)}', '${escapeHtml(o.variant || "")}', '${escapeHtml(o.notes || "")}')" class="px-2 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded-lg text-[11px] font-semibold transition border border-emerald-200" title="Kirim Notif WA ke Koordinator">📲 WA</button>`;

        const cancelBtn = (isSessionOpen && isMyOrder)
            ? `<button onclick="window.cancelMyOrder(${o.id}, '${escapeHtml(o.user_name)}')" class="px-2 py-1 bg-rose-50 hover:bg-rose-100 text-rose-600 rounded-lg text-[11px] font-semibold transition border border-rose-200 ml-1" title="Batalkan pesanan">✕</button>`
            : "";

        tr.innerHTML = `
            <td class="py-3 px-3.5 text-center font-bold text-slate-500">${index + 1}</td>
            <td class="py-3 px-3.5 font-bold text-slate-800">${o.user_name} ${myBadge}</td>
            <td class="py-3 px-3.5 font-semibold text-indigo-700">${o.vendor}</td>
            <td class="py-3 px-3.5 font-medium text-slate-800">${o.item_name}</td>
            <td class="py-3 px-3.5 text-slate-600">${variantBadge}${notesText}</td>
            <td class="py-3 px-3.5">${priceDisplay}</td>
            <td class="py-3 px-3.5 text-center">${paymentBadge}</td>
            <td class="py-3 px-3.5 text-right whitespace-nowrap">${notifyBtn}${cancelBtn}</td>
        `;
        tbody.appendChild(tr);
    });
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/'/g, "\\'");
}

function buildWhatsAppUrl(userName, vendor, itemName, variant, notes) {
    const coordName = currentSession ? currentSession.coordinator_name : "Koordinator";
    let text = `Halo kak ${coordName}, aku ${userName} sudah titip pesanan:\n• *${itemName}* (${vendor})${variant ? `\n• Varian: ${variant}` : ""}${notes ? `\n• Catatan: ${notes}` : ""}\n\nTolong dicek ya kak, makasih! 🙏`;

    let phone = currentSession && currentSession.coordinator_phone ? currentSession.coordinator_phone.replace(/[^0-9]/g, "") : "";
    if (phone.startsWith("0")) {
        phone = "62" + phone.slice(1);
    }

    if (phone) {
        return `https://wa.me/${phone}?text=${encodeURIComponent(text)}`;
    }
    return `https://wa.me/?text=${encodeURIComponent(text)}`;
}

window.notifySpecificOrder = function(userName, vendor, itemName, variant, notes) {
    const url = buildWhatsAppUrl(userName, vendor, itemName, variant, notes);
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
    const closeBtn = document.getElementById("btn-close-modal");
    const finishBtn = document.getElementById("btn-finish-and-view-table");

    function openModal() {
        if (!currentSession || currentSession.status !== "OPEN") {
            showToast("Sesi pemesanan sudah ditutup!", "warning");
            return;
        }
        document.getElementById("modal-step-form").classList.remove("hidden");
        document.getElementById("modal-step-success").classList.add("hidden");
        modal.classList.remove("hidden");

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
    }

    openBtn.addEventListener("click", openModal);
    closeBtn.addEventListener("click", closeModal);
    finishBtn.addEventListener("click", closeModal);

    // Close on backdrop click
    modal.addEventListener("click", (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    // ESC to close
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && !modal.classList.contains("hidden")) {
            closeModal();
        }
    });
}

function setupFormEventListeners() {
    const tenantInput = document.getElementById("input-tenant");
    tenantInput.addEventListener("input", updateMenuAndVariantDatalists);
    tenantInput.addEventListener("change", updateMenuAndVariantDatalists);

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
        const variant = document.getElementById("input-variant").value.trim();
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

        const submitBtn = document.getElementById("btn-submit-order");
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
                    variant: variant,
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

            // Reset optional inputs
            document.getElementById("input-menu").value = "";
            document.getElementById("input-variant").value = "";
            document.getElementById("input-notes").value = "";
            document.getElementById("input-price").value = "";

            // Refresh table and suggestions
            await loadOrders();
            await fetchSuggestions();

            // Transition to Step 2: WhatsApp Notification
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
        ${order.variant ? `
        <div class="flex justify-between border-b border-slate-200 pb-1.5">
            <span class="text-slate-500">Varian:</span>
            <span class="font-medium text-slate-700">${order.variant}</span>
        </div>` : ''}
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

    const waUrl = buildWhatsAppUrl(order.user_name, order.vendor, order.item_name, order.variant, order.notes);
    const waBtn = document.getElementById("btn-wa-notify-coordinator");
    waBtn.href = waUrl;

    const copyBtn = document.getElementById("btn-copy-wa-msg");
    copyBtn.onclick = async () => {
        const coordName = currentSession ? currentSession.coordinator_name : "Koordinator";
        const text = `Halo kak ${coordName}, aku ${order.user_name} sudah titip pesanan:\n• ${order.item_name} (${order.vendor})${order.variant ? ` [${order.variant}]` : ""}${order.notes ? ` (Catatan: ${order.notes})` : ""}. Tolong dicek ya kak!`;
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
            timerElem.className = "text-lg font-bold text-rose-600";
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
