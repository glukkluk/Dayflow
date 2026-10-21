(() => {
    "use strict";
    const root = document.documentElement;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Time-of-day greeting (client-side so it follows the viewer's clock).
    const greeting = document.querySelector("[data-greeting]");
    if (greeting) {
        const h = new Date().getHours();
        greeting.textContent = h < 5 ? "Доброї ночі" : h < 12 ? "Доброго ранку" : h < 18 ? "Доброго дня" : "Доброго вечора";
    }

    // Count-up numbers.
    const countUp = (el) => {
        const target = Number(el.dataset.count);
        if (!Number.isFinite(target) || reduce || target === 0) return;
        const start = performance.now();
        const duration = 1100;
        const tick = (now) => {
            const t = Math.min((now - start) / duration, 1);
            el.textContent = Math.round(target * (1 - Math.pow(1 - t, 3)));
            if (t < 1) requestAnimationFrame(tick);
        };
        el.textContent = "0";
        requestAnimationFrame(tick);
    };
    document.querySelectorAll("[data-count]").forEach(countUp);

    // Staggered reveal on scroll. Content stays visible if JS or observer fails.
    const items = document.querySelectorAll("[data-reveal]");
    if (items.length && "IntersectionObserver" in window && !reduce) {
        root.classList.add("js");
        const seen = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                entry.target.classList.add("is-visible");
                seen.unobserve(entry.target);
            });
        }, { threshold: 0.08 });
        items.forEach((el, i) => {
            el.style.setProperty("--d", `${Math.min(i, 6) * 0.07}s`);
            seen.observe(el);
        });
        // Safety net: never leave blocks hidden.
        setTimeout(() => items.forEach((el) => el.classList.add("is-visible")), 2500);
    }

    // Keep "?" tooltips inside the viewport (shift sideways, flip below if clipped).
    const placeHint = (hint) => {
        const bubble = hint.querySelector(".hint-bubble");
        if (!bubble || getComputedStyle(hint).position === "static") return;
        hint.classList.remove("is-below");
        bubble.style.setProperty("--hint-shift", "0px");
        const rect = bubble.getBoundingClientRect();
        const margin = 12;
        let shift = 0;
        if (rect.left < margin) shift = margin - rect.left;
        else if (rect.right > window.innerWidth - margin) shift = window.innerWidth - margin - rect.right;
        bubble.style.setProperty("--hint-shift", `${shift}px`);
        if (rect.top < 80) hint.classList.add("is-below");
    };
    ["mouseenter", "focusin", "touchstart"].forEach((type) =>
        document.addEventListener(type, (event) => {
            const hint = event.target.closest?.(".hint");
            if (hint) placeHint(hint);
        }, { passive: true, capture: true }),
    );

    // Mobile user menu (profile / theme / sign out in one popover).
    const menu = document.querySelector(".user-menu");
    if (menu) {
        const toggle = menu.querySelector(".user-menu-toggle");
        const panel = menu.querySelector(".user-menu-panel");
        const setOpen = (open) => {
            menu.classList.toggle("is-open", open);
            toggle.setAttribute("aria-expanded", String(open));
            panel.setAttribute("aria-hidden", String(!open));
        };
        toggle.addEventListener("click", () => setOpen(!menu.classList.contains("is-open")));
        document.addEventListener("click", (event) => {
            if (!menu.contains(event.target)) setOpen(false);
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && menu.classList.contains("is-open")) {
                setOpen(false);
                toggle.focus();
            }
        });
        panel.querySelector(".theme-toggle")?.addEventListener("click", () => setOpen(false));
    }

    // Colour picker as a pill: swatch + hex value, whole pill is clickable.
    document.querySelectorAll('input[type="color"]').forEach((input) => {
        const field = document.createElement("label");
        field.className = "color-field";
        field.htmlFor = input.id;
        const value = document.createElement("output");
        value.textContent = input.value.toUpperCase();
        input.before(field);
        field.append(input, value);
        input.addEventListener("input", () => { value.textContent = input.value.toUpperCase(); });
    });

    // Collapsible sidebar (desktop): click the logo mark.
    const sidebarToggle = document.querySelector(".sidebar-toggle");
    if (sidebarToggle) {
        const narrow = window.matchMedia("(max-width: 850px)");
        const apply = (collapsed) => {
            if (collapsed) root.dataset.sidebar = "collapsed";
            else delete root.dataset.sidebar;
            const label = collapsed ? "Розгорнути бічну панель" : "Згорнути бічну панель";
            sidebarToggle.setAttribute("aria-expanded", String(!collapsed));
            sidebarToggle.setAttribute("aria-label", label);
            sidebarToggle.title = label;
        };
        apply(root.dataset.sidebar === "collapsed");
        sidebarToggle.addEventListener("click", () => {
            if (narrow.matches) {
                window.location.href = sidebarToggle.dataset.home;
                return;
            }
            const collapsed = root.dataset.sidebar !== "collapsed";
            apply(collapsed);
            try { localStorage.setItem("planner-sidebar", collapsed ? "collapsed" : "expanded"); } catch { /* not persisted */ }
        });
    }

    // Dialog openers / closers (dashboard "all events today").
    document.addEventListener("click", (event) => {
        const opener = event.target.closest("[data-open-dialog]");
        if (opener) document.getElementById(opener.dataset.openDialog)?.showModal();
        const closer = event.target.closest("[data-close-dialog]");
        if (closer) closer.closest("dialog")?.close();
        if (event.target instanceof HTMLDialogElement && event.target.id !== "conflict-dialog") {
            // Only the dimmed backdrop (outside the box) closes it, not the dialog's own padding.
            const r = event.target.getBoundingClientRect();
            const outside = event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom;
            if (outside) event.target.close();
        }
    });
})();
