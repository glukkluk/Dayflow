(() => {
    // Capture runs before HTMX's change handler serializes the form.
    document.addEventListener("change", (event) => {
        const input = event.target;
        if (!(input instanceof HTMLInputElement) ||
            input.form?.id !== "task-filters" || !input.checked) return;

        const opposite = {
            overdue: "not_overdue",
            not_overdue: "overdue",
        }[input.name];
        if (!opposite) return;

        // No synthetic change: the original event sends one consistent request.
        input.form.elements.namedItem(opposite).checked = false;
    }, true);
})();
