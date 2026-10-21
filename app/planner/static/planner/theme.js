(() => {
    "use strict";
    try {
        if (localStorage.getItem("planner-sidebar") === "collapsed") document.documentElement.dataset.sidebar = "collapsed";
    } catch { /* default: expanded */ }
    const key = "planner-theme";
    const system = window.matchMedia("(prefers-color-scheme: dark)");
    let preference = null;
    const readPreference = () => {
        try {
            const value = localStorage.getItem(key);
            return value === "dark" || value === "light" ? value : null;
        } catch {
            return null;
        }
    };
    const updateControls = () => {
        const dark = document.documentElement.dataset.colorScheme === "dark";
        document.querySelectorAll(".theme-toggle").forEach((button) => {
            button.hidden = false;
            button.setAttribute("aria-pressed", String(dark));
            button.querySelector(".theme-label").textContent = dark ? "Світла тема" : "Темна тема";
            button.title = dark ? "Увімкнути світлу тему" : "Увімкнути темну тему";
        });
    };
    const apply = () => {
        document.documentElement.dataset.colorScheme = preference || (system.matches ? "dark" : "light");
        updateControls();
    };
    preference = readPreference();
    // Run before styles are loaded to avoid a flash of the opposite theme.
    apply();
    document.addEventListener("DOMContentLoaded", updateControls);
    document.addEventListener("htmx:historyRestore", updateControls);
    document.addEventListener("click", (event) => {
        if (!event.target.closest(".theme-toggle")) return;
        preference = document.documentElement.dataset.colorScheme === "dark" ? "light" : "dark";
        try { localStorage.setItem(key, preference); } catch { /* In-memory choice still works. */ }
        apply();
    });
    system.addEventListener("change", () => { if (!preference) apply(); });
    window.addEventListener("storage", (event) => {
        if (event.key === key || event.key === null) {
            preference = readPreference();
            apply();
        }
    });
    window.addEventListener("pageshow", apply);
})();
