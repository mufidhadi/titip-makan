let activeSessionId = null;

async function initCoordinator() {
    await checkActiveSession();
    setupEventListeners();
}

async function checkActiveSession() {
    try {
        const resp = await fetch("/api/v1/sessions/active");
        const session = await resp.json();

        if (session && session.status === "OPEN") {
            activeSessionId = session.id;
            document.getElementById("create-session-card").classList.add("hidden");
            document.getElementById("active-session-management").classList.remove("hidden");
            document.getElementById("coord-session-id").innerText = `Session #${session.id}`;
            document.getElementById("coord-session-title").innerText = session.title;
            document.getElementById("coord-session-info").innerText = `Koordinator: ${session.coordinator_name} • Batas: ${session.cutoff_at ? new Date(session.cutoff_at).toLocaleTimeString() : 'Tanpa Batas'}`;
            await loadSummary();
        } else {
            activeSessionId = null;
            document.getElementById("create-session-card").classList.remove("hidden");
            document.getElementById("active-session-management").classList.add("hidden");
        }
    } catch (err) {
        console.error("Gagal memeriksa sesi:", err);
    }
}

async function loadSummary() {
    if (!activeSessionId) return;

    try {
        const resp = await fetch(`/api/v1/sessions/${activeSessionId}/summary`);
        if (!resp.ok) return;
        const summary = await resp.json();

        // Update metrics
        document.getElementById("metric-orders").innerText = `${summary.total_orders} porsi`;
        document.getElementById("metric-amount").innerText = `Rp ${summary.total_amount.toLocaleString("id-ID")}`;
        document.getElementById("metric-paid").innerText = summary.total_paid_count;
        document.getElementById("metric-unpaid").innerText = summary.total_unpaid_count;

        // Render aggregated items for shopping
        renderAggregatedItems(summary.aggregated_items);

        // Render detailed orders & payment status
        renderOrdersTable(summary.orders);

        // Store recap text in window for copy button
        window.currentRecapText = summary.whatsapp_recap_text;

    } catch (err) {
        console.error("Gagal memuat rekap:", err);
    }
}

function renderAggregatedItems(items) {
    const container = document.getElementById("aggregated-items-container");
    container.innerHTML = "";

    if (!items || items.length === 0) {
        container.innerHTML = `<p class="text-xs text-slate-400 col-span-3 py-4 text-center">Belum ada item pesanan yang terkumpul.</p>`;
        return;
    }

    items.forEach(item => {
        const card = document.createElement("div");
        card.className = "p-3.5 rounded-xl border border-slate-200 bg-slate-50 flex flex-col justify-between";
        
        let notesHtml = "";
        if (item.notes_list && item.notes_list.length > 0) {
            notesHtml = `<div class="mt-2 pt-2 border-t border-slate-200 text-[11px] text-slate-500 space-y-0.5">
                ${item.notes_list.map(n => `<p class="italic">↳ ${n}</p>`).join("")}
            </div>`;
        }

        card.innerHTML = `
            <div>
                <div class="flex items-center justify-between">
                    <span class="text-[10px] font-bold uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-md">${item.vendor}</span>
                    <span class="text-sm font-extrabold text-slate-900 bg-white border border-slate-200 px-2 py-0.5 rounded-lg shadow-sm">${item.quantity}x</span>
                </div>
                <h4 class="font-bold text-slate-800 text-sm mt-2">${item.item_name}</h4>
                ${item.variant ? `<p class="text-xs text-slate-600 font-medium">Varian: <span class="text-indigo-600 font-semibold">${item.variant}</span></p>` : ''}
                ${notesHtml}
            </div>
            <div class="mt-3 text-right text-xs font-semibold text-slate-700">
                Subtotal: Rp ${item.subtotal.toLocaleString("id-ID")}
            </div>
        `;
        container.appendChild(card);
    });
}

