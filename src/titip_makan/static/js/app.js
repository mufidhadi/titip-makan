// Menu catalog with default variants and prices
const MENU_CATALOG = {
    "Mie Ayam": [
        { name: "Mie Ayam", variants: ["Pangsit Rebus", "Pangsit Goreng", "Polos"], price: 15000 },
        { name: "Mie Ayam Bakso", variants: ["Pangsit Rebus", "Pangsit Goreng"], price: 18000 }
    ],
    "Babun": [
        { name: "Babun Nasi Ayam", variants: ["Lada Hitam", "Kremes", "Daging Suwir"], price: 22000 },
        { name: "Babun Nasi Telor", variants: ["Telor Dobel", "Telor Ceplok", "Telor Dadar"], price: 16000 }
    ],
    "Nasi Goreng": [
        { name: "Nasi Goreng Ayam", variants: ["Pedas Sedang", "Pedas Banget", "Tidak Pedas"], price: 18000 },
        { name: "Nasi Goreng Telor", variants: ["Pedas Sedang", "Tidak Pedas"], price: 15000 }
    ],
    "Dimsum": [
        { name: "Dimsum Ori isi 5", variants: ["Ori", "Mentai", "Frozen 1 Pack"], price: 20000 }
    ]
};

let currentSession = null;
let pollTimer = null;
let countdownInterval = null;

async function initApp() {
    setupQuickNames();
    await fetchActiveSession();
    setupEventListeners();
}

function parseUtcDate(dateStr) {
    if (!dateStr) return null;
    if (!dateStr.endsWith("Z") && !dateStr.includes("+")) {
        dateStr += "Z";
    }
    return new Date(dateStr);
}

async function fetchActiveSession() {
    try {
        const resp = await fetch("/api/v1/sessions/latest");
        const data = await resp.json();
        
        if (!data) {
            document.getElementById("session-banner").classList.add("hidden");
            document.getElementById("order-grid").classList.add("hidden");
            document.getElementById("no-session-alert").classList.remove("hidden");
            return;
        }

        currentSession = data;
        document.getElementById("no-session-alert").classList.add("hidden");
        document.getElementById("session-banner").classList.remove("hidden");
        document.getElementById("order-grid").classList.remove("hidden");

        document.getElementById("session-title").innerText = data.title;
        document.getElementById("session-coordinator").innerText = `Koordinator: ${data.coordinator_name}`;
        document.getElementById("session-vendors").innerText = `Pilihan Vendor: ${data.vendor_options.join(", ")}`;
        document.getElementById("payment-info-text").innerText = data.payment_info || "Belum ada detail pembayaran.";

        const statusBadge = document.getElementById("session-status-badge");
        const submitBtn = document.getElementById("btn-submit-order");

        if (data.status === "CLOSED") {
            statusBadge.className = "px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-700";
            statusBadge.innerText = "SESI DITUTUP";
            submitBtn.disabled = true;
            submitBtn.innerHTML = "<span>🔒</span> Pemesanan Ditutup";
            submitBtn.className = "w-full py-2.5 bg-slate-300 text-slate-500 font-semibold rounded-xl text-sm cursor-not-allowed flex items-center justify-center gap-2";
            document.getElementById("countdown-timer").innerText = "DITUTUP";
        } else {
            statusBadge.className = "px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700";
            statusBadge.innerText = "MEMBUAT PESANAN";
            submitBtn.disabled = false;
            submitBtn.innerHTML = "<span>🚀</span> Kirim Pesanan (Anti-Ketimpa)";
            submitBtn.className = "w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 active:scale-[0.99] text-white font-semibold rounded-xl text-sm transition shadow-sm flex items-center justify-center gap-2";
            startCountdown(data.cutoff_at);
        }

        populateVendors(data.vendor_options);
        await loadOrders();

        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(loadOrders, 5000);

    } catch (err) {
        console.error("Gagal memuat sesi aktif:", err);
    }
}

