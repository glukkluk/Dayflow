(() => {
    "use strict";

    const menu = document.querySelector(".menu-toggle");
    const navigation = document.getElementById("main-navigation");
    if (menu && navigation) {
        document.body.classList.add("has-mobile-menu");
        menu.hidden = false;
        const closeMenu = () => {
            document.querySelector(".menu-toggle")?.setAttribute("aria-expanded", "false");
            document.getElementById("main-navigation")?.classList.remove("is-open");
        };
        document.addEventListener("click", (event) => {
            const toggle = event.target.closest(".menu-toggle");
            if (!toggle) return;
            const open = toggle.getAttribute("aria-expanded") !== "true";
            toggle.setAttribute("aria-expanded", String(open));
            document.getElementById("main-navigation")?.classList.toggle("is-open", open);
        });
        document.addEventListener("keydown", (event) => {
            const toggle = document.querySelector(".menu-toggle");
            if (event.key === "Escape" && toggle?.getAttribute("aria-expanded") === "true") {
                closeMenu();
                toggle.focus();
            }
        });
    }

    // Reveal passwords only on explicit request; never store field values.
    document.querySelectorAll('input[type="password"]').forEach((input) => {
        const wrapper = document.createElement("div");
        wrapper.className = "password-control";
        input.before(wrapper);
        wrapper.append(input);
        const toggle = document.createElement("button");
        toggle.type = "button";
        toggle.className = "secondary password-toggle";
        toggle.textContent = "Показати";
        toggle.setAttribute("aria-controls", input.id);
        toggle.setAttribute("aria-pressed", "false");
        toggle.setAttribute("aria-label", `Показати пароль: ${input.labels?.[0]?.textContent || "пароль"}`);
        toggle.addEventListener("click", () => {
            const show = input.type === "password";
            input.type = show ? "text" : "password";
            toggle.textContent = show ? "Приховати" : "Показати";
            toggle.setAttribute("aria-pressed", String(show));
        });
        wrapper.append(toggle);
    });

    document.querySelector(".error-summary")?.focus();
    document.querySelectorAll("[data-edit-form]").forEach((form) => {
        const state = form.querySelector(".save-state");
        form.addEventListener("input", () => { state.textContent = "Є незбережені зміни"; });
        let submitting = false;
        form.addEventListener("submit", (event) => {
            if (submitting) {
                event.preventDefault();
                return;
            }
            submitting = true;
            form.setAttribute("aria-busy", "true");
            state.textContent = "Зберігаємо…";
            // Keep the submitter enabled so name=force reaches the server.
            event.submitter?.setAttribute("aria-disabled", "true");
        });
        window.addEventListener("pageshow", () => {
            submitting = false;
            form.removeAttribute("aria-busy");
            form.querySelectorAll("[aria-disabled]").forEach((button) => button.removeAttribute("aria-disabled"));
            state.textContent = "";
        });
    });

    const announce = (message, error = false) => {
        const status = document.getElementById("interaction-status");
        if (!status) return;
        status.hidden = false;
        status.textContent = message;
        status.classList.toggle("is-error", error);
    };
    let toggledTask = null;
    document.addEventListener("htmx:beforeRequest", (event) => {
        const button = event.detail.elt.matches("form")
            ? event.detail.elt.querySelector("[data-task-toggle]") : null;
        if (button) toggledTask = button.dataset.taskToggle;
        if (event.detail.target?.id === "task-results") {
            event.detail.target.setAttribute("aria-busy", "true");
        }
    });
    document.addEventListener("htmx:afterRequest", (event) => {
        document.getElementById("task-results")?.removeAttribute("aria-busy");
        if (event.detail.failed) {
            toggledTask = null;
            announce("Не вдалося виконати дію. Перевірте з'єднання та спробуйте ще раз.", true);
        }
    });
    document.addEventListener("htmx:sendError", () => {
        toggledTask = null;
        document.getElementById("task-results")?.removeAttribute("aria-busy");
        announce("Немає з'єднання із сервером. Спробуйте ще раз, коли зв'язок відновиться.", true);
    });
    document.addEventListener("htmx:afterSwap", (event) => {
        if (event.detail.target.id !== "task-results") return;
        if (toggledTask) {
            const button = document.querySelector(`[data-task-toggle="${toggledTask}"]`);
            (button || document.getElementById("task-result-count"))?.focus({ preventScroll: true });
            announce("Статус завдання змінено.");
            toggledTask = null;
        } else {
            document.getElementById("interaction-status").hidden = true;
        }
    });
})();