function renderOrdersTable(orders) {
    const tbody = document.getElementById("coordinator-orders-table");
    tbody.innerHTML = "";

    if (!orders || orders.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-slate-400">Belum ada pesanan.</td></tr>`;
        return;
    }

    orders.forEach((o, idx) => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-50 transition";

        const paymentBadge = o.is_paid
            ? `<span class="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-semibold text-[10px]">✅ Lunas</span>`
            : `<span class="px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 font-semibold text-[10px]">⏳ Belum</span>`;

        tr.innerHTML = `
            <td class="py-2.5 px-3 font-semibold text-slate-500">${idx + 1}</td>
            <td class="py-2.5 px-3 font-bold text-slate-800">${o.user_name}</td>
            <td class="py-2.5 px-3">${o.item_name} <span class="text-[10px] text-slate-400">(${o.vendor})</span></td>
            <td class="py-2.5 px-3 text-slate-600">
                ${o.variant ? `<span class="font-medium text-indigo-600">${o.variant}</span>` : '-'}
                ${o.notes ? `<span class="block text-[11px] text-slate-400 italic">Note: ${o.notes}</span>` : ''}
            </td>
            <td class="py-2.5 px-3 font-semibold text-slate-800">Rp ${o.price.toLocaleString("id-ID")}</td>
            <td class="py-2.5 px-3">${paymentBadge}</td>
            <td class="py-2.5 px-3 text-right">
                <button onclick="togglePaymentStatus(${o.id}, ${!o.is_paid})" 
                    class="px-2 py-1 rounded-lg text-[11px] font-semibold border ${o.is_paid ? 'border-amber-300 text-amber-700 bg-amber-50 hover:bg-amber-100' : 'border-emerald-300 text-emerald-700 bg-emerald-50 hover:bg-emerald-100'} transition">
                    ${o.is_paid ? 'Set Belum' : 'Set Lunas'}
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function togglePaymentStatus(orderId, newStatus) {
    try {
        const resp = await fetch(`/api/v1/orders/${orderId}/payment`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ is_paid: newStatus })
        });
        if (resp.ok) {
            await loadSummary();
        }
    } catch (err) {
        alert("Gagal memperbarui status pembayaran.");
    }
}

function setupEventListeners() {
    document.getElementById("btn-refresh").addEventListener("click", loadSummary);

    // Create session form
    document.getElementById("create-session-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const title = document.getElementById("cs-title").value.trim();
        const coordinator = document.getElementById("cs-coordinator").value.trim();
        const vendorsStr = document.getElementById("cs-vendors").value.trim();
        const cutoff = parseInt(document.getElementById("cs-cutoff").value, 10);
        const payment = document.getElementById("cs-payment").value.trim();

        const vendors = vendorsStr.split(",").map(v => v.trim()).filter(Boolean);

        try {
            const resp = await fetch("/api/v1/sessions", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    title: title,
                    coordinator_name: coordinator,
                    vendor_options: vendors,
                    cutoff_minutes: cutoff,
                    payment_info: payment
                })
            });

            if (!resp.ok) {
                alert("Gagal membuat sesi.");
                return;
            }

            alert("✅ Sesi titip makan berhasil dibuat!");
            await checkActiveSession();
        } catch (err) {
            alert("Terjadi kesalahan jaringan.");
        }
    });

    // Copy WA recap text
    document.getElementById("btn-copy-wa").addEventListener("click", async () => {
        if (!window.currentRecapText) {
            alert("Belum ada teks rekap.");
            return;
        }
        await navigator.clipboard.writeText(window.currentRecapText);
        alert("📋 Teks rekap WhatsApp berhasil disalin ke clipboard! Tinggal paste di grup MTN CORE.");
    });

    // Copy link order
    document.getElementById("btn-copy-link").addEventListener("click", async () => {
        const url = window.location.origin + "/";
        await navigator.clipboard.writeText(url);
        alert("🔗 Link order berhasil disalin: " + url);
    });

    // Close session
    document.getElementById("btn-close-session").addEventListener("click", async () => {
        const pin = prompt("Masukkan PIN Koordinator untuk menutup sesi:", "1234");
        if (!pin) return;

        try {
            const resp = await fetch(`/api/v1/sessions/${activeSessionId}/close`, {
                method: "POST",
                headers: { "X-Coordinator-Pin": pin }
            });

            if (!resp.ok) {
                alert("PIN salah atau sesi gagal ditutup.");
                return;
            }

            alert("🔒 Sesi berhasil ditutup. Rekap akhir siap dikirim!");
            await checkActiveSession();
        } catch (err) {
            alert("Gagal menutup sesi.");
        }
    });
}

document.addEventListener("DOMContentLoaded", initCoordinator);