function populateVendors(vendors) {
    const select = document.getElementById("select-vendor");
    select.innerHTML = '<option value="">-- Pilih Vendor --</option>';
    vendors.forEach(v => {
        const opt = document.createElement("option");
        opt.value = v;
        opt.innerText = v;
        select.appendChild(opt);
    });
    // Option for custom vendor
    const customOpt = document.createElement("option");
    customOpt.value = "__custom__";
    customOpt.innerText = "➕ Tambah Tenant / Vendor Lain...";
    customOpt.className = "font-semibold text-indigo-600";
    select.appendChild(customOpt);
}

function handleVendorChange() {
    const vendorSelect = document.getElementById("select-vendor");
    const vendorVal = vendorSelect.value;
    const customVendorWrapper = document.getElementById("custom-vendor-wrapper");
    const customVendorInput = document.getElementById("input-custom-vendor");
    const menuSelect = document.getElementById("select-menu");
    const customMenuWrapper = document.getElementById("custom-menu-wrapper");
    const customVariantWrapper = document.getElementById("custom-variant-wrapper");
    const variantContainer = document.getElementById("variant-options");

    menuSelect.innerHTML = '<option value="">-- Pilih Menu --</option>';
    variantContainer.innerHTML = "";
    document.getElementById("price-display").innerText = "Rp 0";

    if (vendorVal === "__custom__") {
        customVendorWrapper.classList.remove("hidden");
        customVendorInput.focus();
        
        const opt = document.createElement("option");
        opt.value = "__custom__";
        opt.innerText = "➕ Ketik Menu Kustom...";
        opt.selected = true;
        menuSelect.appendChild(opt);

        handleMenuChange();
        return;
    } else {
        customVendorWrapper.classList.add("hidden");
        customMenuWrapper.classList.add("hidden");
        customVariantWrapper.classList.add("hidden");
    }

    if (!vendorVal) return;

    const items = MENU_CATALOG[vendorVal] || [
        { name: `${vendorVal} Standar`, variants: ["Biasa", "Spesial"], price: 15000 }
    ];

    items.forEach(item => {
        const opt = document.createElement("option");
        opt.value = item.name;
        opt.innerText = `${item.name} (~Rp ${item.price.toLocaleString("id-ID")})`;
        opt.dataset.itemData = JSON.stringify(item);
        menuSelect.appendChild(opt);
    });

    const customMenuOpt = document.createElement("option");
    customMenuOpt.value = "__custom__";
    customMenuOpt.innerText = "➕ Menu Lainnya (Ketik Manual)...";
    customMenuOpt.className = "font-semibold text-indigo-600";
    menuSelect.appendChild(customMenuOpt);
}

function handleMenuChange() {
    const menuSelect = document.getElementById("select-menu");
    const selectedOption = menuSelect.options[menuSelect.selectedIndex];
    const container = document.getElementById("variant-options");
    const customMenuWrapper = document.getElementById("custom-menu-wrapper");
    const customVariantWrapper = document.getElementById("custom-variant-wrapper");
    container.innerHTML = "";

    if (!selectedOption || !selectedOption.value) {
        customMenuWrapper.classList.add("hidden");
        customVariantWrapper.classList.add("hidden");
        document.getElementById("price-display").innerText = "Rp 0";
        return;
    }

    if (selectedOption.value === "__custom__") {
        customMenuWrapper.classList.remove("hidden");
        customVariantWrapper.classList.remove("hidden");
        document.getElementById("input-custom-menu").focus();

        const customPriceInput = document.getElementById("input-custom-price");
        const priceVal = parseInt(customPriceInput.value, 10) || 0;
        document.getElementById("price-display").innerText = `Rp ${priceVal.toLocaleString("id-ID")}`;
        return;
    }

    customMenuWrapper.classList.add("hidden");
    customVariantWrapper.classList.add("hidden");

    const item = JSON.parse(selectedOption.dataset.itemData || "{}");
    document.getElementById("price-display").innerText = `Rp ${(item.price || 0).toLocaleString("id-ID")}`;

    if (item.variants && item.variants.length > 0) {
        item.variants.forEach((v, idx) => {
            const label = document.createElement("label");
            label.className = "flex items-center gap-2 p-2 rounded-lg border border-slate-200 hover:bg-indigo-50/50 cursor-pointer text-xs";
            label.innerHTML = `
                <input type="radio" name="order-variant" value="${v}" ${idx === 0 ? "checked" : ""} class="text-indigo-600 focus:ring-indigo-500">
                <span>${v}</span>
            `;
            container.appendChild(label);
        });
    }

    const customVarLabel = document.createElement("label");
    customVarLabel.className = "flex items-center gap-2 p-2 rounded-lg border border-indigo-200 bg-indigo-50/30 hover:bg-indigo-50/60 cursor-pointer text-xs col-span-2";
    customVarLabel.innerHTML = `
        <input type="radio" name="order-variant" value="__custom__" class="text-indigo-600 focus:ring-indigo-500">
        <span class="font-semibold text-indigo-700">➕ Varian Kustom Lainnya</span>
    `;
    container.appendChild(customVarLabel);

    document.querySelectorAll('input[name="order-variant"]').forEach(radio => {
        radio.addEventListener("change", () => {
            if (radio.value === "__custom__") {
                customVariantWrapper.classList.remove("hidden");
                document.getElementById("input-custom-variant").focus();
            } else {
                customVariantWrapper.classList.add("hidden");
            }
        });
    });
}

