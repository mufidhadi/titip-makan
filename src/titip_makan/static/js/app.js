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

async function initApp() {
    setupQuickNames();
    await fetchActiveSession();
    setupEventListeners();
}

async function fetchActiveSession() {
    try {
        const resp = await fetch("/api/v1/sessions/active");
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

        populateVendors(data.vendor_options);
        startCountdown(data.cutoff_at);
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
}

function handleVendorChange() {
    const vendor = document.getElementById("select-vendor").value;
    const menuSelect = document.getElementById("select-menu");
    menuSelect.innerHTML = '<option value="">-- Pilih Menu --</option>';
    document.getElementById("variant-options").innerHTML = "";
    document.getElementById("price-display").innerText = "Rp 0";

    const items = MENU_CATALOG[vendor] || [
        { name: `${vendor} Standar`, variants: ["Biasa", "Spesial"], price: 15000 }
    ];

    items.forEach(item => {
        const opt = document.createElement("option");
        opt.value = item.name;
        opt.innerText = `${item.name} (~Rp ${item.price.toLocaleString("id-ID")})`;
        opt.dataset.itemData = JSON.stringify(item);
        menuSelect.appendChild(opt);
    });
}

function handleMenuChange() {
    const menuSelect = document.getElementById("select-menu");
    const selectedOption = menuSelect.options[menuSelect.selectedIndex];
    const container = document.getElementById("variant-options");
    container.innerHTML = "";

    if (!selectedOption || !selectedOption.dataset.itemData) return;

    const item = JSON.parse(selectedOption.dataset.itemData);
    document.getElementById("price-display").innerText = `Rp ${item.price.toLocaleString("id-ID")}`;

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
            <div class="text-right flex-shrink-0">
                <p class="font-semibold text-slate-900 text-xs">Rp ${o.price.toLocaleString("id-ID")}</p>
                <div class="mt-1">${statusBadge}</div>
            </div>
        `;
        list.appendChild(item);
    });
}

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

    document.getElementById("order-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!currentSession) {
            alert("Sesi tidak aktif!");
            return;
        }

        const username = document.getElementById("input-username").value.trim();
        const vendor = document.getElementById("select-vendor").value;
        const menuSelect = document.getElementById("select-menu");
        const itemName = menuSelect.value;
        const selectedVariantRadio = document.querySelector('input[name="order-variant"]:checked');
        const variant = selectedVariantRadio ? selectedVariantRadio.value : "";
        const notes = document.getElementById("input-notes").value.trim();

        let price = 0;
        if (menuSelect.selectedIndex > 0) {
            const data = JSON.parse(menuSelect.options[menuSelect.selectedIndex].dataset.itemData || "{}");
            price = data.price || 0;
        }

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
                alert(`Gagal: ${err.detail || "Gagal mengirim pesanan"}`);
                return;
            }

            document.getElementById("input-notes").value = "";
            await loadOrders();
            alert("✅ Pesanan berhasil disimpan! Tidak ada list yang tertimpa.");
        } catch (err) {
            alert("Terjadi kesalahan jaringan.");
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = "<span>🚀</span> Kirim Pesanan (Anti-Ketimpa)";
        }
    });
}

function startCountdown(cutoffIsoString) {
    const timerElem = document.getElementById("countdown-timer");
    if (!cutoffIsoString) {
        timerElem.innerText = "Tanpa Batas";
        return;
    }

    const cutoffTime = new Date(cutoffIsoString).getTime();

    function update() {
        const now = new Date().getTime();
        const diff = cutoffTime - now;

        if (diff <= 0) {
            timerElem.innerText = "DITUTUP";
            timerElem.classList.add("text-rose-600");
            return;
        }

        const minutes = Math.floor(diff / 60000);
        const seconds = Math.floor((diff % 60000) / 1000);
        timerElem.innerText = `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
    }

    update();
    setInterval(update, 1000);
}

document.addEventListener("DOMContentLoaded", initApp);
