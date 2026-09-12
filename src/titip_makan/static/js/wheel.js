(function () {
    const PALETTE = ["#4f46e5", "#7c3aed", "#059669", "#d97706", "#e11d48", "#0284c7"];
    const MAX_LABELED_SLICES = 16;
    const SPIN_DURATION_MS = 4000;

    let state = null;

    function qs(id) {
        return document.getElementById(id);
    }

    function secureRandomInt(maxExclusive) {
        if (maxExclusive <= 0) return 0;
        const range = 0x100000000;
        const limit = range - (range % maxExclusive);
        const buf = new Uint32Array(1);
        let x;
        do {
            crypto.getRandomValues(buf);
            x = buf[0];
        } while (x >= limit);
        return x % maxExclusive;
    }

    function normalizeMod360(deg) {
        return ((deg % 360) + 360) % 360;
    }

    function computeTargetRotation(currentRotationDeg, winnerIndex, sliceCount) {
        const sliceAngle = 360 / sliceCount;
        const sliceCenter = winnerIndex * sliceAngle + sliceAngle / 2;
        const currentModNorm = normalizeMod360(currentRotationDeg);
        const desiredMod = normalizeMod360(360 - sliceCenter);
        let delta = desiredMod - currentModNorm;
        if (delta < 0) delta += 360;
        return currentRotationDeg + 5 * 360 + delta;
    }

    function prefersReducedMotion() {
        return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    function debounce(fn, delay) {
        let timer = null;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    function resetState(mode, onApply, triggerEl) {
        state = {
            mode,
            onApply,
            triggerEl,
            allCandidates: [],
            vendors: [],
            excludedLabels: new Set(),
            rotationDeg: 0,
            spinning: false,
            winner: null,
            fetchController: null,
        };
    }

    function activeCandidates() {
        if (!state) return [];
        return state.allCandidates.filter((c) => !state.excludedLabels.has(c.label));
    }

    function setError(message) {
        const el = qs("wheel-error");
        if (!message) {
            el.classList.add("hidden");
            el.innerText = "";
            return;
        }
        el.innerText = message;
        el.classList.remove("hidden");
    }

    function showWheelUi(visible) {
        qs("wheel-canvas-wrap").classList.toggle("hidden", !visible);
        qs("wheel-candidate-list").classList.toggle("hidden", !visible);
        qs("wheel-spin").classList.toggle("hidden", !visible);
    }

    function updateSpinButtonState() {
        const btn = qs("wheel-spin");
        const hint = qs("wheel-spin-hint");
        const count = activeCandidates().length;
        const disabled = state.spinning || count < 2;
        btn.disabled = disabled;
        if (count < 2 && !state.spinning) {
            hint.innerText = "Minimal 2 pilihan untuk diputar";
            hint.classList.remove("hidden");
        } else {
            hint.classList.add("hidden");
        }
    }

    function renderCandidateList() {
        const container = qs("wheel-candidate-list");
        container.innerHTML = "";
        state.allCandidates.forEach((candidate) => {
            const row = document.createElement("label");
            row.className = "flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-slate-50 text-xs text-slate-700 cursor-pointer";

            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.className = "w-3.5 h-3.5";
            checkbox.setAttribute("data-testid", "wheel-candidate");
            checkbox.checked = !state.excludedLabels.has(candidate.label);
            checkbox.addEventListener("change", () => {
                if (checkbox.checked) {
                    state.excludedLabels.delete(candidate.label);
                } else {
                    state.excludedLabels.add(candidate.label);
                }
                renderWheel();
                updateSpinButtonState();
            });

            const text = document.createElement("span");
            let label = candidate.label;
            if (state.mode === "item") {
                const priceText = candidate.price != null ? `Rp ${candidate.price.toLocaleString("id-ID")}` : "";
                label = `${candidate.label} — ${candidate.vendor}${priceText ? " (" + priceText + ")" : ""}`;
            }
            text.innerText = label;

            row.appendChild(checkbox);
            row.appendChild(text);
            container.appendChild(row);
        });
    }

    function polarPoint(cx, cy, r, angleDeg) {
        const rad = (angleDeg * Math.PI) / 180;
        return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
    }

    function renderWheel() {
        const svg = qs("wheel-svg");
        const candidates = activeCandidates();
        svg.innerHTML = "";
        if (candidates.length === 0) return;

        const cx = 150, cy = 150, r = 140;
        const n = candidates.length;
        const sliceAngle = 360 / n;
        const showLabels = n <= MAX_LABELED_SLICES;

        candidates.forEach((candidate, i) => {
            const startDeg = -90 + i * sliceAngle;
            const endDeg = -90 + (i + 1) * sliceAngle;
            const p1 = polarPoint(cx, cy, r, startDeg);
            const p2 = polarPoint(cx, cy, r, endDeg);
            const largeArc = sliceAngle > 180 ? 1 : 0;

            const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
            path.setAttribute("d", `M ${cx},${cy} L ${p1.x},${p1.y} A ${r},${r} 0 ${largeArc} 1 ${p2.x},${p2.y} Z`);
            path.setAttribute("fill", PALETTE[i % PALETTE.length]);
            path.setAttribute("stroke", "#ffffff");
            path.setAttribute("stroke-width", "1.5");
            svg.appendChild(path);

            if (showLabels) {
                const midDeg = startDeg + sliceAngle / 2;
                const labelPoint = polarPoint(cx, cy, r * 0.62, midDeg);
                const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
                text.setAttribute("x", labelPoint.x);
                text.setAttribute("y", labelPoint.y);
                text.setAttribute("fill", "#ffffff");
                text.setAttribute("font-size", n > 8 ? "7" : "9");
                text.setAttribute("font-weight", "700");
                text.setAttribute("text-anchor", "middle");
                text.setAttribute("dominant-baseline", "middle");
                text.setAttribute("transform", `rotate(${midDeg + 90}, ${labelPoint.x}, ${labelPoint.y})`);
                text.textContent = candidate.label.length > 14 ? candidate.label.slice(0, 13) + "…" : candidate.label;
                svg.appendChild(text);
            }
        });
    }

    function applyFilterVisibility() {
        const isTenant = state.mode === "tenant";
        qs("wheel-avoid-last-wrap").classList.toggle("hidden", !isTenant);
        qs("wheel-avoid-last-wrap").classList.toggle("flex", isTenant);
        qs("wheel-tenant-filter-wrap").classList.toggle("hidden", isTenant);
        qs("wheel-max-price-wrap").classList.toggle("hidden", isTenant);
        qs("wheel-main-only-wrap").classList.toggle("hidden", isTenant);
        qs("wheel-main-only-wrap").classList.toggle("flex", !isTenant);
        qs("wheel-modal-heading").innerText = isTenant ? "Roda Pilihan Tenant" : "Roda Pilihan Menu";
    }

    function buildQuery() {
        const params = new URLSearchParams();
        params.set("mode", state.mode);
        if (state.mode === "tenant") {
            params.set("avoid_last", qs("wheel-avoid-last").checked ? "true" : "false");
        } else {
            const tenant = qs("wheel-tenant-filter").value;
            if (tenant) params.set("tenant", tenant);
            const maxPrice = qs("wheel-max-price").value.trim();
            if (maxPrice !== "") params.set("max_price", maxPrice);
            params.set("main_only", qs("wheel-main-only").checked ? "true" : "false");
        }
        return params.toString();
    }

    function renderTenantFilterOptions(vendors) {
        const select = qs("wheel-tenant-filter");
        const current = select.value;
        select.innerHTML = '<option value="">Semua</option>';
        vendors.forEach((v) => {
            const opt = document.createElement("option");
            opt.value = v;
            opt.innerText = v;
            select.appendChild(opt);
        });
        if (vendors.includes(current)) {
            select.value = current;
        }
    }

    function hideResult() {
        qs("wheel-result").classList.add("hidden");
        state.winner = null;
    }

    async function fetchCandidates() {
        if (!state) return;
        setError(null);
        hideResult();
        qs("wheel-avoid-last-info").classList.add("hidden");

        if (state.fetchController) {
            state.fetchController.abort();
        }
        const controller = new AbortController();
        state.fetchController = controller;

        try {
            const resp = await fetch(`/api/v1/wheel/candidates?${buildQuery()}`, { signal: controller.signal });
            if (!resp.ok) {
                let detail = "Gagal memuat pilihan.";
                try {
                    const body = await resp.json();
                    if (body && body.detail) detail = body.detail;
                } catch (e) { /* ignore body parse errors */ }

                if (resp.status === 409) {
                    detail = "Belum ada sesi aktif";
                    showWheelUi(false);
                } else {
                    showWheelUi(true);
                }
                setError(detail);
                state.allCandidates = [];
                renderCandidateList();
                updateSpinButtonState();
                return;
            }

            const data = await resp.json();
            showWheelUi(true);
            state.allCandidates = data.candidates || [];
            state.vendors = data.vendors || [];

            if (state.mode === "item") {
                renderTenantFilterOptions(state.vendors);
            }

            if (state.mode === "tenant" && data.avoid_last_applied && data.excluded_last_tenants && data.excluded_last_tenants.length > 0) {
                const info = qs("wheel-avoid-last-info");
                info.innerText = `Tidak termasuk: ${data.excluded_last_tenants.join(", ")}`;
                info.classList.remove("hidden");
            }

            renderCandidateList();
            renderWheel();
            updateSpinButtonState();
        } catch (err) {
            if (err.name === "AbortError") return;
            console.error("Gagal memuat kandidat wheel:", err);
            setError("Gagal memuat pilihan. Coba lagi.");
            showWheelUi(true);
        }
    }

    const debouncedFetch = debounce(fetchCandidates, 300);

    function showResult(winner) {
        state.winner = winner;
        qs("wheel-result-label").innerText = winner.label;
        if (state.mode === "item") {
            const priceText = winner.price != null ? `Rp ${winner.price.toLocaleString("id-ID")}` : "Harga belum ditentukan";
            qs("wheel-result-detail").innerText = `${winner.vendor} • ${priceText}`;
        } else {
            qs("wheel-result-detail").innerText = "";
        }
        qs("wheel-result").classList.remove("hidden");
    }

    function spin() {
        if (!state || state.spinning) return;
        const candidates = activeCandidates();
        if (candidates.length < 2) return;

        state.spinning = true;
        hideResult();
        updateSpinButtonState();

        const winnerIndex = secureRandomInt(candidates.length);
        const winner = candidates[winnerIndex];
        const target = computeTargetRotation(state.rotationDeg, winnerIndex, candidates.length);

        const svg = qs("wheel-svg");

        function finishSpin() {
            state.rotationDeg = target;
            state.spinning = false;
            updateSpinButtonState();
            showResult(winner);
        }

        if (prefersReducedMotion()) {
            svg.style.transition = "none";
            svg.style.transform = `rotate(${target}deg)`;
            finishSpin();
            return;
        }

        svg.style.transition = `transform ${SPIN_DURATION_MS}ms cubic-bezier(0.12, 0.67, 0.1, 1)`;
        void svg.getBoundingClientRect(); // force reflow so the transition applies
        svg.style.transform = `rotate(${target}deg)`;

        let settled = false;
        const onEnd = () => {
            if (settled) return;
            settled = true;
            svg.removeEventListener("transitionend", onEnd);
            finishSpin();
        };
        svg.addEventListener("transitionend", onEnd);
        setTimeout(onEnd, SPIN_DURATION_MS + 300);
    }

    function closeModal() {
        qs("wheel-modal").classList.add("hidden");
        qs("wheel-modal").classList.remove("flex");
        if (state && state.fetchController) state.fetchController.abort();
        if (state && state.triggerEl && typeof state.triggerEl.focus === "function") {
            state.triggerEl.focus();
        }
    }

    function handleKeydown(e) {
        if (e.key === "Escape" && !qs("wheel-modal").classList.contains("hidden")) {
            closeModal();
        }
    }

    function setupOnce() {
        if (window.__menuWheelSetup) return;
        window.__menuWheelSetup = true;

        qs("wheel-close").addEventListener("click", closeModal);
        qs("wheel-modal").addEventListener("click", (e) => {
            if (e.target.id === "wheel-modal") closeModal();
        });
        document.addEventListener("keydown", handleKeydown);

        qs("wheel-spin").addEventListener("click", spin);
        qs("wheel-respin").addEventListener("click", () => {
            hideResult();
            spin();
        });
        qs("wheel-apply").addEventListener("click", () => {
            if (!state || !state.winner) return;
            const winner = state.winner;
            const callback = state.onApply;
            closeModal();
            if (typeof callback === "function") callback(winner);
        });

        qs("wheel-avoid-last").addEventListener("change", fetchCandidates);
        qs("wheel-tenant-filter").addEventListener("change", fetchCandidates);
        qs("wheel-main-only").addEventListener("change", fetchCandidates);
        qs("wheel-max-price").addEventListener("input", debouncedFetch);
    }

    function open(options) {
        setupOnce();
        const mode = options && options.mode === "item" ? "item" : "tenant";
        const onApply = options && options.onApply;
        const triggerEl = document.activeElement;

        resetState(mode, onApply, triggerEl);

        qs("wheel-avoid-last").checked = false;
        qs("wheel-main-only").checked = true;
        qs("wheel-max-price").value = "";
        qs("wheel-tenant-filter").innerHTML = '<option value="">Semua</option>';
        qs("wheel-avoid-last-info").classList.add("hidden");
        hideResult();
        setError(null);
        showWheelUi(true);

        const svg = qs("wheel-svg");
        svg.style.transition = "none";
        svg.style.transform = "rotate(0deg)";

        applyFilterVisibility();

        const modal = qs("wheel-modal");
        modal.classList.remove("hidden");
        modal.classList.add("flex");
        qs("wheel-close").focus();

        fetchCandidates();
    }

    window.MenuWheel = { open };
})();
