// Text dates follow the profile; the browser picker only supplies an ISO date.
(() => {
    "use strict";
    const pad = (value) => String(value).padStart(2, "0");

    function parseDate(text, format) {
        text = (text || "").trim();
        if (!text) return null;
        let year, month, day;
        const iso = text.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
        if (iso) {
            [, year, month, day] = iso.map(Number);
        } else {
            const pattern = format === "dmy_dot"
                ? /^(\d{1,2})\.(\d{1,2})\.(\d{4})$/
                : /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/;
            const match = text.match(pattern);
            if (!match || format === "ymd_dash") return null;
            const [, first, second, last] = match.map(Number);
            year = last;
            [day, month] = format === "mdy_slash" ? [second, first] : [first, second];
        }
        const date = new Date(0);
        date.setUTCFullYear(year, month - 1, day);
        if (year < 1 || date.getUTCFullYear() !== year
            || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return null;
        return `${String(year).padStart(4, "0")}-${pad(month)}-${pad(day)}`;
    }

    function formatDate(iso, format) {
        if (!iso) return "";
        const [year, month, day] = iso.split("-");
        if (format === "dmy_dot") return `${day}.${month}.${year}`;
        if (format === "dmy_slash") return `${day}/${month}/${year}`;
        if (format === "mdy_slash") return `${month}/${day}/${year}`;
        return iso;
    }

    const getISO = (input) => parseDate(input.value, input.dataset.dateFormat);
    const setISO = (input, iso) => {
        input.value = formatDate(iso, input.dataset.dateFormat);
        input.setCustomValidity("");
    };

    function attach(input) {
        function normalize() {
            input.setCustomValidity("");
            if (input.disabled || !input.value.trim()) return;
            const iso = getISO(input);
            if (iso) setISO(input, iso);
            else input.setCustomValidity(`Укажіть дійсну дату у форматі ${input.placeholder}.`);
        }
        input.addEventListener("input", () => input.setCustomValidity(""));
        input.addEventListener("change", normalize);
        input.addEventListener("blur", normalize);
        if (input.form) input.form.addEventListener("submit", normalize, true);

        const button = input.parentElement.querySelector("[data-date-picker]");
        const picker = document.createElement("input");
        picker.type = "date";
        if (!picker.showPicker || !button) return;
        picker.className = "date-picker-native";
        picker.tabIndex = -1;
        picker.setAttribute("aria-hidden", "true");
        input.parentElement.append(picker);
        button.hidden = false;
        button.addEventListener("click", () => {
            if (input.disabled) return;
            picker.value = getISO(input) || "";
            picker.showPicker();
        });
        picker.addEventListener("change", () => {
            setISO(input, picker.value);
            input.dispatchEvent(new Event("input", { bubbles: true }));
            input.dispatchEvent(new Event("change", { bubbles: true }));
            input.focus();
        });
    }

    window.DayflowDateInput = { parseDate, formatDate, getISO, setISO };
    document.addEventListener("DOMContentLoaded", () => {
        document.querySelectorAll("[data-date-format]").forEach(attach);
    });
})();
