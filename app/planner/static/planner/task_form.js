(() => {
    "use strict";
    document.addEventListener("DOMContentLoaded", () => {
        const checkbox = document.getElementById("id_no_deadline");
        const deadline = document.getElementById("id_deadline_0");
        const deadlineTime = document.getElementById("id_deadline_1");
        const status = document.getElementById("id_status");
        const duration = document.getElementById("id_estimated_minutes");
        if (!checkbox || !deadline || !deadlineTime || !status) return;
        window.OnTimeTimeInput.attach(deadlineTime);
        const inputs = [deadline, deadlineTime];
        document.querySelectorAll("[data-clear-deadline]").forEach((button) => {
            button.addEventListener("click", () => {
                inputs.forEach((input) => {
                    input.value = "";
                    input.setCustomValidity("");
                    input.dispatchEvent(new Event("input", { bubbles: true }));
                    input.dispatchEvent(new Event("change", { bubbles: true }));
                });
            });
        });
        const update = () => {
            inputs.forEach((input) => {
                input.disabled = checkbox.checked;
                input.required = !checkbox.checked;
                if (checkbox.checked) input.setCustomValidity("");
            });
            deadline.closest(".editor-field").hidden = checkbox.checked;
            const deadlineMarker = deadline.closest(".editor-field").querySelector(".field-requirement");
            deadlineMarker.textContent = checkbox.checked ? "Необов'язково" : "*";
            if (checkbox.checked) deadlineMarker.removeAttribute("aria-label");
            else deadlineMarker.setAttribute("aria-label", "обов'язкове поле");
            const free = checkbox.checked;
            if (duration) {
                duration.required = checkbox.checked;
                const marker = duration.closest(".editor-field").querySelector(".field-requirement");
                marker.textContent = checkbox.checked ? "*" : "Необов'язково";
                if (checkbox.checked) marker.setAttribute("aria-label", "обов'язкове поле");
                else marker.removeAttribute("aria-label");
            }
            const blocked = free && status.dataset.startedFree !== "true";
            status.querySelector('option[value="in_progress"]').disabled = blocked;
            status.setCustomValidity(blocked && status.value === "in_progress"
                ? "Вільне завдання береться в роботу через дашборд. Оберіть статус «До виконання»."
                : "");
        };
        checkbox.addEventListener("change", update);
        deadline.addEventListener("input", update);
        deadline.addEventListener("change", update);
        status.addEventListener("change", update);
        update();
    });
})();
