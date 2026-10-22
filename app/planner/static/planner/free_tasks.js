(() => {
    "use strict";
    const form = document.querySelector("[data-free-time-form]");
    if (!form) return;
    const amount = form.elements.amount;
    const unit = form.elements.unit;
    const updateLimit = () => {
        amount.max = unit.value === "hours" ? "24" : "59";
    };
    unit.addEventListener("change", updateLimit);
    updateLimit();
    const dialog = document.getElementById("free-task-dialog");
    if (!dialog || typeof dialog.showModal !== "function") return;
    const results = dialog.querySelector("[data-free-task-results]");
    const button = form.querySelector('button[type="submit"]');
    let controller;

    dialog.addEventListener("close", () => controller?.abort());
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        controller?.abort();
        const request = new AbortController();
        controller = request;
        const url = new URL(form.action);
        url.search = new URLSearchParams(new FormData(form)).toString();
        results.textContent = "Шукаємо завдання…";
        results.setAttribute("aria-busy", "true");
        button.disabled = true;
        dialog.showModal();
        try {
            const response = await fetch(url, {
                headers: { "X-Requested-With": "XMLHttpRequest" },
                signal: request.signal,
            });
            if (response.redirected) {
                window.location.assign(response.url);
                return;
            }
            if (!response.ok) throw new Error("Request failed");
            const html = await response.text();
            if (!request.signal.aborted) results.innerHTML = html;
        } catch (error) {
            if (error.name !== "AbortError") {
                results.textContent =
                    "Не вдалося завантажити завдання. Закрийте вікно та спробуйте ще раз.";
            }
        } finally {
            if (controller === request) {
                results.removeAttribute("aria-busy");
                button.disabled = false;
            }
        }
    });
})();