async function loadOrders() {
    if (!currentSession) return;
    try {
        const resp = await fetch(`/api/v1/sessions/${currentSession.id}/orders`);
        const orders = await resp.json();
        renderOrdersList(orders);
    } catch (err) {
        console.error("Gagal memuat pesanan:", err);
    }
}

function renderOrdersList(orders) {
    const list = document.getElementById("orders-list");
    const countBadge = document.getElementById("orders-count-badge");
    countBadge.innerText = `${orders.length} Pesanan`;

    if (!orders || orders.length === 0) {
        list.innerHTML = `
            <div class="text-center py-10 text-slate-400 text-xs">
                Belum ada pesanan masuk. Jadilah yang pertama memesan! 🍜
            </div>
        `;
        return;
    }

    const isSessionOpen = currentSession && currentSession.status === "OPEN";

    list.innerHTML = "";
    orders.forEach((o, index) => {
        const item = document.createElement("div");
        item.className = "order-card p-3 rounded-xl border border-slate-100 bg-slate-50 flex items-center justify-between gap-3 text-xs";
        
        const statusBadge = o.is_paid 
            ? '<span class="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-semibold text-[10px]">✅ Lunas</span>'
            : '<span class="px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 font-semibold text-[10px]">⏳ Belum Bayar</span>';

        const variantBadge = o.variant 
            ? `<span class="bg-indigo-100 text-indigo-700 font-medium px-1.5 py-0.5 rounded text-[10px]">${o.variant}</span>` 
            : "";

        const notesText = o.notes ? `<p class="text-[11px] text-slate-500 mt-0.5 italic">"${o.notes}"</p>` : "";

        const cancelBtn = isSessionOpen 
            ? `<button onclick="window.cancelMyOrder(${o.id}, '${o.user_name}')" class="text-slate-400 hover:text-rose-600 transition ml-2 text-xs font-semibold" title="Batalkan pesanan">✕</button>`
            : "";

        item.innerHTML = `
            <div class="flex items-start gap-2.5">
                <span class="w-5 h-5 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center font-bold text-[10px] flex-shrink-0 mt-0.5">
                    ${index + 1}
                </span>
                <div>
                    <p class="font-bold text-slate-800 text-xs">${o.user_name} <span class="font-normal text-slate-500">• ${o.vendor}</span></p>
                    <p class="text-slate-700 font-medium">${o.item_name} ${variantBadge}</p>
                    ${notesText}
                </div>
            </div>
            <div class="text-right flex-shrink-0 flex items-center gap-2">
                <div>
                    <p class="font-semibold text-slate-900 text-xs">Rp ${o.price.toLocaleString("id-ID")}</p>
                    <div class="mt-1">${statusBadge}</div>
                </div>
                ${cancelBtn}
            </div>
        `;
        list.appendChild(item);
    });
}

window.cancelMyOrder = async function(orderId, userName) {
    if (!confirm(`Batalkan pesanan untuk "${userName}"?`)) return;
    try {
        const resp = await fetch(`/api/v1/orders/${orderId}`, {
            method: "DELETE"
        });
        if (resp.ok) {
            await loadOrders();
            showToast("Pesanan berhasil dibatalkan.", "success");
        } else {
            showToast("Gagal membatalkan pesanan.", "error");
        }
    } catch (err) {
        showToast("Terjadi kesalahan jaringan.", "error");
    }
};

