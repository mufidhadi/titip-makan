async function initLeaderboard() {
    document.getElementById("btn-refresh-leaderboard").addEventListener("click", async () => {
        await loadLeaderboard();
        showToast("Leaderboard diperbarui.", "info");
    });
    await loadLeaderboard();
}

async function loadLeaderboard() {
    try {
        const resp = await fetch("/api/v1/analytics/leaderboard");
        if (!resp.ok) return;
        const data = await resp.json();

        renderBadges(data.badges_summary);
        renderRankings(data.rankings);
    } catch (err) {
        console.error("Gagal memuat leaderboard:", err);
    }
}

function renderBadges(badges) {
    const container = document.getElementById("badges-grid");
    container.innerHTML = "";

    if (!badges || badges.length === 0) {
        container.innerHTML = `<p class="col-span-full text-center text-slate-400 py-6 text-xs">Belum ada badge yang diraih.</p>`;
        return;
    }

    const badgeColors = {
        sultan: "from-amber-500/10 to-yellow-500/20 border-amber-300 text-amber-900",
        rajin: "from-indigo-500/10 to-blue-500/20 border-indigo-300 text-indigo-900",
        catatan: "from-pink-500/10 to-rose-500/20 border-pink-300 text-pink-900",
        ninja: "from-slate-700/10 to-slate-900/20 border-slate-400 text-slate-900",
        setia: "from-stone-500/10 to-stone-700/20 border-stone-300 text-stone-900",
        eksplorator: "from-emerald-500/10 to-teal-500/20 border-emerald-300 text-emerald-900",
    };

    badges.forEach(b => {
        const card = document.createElement("div");
        const colorClass = badgeColors[b.code] || "from-slate-100 to-slate-200 border-slate-300 text-slate-800";
        card.className = `p-4 rounded-2xl border bg-gradient-to-br ${colorClass} shadow-sm flex flex-col justify-between transition hover:shadow-md hover:-translate-y-0.5`;

        const holderHtml = b.holder
            ? `<div class="mt-2 flex items-center justify-between">
                 <span class="font-extrabold text-sm sm:text-base">${b.holder}</span>
                 <span class="text-xs font-bold px-2 py-0.5 rounded-lg bg-white/80 shadow-sm">${b.metric_value || ''}</span>
               </div>`
            : `<div class="mt-2 text-xs italic opacity-60">Belum ada pemenang</div>`;

        card.innerHTML = `
            <div>
                <div class="flex items-center gap-2">
                    <span class="text-2xl">${b.icon}</span>
                    <div>
                        <h4 class="font-extrabold text-xs uppercase tracking-wider">${b.title}</h4>
                    </div>
                </div>
                ${holderHtml}
            </div>
            <p class="text-[11px] mt-2.5 opacity-75 leading-tight">${b.description}</p>
        `;
        container.appendChild(card);
    });
}

function renderRankings(rankings) {
    const tbody = document.getElementById("leaderboard-tbody");
    tbody.innerHTML = "";

    if (!rankings || rankings.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-400">Belum ada data pesanan anggota.</td></tr>`;
        return;
    }

    rankings.forEach(r => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-50 transition";

        let rankBadge = `<span class="font-bold text-slate-500">#${r.rank}</span>`;
        if (r.rank === 1) rankBadge = `<span class="text-xl">🥇</span>`;
        else if (r.rank === 2) rankBadge = `<span class="text-xl">🥈</span>`;
        else if (r.rank === 3) rankBadge = `<span class="text-xl">🥉</span>`;

        let badgesChips = "-";
        if (r.badges && r.badges.length > 0) {
            badgesChips = r.badges.map(b => `<span class="inline-block text-[10px] font-bold px-2 py-0.5 rounded-md bg-amber-100 text-amber-800 mr-1 mb-0.5 shadow-xs">${b}</span>`).join("");
        }

        tr.innerHTML = `
            <td class="py-3 px-3 text-center">${rankBadge}</td>
            <td class="py-3 px-3 font-bold text-slate-900">${r.user_name}</td>
            <td class="py-3 px-3">${badgesChips}</td>
            <td class="py-3 px-3 text-right font-extrabold text-slate-900">Rp ${r.total_spend.toLocaleString("id-ID")}</td>
            <td class="py-3 px-3 text-center font-semibold text-indigo-600">${r.order_count}</td>
            <td class="py-3 px-3 text-center text-slate-600">${r.custom_notes_count > 0 ? `✍️ ${r.custom_notes_count}` : '-'}</td>
            <td class="py-3 px-3 text-center text-slate-600">${r.unique_menus_count}</td>
        `;
        tbody.appendChild(tr);
    });
}

document.addEventListener("DOMContentLoaded", initLeaderboard);
