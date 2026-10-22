(() => {
    "use strict";
    document.addEventListener("DOMContentLoaded", () => {
        const checkbox = document.getElementById("id_no_deadline");
        const deadline = document.getElementById("id_deadline");
        const status = document.getElementById("id_status");
        if (!checkbox || !deadline || !status) return;
        const update = () => {
            deadline.disabled = checkbox.checked;
            deadline.closest(".editor-field").hidden = checkbox.checked;
            const free = checkbox.checked || !deadline.value;
            const blocked = free && status.dataset.startedFree !== "true";
            status.querySelector('option[value="in_progress"]').disabled = blocked;
            status.setCustomValidity(blocked && status.value === "in_progress"
                ? "Вільне завдання береться в роботу через дашборд. Оберіть статус «До виконання»."
                : "");
        };
        checkbox.addEventListener("change", update);
        deadline.addEventListener("input", update);
        status.addEventListener("change", update);
        update();
    });
})();
