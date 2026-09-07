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
        
        // Auto setup custom menu
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

    // Option for custom menu under existing vendor
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

    // Always add an option for Custom Variant
    const customVarLabel = document.createElement("label");
    customVarLabel.className = "flex items-center gap-2 p-2 rounded-lg border border-indigo-200 bg-indigo-50/30 hover:bg-indigo-50/60 cursor-pointer text-xs col-span-2";
    customVarLabel.innerHTML = `
        <input type="radio" name="order-variant" value="__custom__" class="text-indigo-600 focus:ring-indigo-500">
        <span class="font-semibold text-indigo-700">➕ Varian Kustom Lainnya</span>
    `;
    container.appendChild(customVarLabel);

    // Event listener for variant radios
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
        if (!currentSession) {
            alert("Sesi tidak aktif!");
            return;
        }

        const username = document.getElementById("input-username").value.trim();
        if (!username) {
            alert("Harap masukkan nama Anda!");
            document.getElementById("input-username").focus();
            return;
        }

        let vendor = document.getElementById("select-vendor").value;
        if (vendor === "__custom__") {
            vendor = document.getElementById("input-custom-vendor").value.trim();
            if (!vendor) {
                alert("Harap isi nama tenant / vendor baru!");
                document.getElementById("input-custom-vendor").focus();
                return;
            }
        } else if (!vendor) {
            alert("Harap pilih vendor!");
            return;
        }

        const menuSelect = document.getElementById("select-menu");
        let itemName = menuSelect.value;
        let price = 0;

        if (itemName === "__custom__") {
            itemName = document.getElementById("input-custom-menu").value.trim();
            if (!itemName) {
                alert("Harap isi nama menu makanan!");
                document.getElementById("input-custom-menu").focus();
                return;
            }
            price = parseInt(document.getElementById("input-custom-price").value, 10) || 0;
        } else if (menuSelect.selectedIndex > 0) {
            const data = JSON.parse(menuSelect.options[menuSelect.selectedIndex].dataset.itemData || "{}");
            price = data.price || 0;
        } else {
            alert("Harap pilih menu makanan!");
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
                alert(`Gagal: ${err.detail || "Gagal mengirim pesanan"}`);
                return;
            }

            document.getElementById("input-notes").value = "";
            document.getElementById("input-custom-vendor").value = "";
            document.getElementById("input-custom-menu").value = "";
            document.getElementById("input-custom-price").value = "";
            document.getElementById("input-custom-variant").value = "";
            
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
