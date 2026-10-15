// Weekday auto random order: each user keeps a list of menus; the server picks one at random
// for every Monday-Friday session. Uses getSavedUsername/saveUsername from app.js.
(() => {
    const $ = (id) => document.getElementById(id);
    let suggestions = { tenants: [], menus: {}, prices: {} };
    let candidates = [];

    function fillDatalist(el, values) {
        el.replaceChildren(...values.map((v) => Object.assign(document.createElement("option"), { value: v })));
    }

    function refreshMenuDatalist() {
        const menus = suggestions.menus[$("auto-order-tenant").value.trim()] || Object.values(suggestions.menus).flat();
        fillDatalist($("auto-order-menus"), [...new Set(menus)].sort());
    }

    function setStatus(text, ok = true) {
        const el = $("auto-order-status");
        el.textContent = text;
        el.className = `text-xs ${ok ? "text-emerald-700" : "text-rose-600"}`;
    }

    function setBadge(enabled) {
        const badge = $("auto-order-badge");
        badge.textContent = enabled ? "Aktif" : "Nonaktif";
        badge.className = `px-2 py-0.5 rounded-full text-[11px] font-bold flex-shrink-0 ${enabled ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"}`;
    }

    function renderCandidates() {
        const list = $("auto-order-candidates");
        if (!candidates.length) {
            const empty = document.createElement("li");
            empty.className = "text-[11px] text-slate-400";
            empty.textContent = "Belum ada menu. Tambahkan minimal satu menu untuk diacak.";
            list.replaceChildren(empty);
            return;
        }
        list.replaceChildren(...candidates.map((c, i) => {
            const li = document.createElement("li");
            li.className = "flex items-center justify-between gap-2 px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs";
            const label = document.createElement("span");
            label.className = "min-w-0 truncate text-slate-700";
            label.textContent = `${c.item_name} · ${c.vendor}${c.price ? ` · Rp ${c.price.toLocaleString("id-ID")}` : ""}`;
            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "text-rose-600 hover:text-rose-700 font-bold px-1.5 flex-shrink-0";
            remove.textContent = "✕";
            remove.setAttribute("aria-label", `Hapus ${c.item_name}`);
            remove.addEventListener("click", () => {
                candidates.splice(i, 1);
                renderCandidates();
            });
            li.append(label, remove);
            return li;
        }));
    }

    async function loadPreference() {
        const name = $("auto-order-username").value.trim();
        if (!name) return setStatus("Isi nama dulu.", false);
        try {
            const resp = await fetch(`/api/v1/auto-order?user_name=${encodeURIComponent(name)}`);
            if (!resp.ok) throw new Error(resp.status);
            const data = await resp.json();
            candidates = data.candidates;
            $("auto-order-enabled").checked = data.enabled;
            setBadge(data.enabled);
            renderCandidates();
            setStatus("");
        } catch (err) {
            console.error("Gagal memuat auto pesan:", err);
            setStatus("Gagal memuat pengaturan.", false);
        }
    }

    function addCandidate() {
        const vendor = $("auto-order-tenant").value.trim();
        const itemName = $("auto-order-menu").value.trim();
        if (!vendor || !itemName) return setStatus("Isi tenant dan menu dulu.", false);
        if (candidates.some((c) => c.vendor === vendor && c.item_name === itemName)) {
            return setStatus("Menu sudah ada di daftar.", false);
        }
        candidates.push({ vendor, item_name: itemName, price: suggestions.prices[itemName] || 0 });
        $("auto-order-menu").value = "";
        renderCandidates();
        setStatus("");
    }

    async function savePreference() {
        const name = $("auto-order-username").value.trim();
        const enabled = $("auto-order-enabled").checked;
        if (!name) return setStatus("Isi nama dulu.", false);
        if (enabled && !candidates.length) return setStatus("Tambahkan minimal satu menu.", false);
        try {
            const resp = await fetch("/api/v1/auto-order", {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_name: name, enabled, candidates }),
            });
            const data = await resp.json();
            if (!resp.ok) {
                const detail = Array.isArray(data.detail) ? data.detail[0].msg.replace(/^Value error, /, "") : data.detail;
                return setStatus(detail || "Gagal menyimpan.", false);
            }
            saveUsername(data.user_name);
            setBadge(data.enabled);
            setStatus(data.enabled ? "Tersimpan. Auto pesan aktif Senin–Jumat." : "Tersimpan. Auto pesan nonaktif.");
        } catch (err) {
            console.error("Gagal menyimpan auto pesan:", err);
            setStatus("Gagal menyimpan.", false);
        }
    }

    async function init() {
        if (!$("auto-order-card")) return;
        $("auto-order-tenant").addEventListener("input", refreshMenuDatalist);
        $("auto-order-load").addEventListener("click", loadPreference);
        $("auto-order-add").addEventListener("click", addCandidate);
        $("auto-order-save").addEventListener("click", savePreference);
        renderCandidates();

        try {
            const resp = await fetch("/api/v1/sessions/suggestions");
            if (resp.ok) suggestions = await resp.json();
            fillDatalist($("auto-order-tenants"), suggestions.tenants);
            refreshMenuDatalist();
        } catch (err) {
            console.error("Gagal memuat saran menu:", err);
        }

        const savedName = getSavedUsername();
        if (savedName) {
            $("auto-order-username").value = savedName;
            await loadPreference();
        }
    }

    document.addEventListener("DOMContentLoaded", init);
})();