function setupQuickNames() {
    document.querySelectorAll(".name-tag").forEach(btn => {
        btn.addEventListener("click", () => {
            document.getElementById("input-username").value = btn.innerText;
        });
    });
}

function setupEventListeners() {
    document.getElementById("select-vendor").addEventListener("change", handleVendorChange);
    document.getElementById("select-menu").addEventListener("change", handleMenuChange);

    const customPriceInput = document.getElementById("input-custom-price");
    if (customPriceInput) {
        customPriceInput.addEventListener("input", (e) => {
            const val = parseInt(e.target.value, 10) || 0;
            document.getElementById("price-display").innerText = `Rp ${val.toLocaleString("id-ID")}`;
        });
    }

    document.getElementById("order-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!currentSession || currentSession.status !== "OPEN") {
            showToast("Sesi pemesanan sudah ditutup atau tidak aktif!", "warning");
            return;
        }

        const username = document.getElementById("input-username").value.trim();
        if (!username) {
            showToast("Harap masukkan nama Anda!", "warning");
            document.getElementById("input-username").focus();
            return;
        }

        let vendor = document.getElementById("select-vendor").value;
        if (vendor === "__custom__") {
            vendor = document.getElementById("input-custom-vendor").value.trim();
            if (!vendor) {
                showToast("Harap isi nama tenant / vendor baru!", "warning");
                document.getElementById("input-custom-vendor").focus();
                return;
            }
        } else if (!vendor) {
            showToast("Harap pilih vendor!", "warning");
            return;
        }

        const menuSelect = document.getElementById("select-menu");
        let itemName = menuSelect.value;
        let price = 0;

        if (itemName === "__custom__") {
            itemName = document.getElementById("input-custom-menu").value.trim();
            if (!itemName) {
                showToast("Harap isi nama menu makanan!", "warning");
                document.getElementById("input-custom-menu").focus();
                return;
            }
            price = parseInt(document.getElementById("input-custom-price").value, 10) || 0;
        } else if (menuSelect.selectedIndex > 0) {
            const data = JSON.parse(menuSelect.options[menuSelect.selectedIndex].dataset.itemData || "{}");
            price = data.price || 0;
        } else {
            showToast("Harap pilih menu makanan!", "warning");
            return;
        }

        const selectedVariantRadio = document.querySelector('input[name="order-variant"]:checked');
        let variant = selectedVariantRadio ? selectedVariantRadio.value : "";
        if (variant === "__custom__") {
            variant = document.getElementById("input-custom-variant").value.trim();
        } else if (!selectedVariantRadio && !document.getElementById("custom-variant-wrapper").classList.contains("hidden")) {
            variant = document.getElementById("input-custom-variant").value.trim();
        }

        const notes = document.getElementById("input-notes").value.trim();

        const submitBtn = document.getElementById("btn-submit-order");
        submitBtn.disabled = true;
        submitBtn.innerText = "Mengirim...";

        try {
            const resp = await fetch(`/api/v1/sessions/${currentSession.id}/orders`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_name: username,
                    vendor: vendor,
                    item_name: itemName,
                    variant: variant,
                    notes: notes,
                    price: price
                })
            });

            if (!resp.ok) {
                const err = await resp.json();
                showToast(`Gagal: ${err.detail || "Gagal mengirim pesanan"}`, "error");
                return;
            }

            document.getElementById("input-notes").value = "";
            document.getElementById("input-custom-vendor").value = "";
            document.getElementById("input-custom-menu").value = "";
            document.getElementById("input-custom-price").value = "";
            document.getElementById("input-custom-variant").value = "";
            
            await loadOrders();
            showToast("Pesanan berhasil disimpan! Tidak ada list tertimpa.", "success");
        } catch (err) {
            showToast("Terjadi kesalahan jaringan.", "error");
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = "<span>🚀</span> Kirim Pesanan (Anti-Ketimpa)";
        }
    });
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
