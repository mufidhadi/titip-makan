let activeSessionId = null;
let pollTimer = null;

async function initCoordinator() {
    await checkActiveSession();
    setupEventListeners();

    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(async () => {
        if (activeSessionId) {
            await loadSummary();
        }
    }, 5000);
}

function parseUtcDate(dateStr) {
    if (!dateStr) return null;
    if (!dateStr.endsWith("Z") && !dateStr.includes("+")) {
        dateStr += "Z";
    }
    return new Date(dateStr);
}

async function checkActiveSession() {
    try {
        const resp = await fetch("/api/v1/sessions/latest");
        const session = await resp.json();

        if (session) {
            activeSessionId = session.id;
            document.getElementById("create-session-card").classList.add("hidden");
            document.getElementById("active-session-management").classList.remove("hidden");
            document.getElementById("coord-session-id").innerText = `Session #${session.id}`;
            document.getElementById("coord-session-title").innerText = session.title;
            
            const cutoffDate = parseUtcDate(session.cutoff_at);
            const cutoffText = cutoffDate ? cutoffDate.toLocaleTimeString("id-ID", { hour: '2-digit', minute: '2-digit' }) : 'Tanpa Batas';
            document.getElementById("coord-session-info").innerText = `Koordinator: ${session.coordinator_name} • Batas Waktu: ${cutoffText}`;

            const badge = document.getElementById("coord-status-badge");
            const closeBtn = document.getElementById("btn-close-session");
            const closeCutoffBtn = document.getElementById("btn-close-cutoff-now");
            const noticeBanner = document.getElementById("coord-closed-notice");
            const cutoffLabel = document.getElementById("cutoff-label-text");
            const extend5Btn = document.getElementById("btn-extend-5");
            const extend10Btn = document.getElementById("btn-extend-10");

            window.previousSessionStatus = window.currentSessionStatus;
            window.currentSessionStatus = session.status;

            if (session.status === "CLOSED") {
                badge.className = "px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40";
                badge.innerText = "SESI SUDAH DITUTUP (SELESAI)";
                if (closeBtn) closeBtn.classList.add("hidden");
                if (closeCutoffBtn) closeCutoffBtn.classList.add("hidden");
                if (noticeBanner) noticeBanner.classList.remove("hidden");
                if (cutoffLabel) cutoffLabel.innerText = "⏱️ Buka Sementara:";
                if (extend5Btn) {
                    extend5Btn.className = "px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white rounded-lg text-xs font-bold transition shadow-xs flex items-center gap-1";
                    extend5Btn.innerHTML = "<span>🔓</span> +5m";
                    extend5Btn.title = "Buka sesi sementara selama 5 menit";
                }
                if (extend10Btn) {
                    extend10Btn.className = "px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white rounded-lg text-xs font-bold transition shadow-xs flex items-center gap-1";
                    extend10Btn.innerHTML = "<span>🔓</span> +10m";
                    extend10Btn.title = "Buka sesi sementara selama 10 menit";
                }
            } else {
                badge.className = "px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40";
                badge.innerText = "SESI SEDANG BERLANGSUNG";
                if (closeBtn) closeBtn.classList.remove("hidden");
                if (closeCutoffBtn) closeCutoffBtn.classList.remove("hidden");
                if (noticeBanner) noticeBanner.classList.add("hidden");
                if (cutoffLabel) cutoffLabel.innerText = "⏱️ Waktu:";
                if (extend5Btn) {
                    extend5Btn.className = "px-2 py-1 bg-indigo-700 hover:bg-indigo-600 active:bg-indigo-800 text-white rounded-lg text-xs font-bold transition shadow-xs";
                    extend5Btn.innerText = "+5m";
                    extend5Btn.title = "Tambah 5 menit";
                }
                if (extend10Btn) {
                    extend10Btn.className = "px-2 py-1 bg-indigo-700 hover:bg-indigo-600 active:bg-indigo-800 text-white rounded-lg text-xs font-bold transition shadow-xs";
                    extend10Btn.innerText = "+10m";
                    extend10Btn.title = "Tambah 10 menit";
                }
            }

            window.coordinatorPhone = session.coordinator_phone || "+62 815-1382-5480";
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

        // Populate hover popover for unpaid orders
        const popoverList = document.getElementById("unpaid-popover-list");
        const popoverCount = document.getElementById("unpaid-popover-count");
        if (popoverList && summary.unpaid_orders_users) {
            popoverCount.innerText = `${summary.unpaid_orders_users.length} item`;
            if (summary.unpaid_orders_users.length === 0) {
                popoverList.innerHTML = `<p class="text-slate-400 py-1 text-center">Semua sudah lunas! 🎉</p>`;
            } else {
                popoverList.innerHTML = summary.unpaid_orders_users.map(u => `
                    <div class="flex items-center justify-between py-1.5 text-slate-200">
                        <div>
                            <span class="font-bold text-slate-100">${u.user_name}</span>
                            <span class="text-[10px] text-slate-400 block">${u.item_name} (${u.vendor})</span>
                        </div>
                        <span class="text-amber-300 font-bold whitespace-nowrap ml-2">Rp ${u.price.toLocaleString("id-ID")}</span>
                    </div>
                `).join("");
            }
        }

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

        const paymentStatus = o.payment_status || (o.is_paid ? "PAID" : "UNPAID");
        let paymentBadge = "";
        let actionBtn = "";

        if (paymentStatus === "PAID" || o.is_paid) {
            paymentBadge = `<span class="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-semibold text-[10px]">✅ Lunas</span>`;
            actionBtn = `<button onclick="window.togglePaymentStatus(${o.id}, false, 'UNPAID')" 
                class="px-2 py-1 rounded-lg text-[11px] font-semibold border border-amber-300 text-amber-700 bg-amber-50 hover:bg-amber-100 transition">
                Set Belum
            </button>`;
        } else if (paymentStatus === "PENDING_CONFIRMATION") {
            paymentBadge = `<span class="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-bold text-[10px] animate-pulse">🟡 Menunggu Konfirmasi</span>`;
            actionBtn = `<button onclick="window.confirmPayment(${o.id})" 
                class="px-2.5 py-1 rounded-lg text-[11px] font-bold bg-emerald-600 hover:bg-emerald-700 text-white transition shadow-sm">
                ✅ Konfirmasi Lunas
            </button>`;
        } else {
            paymentBadge = `<span class="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-semibold text-[10px]">⏳ Belum Bayar</span>`;
            actionBtn = `<button onclick="window.confirmPayment(${o.id})" 
                class="px-2 py-1 rounded-lg text-[11px] font-semibold border border-emerald-300 text-emerald-700 bg-emerald-50 hover:bg-emerald-100 transition">
                Set Lunas
            </button>`;
        }

        const priceCell = o.price > 0
            ? `<span class="font-semibold text-slate-800">Rp ${o.price.toLocaleString("id-ID")}</span>
               <button onclick="window.promptEditPrice(${o.id}, ${o.price}, '${escapeJs(o.item_name)}')" class="text-slate-400 hover:text-indigo-600 ml-1 text-[10px]" title="Ubah harga">✏️</button>`
            : `<span class="px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 text-[10px] font-bold border border-amber-200">Belum di-set</span>
               <button onclick="window.promptEditPrice(${o.id}, 0, '${escapeJs(o.item_name)}')" class="text-indigo-600 hover:text-indigo-800 text-[11px] font-bold underline ml-1">✏️ Set</button>`;

        tr.innerHTML = `
            <td class="py-2.5 px-3 font-semibold text-slate-500">${idx + 1}</td>
            <td class="py-2.5 px-3 font-bold text-slate-800">${o.user_name}</td>
            <td class="py-2.5 px-3">${o.item_name} <span class="text-[10px] text-slate-400">(${o.vendor})</span></td>
            <td class="py-2.5 px-3 text-slate-600">
                ${o.notes ? `<span class="block text-[11px] text-slate-600 italic">"${o.notes}"</span>` : '-'}
            </td>
            <td class="py-2.5 px-3">${priceCell}</td>
            <td class="py-2.5 px-3">${paymentBadge}</td>
            <td class="py-2.5 px-3 text-right space-x-1">
                ${actionBtn}
                <button onclick="window.deleteOrder(${o.id}, '${escapeJs(o.user_name)}')" 
                    class="px-2 py-1 rounded-lg text-[11px] font-semibold border border-rose-200 text-rose-600 bg-rose-50 hover:bg-rose-100 transition">
                    🗑️
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function escapeJs(str) {
    if (!str) return "";
    return str.replace(/'/g, "\\'");
}

window.promptEditPrice = async function(orderId, currentPrice, itemName) {
    const promptVal = prompt(`Masukkan harga untuk "${itemName}":`, currentPrice > 0 ? currentPrice : "");
    if (promptVal === null) return;
    const price = parseInt(promptVal.trim(), 10);
    if (isNaN(price) || price < 0) {
        showToast("Harga harus berupa nominal angka valid!", "warning");
        return;
    }

    try {
        const resp = await fetch(`/api/v1/orders/${orderId}/price`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ price: price })
        });
        if (resp.ok) {
            await loadSummary();
            showToast("Harga pesanan berhasil diperbarui!", "success");
        } else {
            showToast("Gagal memperbarui harga.", "error");
        }
    } catch (err) {
        showToast("Terjadi kesalahan jaringan.", "error");
    }
};

window.confirmPayment = async function(orderId) {
    try {
        const resp = await fetch(`/api/v1/orders/${orderId}/payment`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ is_paid: true, payment_status: "PAID" })
        });
        if (resp.ok) {
            await loadSummary();
            showToast("Pembayaran dikonfirmasi Lunas! ✅", "success");
        } else {
            showToast("Gagal mengonfirmasi pembayaran.", "error");
        }
    } catch (err) {
        showToast("Terjadi kesalahan jaringan.", "error");
    }
};

window.togglePaymentStatus = async function(orderId, newStatus, paymentStatus) {
    try {
        const resp = await fetch(`/api/v1/orders/${orderId}/payment`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                is_paid: newStatus,
                payment_status: paymentStatus || (newStatus ? "PAID" : "UNPAID")
            })
        });
        if (resp.ok) {
            await loadSummary();
        }
    } catch (err) {
        showToast("Gagal memperbarui status pembayaran.", "error");
    }
};

window.deleteOrder = async function(orderId, userName) {
    if (!confirm(`Hapus pesanan dari "${userName}"?`)) return;
    try {
        const resp = await fetch(`/api/v1/orders/${orderId}`, {
            method: "DELETE"
        });
        if (resp.ok) {
            await loadSummary();
            showToast("Pesanan berhasil dihapus.", "success");
        } else {
            showToast("Gagal menghapus pesanan.", "error");
        }
    } catch (err) {
        showToast("Terjadi kesalahan saat menghapus pesanan.", "error");
    }
};

function setupEventListeners() {
    document.getElementById("btn-refresh").addEventListener("click", () => {
        loadSummary();
        showToast("Data diperbarui.", "info");
    });

    const newSessionBtn = document.getElementById("btn-new-session-toggle");
    if (newSessionBtn) {
        newSessionBtn.addEventListener("click", () => {
            const card = document.getElementById("create-session-card");
            card.classList.toggle("hidden");
            if (!card.classList.contains("hidden")) {
                card.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }

    const wheelOpenTenantBtn = document.getElementById("wheel-open-tenant");
    if (wheelOpenTenantBtn) {
        wheelOpenTenantBtn.addEventListener("click", () => {
            window.MenuWheel.open({
                mode: "tenant",
                onApply: (candidate) => {
                    document.getElementById("cs-vendors").value = candidate.label;
                }
            });
        });
    }

    // Create session form
    document.getElementById("create-session-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const title = document.getElementById("cs-title").value.trim();
        const coordinator = document.getElementById("cs-coordinator").value.trim();
        const vendorsStr = document.getElementById("cs-vendors").value.trim();
        const cutoff = parseInt(document.getElementById("cs-cutoff").value, 10);
        const payment = document.getElementById("cs-payment").value.trim();
        const phoneInput = document.getElementById("cs-phone");
        const phone = phoneInput ? phoneInput.value.trim() : "";

        const vendors = vendorsStr.split(",").map(v => v.trim()).filter(Boolean);

        try {
            const resp = await fetch("/api/v1/sessions", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    title: title,
                    coordinator_name: coordinator,
                    coordinator_phone: phone,
                    vendor_options: vendors,
                    cutoff_minutes: cutoff,
                    payment_info: payment
                })
            });

            if (!resp.ok) {
                showToast("Gagal membuat sesi.", "error");
                return;
            }

            showToast("Sesi titip makan berhasil dibuat!", "success");
            await checkActiveSession();
        } catch (err) {
            showToast("Terjadi kesalahan jaringan.", "error");
        }
    });

    // Cutoff controls
    const btnExtend5 = document.getElementById("btn-extend-5");
    if (btnExtend5) {
        btnExtend5.addEventListener("click", () => updateCutoff(5, false));
    }
    const btnExtend10 = document.getElementById("btn-extend-10");
    if (btnExtend10) {
        btnExtend10.addEventListener("click", () => updateCutoff(10, false));
    }
    const btnNoticeExtend5 = document.getElementById("btn-notice-extend-5");
    if (btnNoticeExtend5) {
        btnNoticeExtend5.addEventListener("click", () => updateCutoff(5, false));
    }
    const btnNoticeExtend10 = document.getElementById("btn-notice-extend-10");
    if (btnNoticeExtend10) {
        btnNoticeExtend10.addEventListener("click", () => updateCutoff(10, false));
    }
    const btnCloseCutoffNow = document.getElementById("btn-close-cutoff-now");
    if (btnCloseCutoffNow) {
        btnCloseCutoffNow.addEventListener("click", () => {
            if (confirm("Tutup batas waktu order sesi sekarang? Anggota tidak akan bisa memesan lagi.")) {
                updateCutoff(0, true);
            }
        });
    }

    async function updateCutoff(extendMinutes, closeNow) {
        if (!activeSessionId) return;
        let pin = localStorage.getItem("titip_makan_coordinator_pin") || "1234";
        try {
            let resp = await fetch(`/api/v1/sessions/${activeSessionId}/cutoff`, {
                method: "PATCH",
                headers: { 
                    "Content-Type": "application/json",
                    "X-Coordinator-Pin": pin
                },
                body: JSON.stringify({
                    extend_minutes: extendMinutes || null,
                    close_now: closeNow || false
                })
            });

            if (resp.status === 403) {
                const promptedPin = prompt("Masukkan PIN Koordinator:", "1234");
                if (!promptedPin) return;
                pin = promptedPin;
                localStorage.setItem("titip_makan_coordinator_pin", pin);
                resp = await fetch(`/api/v1/sessions/${activeSessionId}/cutoff`, {
                    method: "PATCH",
                    headers: { 
                        "Content-Type": "application/json",
                        "X-Coordinator-Pin": pin
                    },
                    body: JSON.stringify({
                        extend_minutes: extendMinutes || null,
                        close_now: closeNow || false
                    })
                });
            }

            if (resp.ok) {
                const updatedSession = await resp.json();
                if (closeNow) {
                    showToast("Batas waktu pemesanan ditutup sekarang!", "success");
                } else if (window.previousSessionStatus === "CLOSED" && updatedSession.status === "OPEN") {
                    showToast(`Sesi berhasil dibuka kembali sementara selama ${extendMinutes} menit! 🎉`, "success");
                } else {
                    showToast(`Waktu sesi diperpanjang +${extendMinutes} menit!`, "success");
                }
                await checkActiveSession();
            } else {
                showToast("Gagal mengubah batas waktu sesi.", "error");
            }
        } catch (e) {
            showToast("Terjadi kesalahan jaringan.", "error");
        }
    }

    // Send recap directly to coordinator WhatsApp
    const btnSendWaCoord = document.getElementById("btn-send-wa-coord");
    if (btnSendWaCoord) {
        btnSendWaCoord.addEventListener("click", () => {
            if (!window.currentRecapText) {
                showToast("Belum ada teks rekap.", "warning");
                return;
            }
            let phone = window.coordinatorPhone || "+62 815-1382-5480";
            phone = phone.replace(/[^0-9]/g, "");
            if (phone.startsWith("0")) phone = "62" + phone.slice(1);
            const waUrl = `https://wa.me/${phone}?text=${encodeURIComponent(window.currentRecapText)}`;
            window.open(waUrl, "_blank");
        });
    }

    // Copy WA recap text
    document.getElementById("btn-copy-wa").addEventListener("click", async () => {
        if (!window.currentRecapText) {
            showToast("Belum ada teks rekap.", "warning");
            return;
        }
        await navigator.clipboard.writeText(window.currentRecapText);
        showToast("Teks rekap WhatsApp disalin ke clipboard!", "success");
    });

    // Copy link order
    document.getElementById("btn-copy-link").addEventListener("click", async () => {
        const url = window.location.origin + "/";
        await navigator.clipboard.writeText(url);
        showToast("Link order disalin: " + url, "info");
    });

    // Broadcast WA announcement to MTN CORE group
    const broadcastBtn = document.getElementById("btn-broadcast-wa");
    if (broadcastBtn) {
        broadcastBtn.addEventListener("click", async () => {
            if (!activeSessionId) {
                showToast("Tidak ada sesi aktif.", "warning");
                return;
            }
            const confirmBroadcast = confirm("Kirim ulang pengumuman sesi ke Grup WhatsApp MTN CORE?");
            if (!confirmBroadcast) return;

            const pin = prompt("Masukkan PIN Koordinator:", "1234");
            if (!pin) return;

            broadcastBtn.disabled = true;
            broadcastBtn.innerText = "Mengirim...";

            try {
                const resp = await fetch(`/api/v1/sessions/${activeSessionId}/broadcast`, {
                    method: "POST",
                    headers: { "X-Coordinator-Pin": pin }
                });
                const data = await resp.json();
                if (resp.ok && data.status === "success") {
                    showToast("Pengumuman berhasil dikirim ke Grup MTN CORE!", "success");
                } else if (data.status === "skipped") {
                    showToast("Notifikasi WA dilewati (" + (data.reason || "dimatikan") + ").", "info");
                } else {
                    showToast("Gagal mengirim WA: " + (data.error || "Terjadi kesalahan"), "error");
                }
            } catch (err) {
                showToast("Gagal menghubungi server.", "error");
            } finally {
                broadcastBtn.disabled = false;
                broadcastBtn.innerHTML = '<span>📢</span> Kirim Ulang WA';
            }
        });
    }

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
                showToast("PIN salah atau sesi gagal ditutup.", "error");
                return;
            }

            showToast("Sesi berhasil ditutup. Rekap akhir tetap tersimpan!", "success");
            await checkActiveSession();
        } catch (err) {
            showToast("Gagal menutup sesi.", "error");
        }
    });
}

document.addEventListener("DOMContentLoaded", initCoordinator);
