// Shared profile-aware time dropdown and autocompletion.
(() => {
    "use strict";
    const pad = (n) => String(n).padStart(2, "0");
    const formatMinutes = (total, hour12 = false) => {
        const hour = Math.floor(total / 60);
        return hour12
            ? `${hour % 12 || 12}:${pad(total % 60)} ${hour < 12 ? "AM" : "PM"}`
            : `${pad(hour)}:${pad(total % 60)}`;
    };
    const uses12Hours = (input) => input.dataset.timeFormat === "12h";
    const attached = new WeakSet();

    // Mirrors parse_time_text() in accounts/time_inputs.py.
    function parseTime(text, hour12 = false) {
        text = (text || "").trim();
        if (!text) return null;
        let meridiem;
        if (hour12) {
            const suffix = text.match(/\s*(AM|PM)$/i);
            if (!suffix) return undefined;
            meridiem = suffix[1].toUpperCase();
            text = text.slice(0, suffix.index).trim();
        }
        let hour, minute;
        const match = text.match(/^(\d{1,2})[:.\s](\d{1,2})$/);
        if (match) {
            hour = Number(match[1]);
            minute = Number(match[2]);
        } else if (/^\d{1,4}$/.test(text)) {
            if (text.length <= 2) {
                hour = Number(text);
                minute = 0;
            } else {
                hour = Number(text.slice(0, -2));
                minute = Number(text.slice(-2));
            }
        } else {
            return undefined;
        }
        if (minute > 59 || (hour12 ? hour < 1 || hour > 12 : hour > 23)) return undefined;
        if (hour12) hour = hour % 12 + (meridiem === "PM" ? 12 : 0);
        return hour * 60 + minute;
    }

    function normalizeTime(input) {
        input.setCustomValidity("");
        if (input.disabled || input.hidden) return;
        const hour12 = uses12Hours(input);
        const minutes = parseTime(input.value, hour12);
        if (minutes === null) return;
        if (minutes === undefined) {
            input.setCustomValidity(hour12
                ? "Укажіть час із AM або PM, наприклад 2:30 PM."
                : "Вкажіть час у форматі ГГ:ХХ, наприклад 13 або 13:30.");
            return;
        }
        input.value = formatMinutes(minutes, hour12);
    }

    const TIME_OPTIONS = Array.from({ length: 96 }, (_, i) => i * 15);

    function attach(input) {
        if (attached.has(input)) return;
        attached.add(input);
        let list = null;
        let active = -1;
        const items = () => (list ? Array.from(list.children) : []);

        function setActive(index, scroll = true) {
            const all = items();
            all.forEach((item) => item.classList.remove("is-active"));
            active = index;
            if (index < 0 || !all[index]) return;
            all[index].classList.add("is-active");
            if (scroll) list.scrollTop = all[index].offsetTop - list.clientHeight / 2;
        }

        function nearestIndex() {
            const minutes = parseTime(input.value, uses12Hours(input));
            if (typeof minutes !== "number") return -1;
            const index = TIME_OPTIONS.findIndex((option) => option >= minutes);
            return index === -1 ? TIME_OPTIONS.length - 1 : index;
        }

        function choose(value) {
            input.value = formatMinutes(value, uses12Hours(input));
            input.setCustomValidity("");
            input.dispatchEvent(new Event("change", { bubbles: true }));
            close();
        }

        function open() {
            if (list || input.hidden || input.disabled) return;
            list = document.createElement("ul");
            list.className = "time-list";
            list.setAttribute("role", "listbox");
            TIME_OPTIONS.forEach((option) => {
                const item = document.createElement("li");
                item.textContent = formatMinutes(option, uses12Hours(input));
                item.setAttribute("role", "option");
                // Keep focus in the input so blur does not close the list early.
                item.addEventListener("mousedown", (event) => {
                    event.preventDefault();
                    choose(option);
                });
                list.append(item);
            });
            const rect = input.getBoundingClientRect();
            list.style.left = `${rect.left + window.scrollX}px`;
            list.style.top = `${rect.bottom + window.scrollY}px`;
            list.style.minWidth = `${rect.width}px`;
            document.body.append(list);
            const index = nearestIndex();
            setActive(index);
            if (index === -1) list.scrollTop = 0;
        }

        function close() {
            if (list) list.remove();
            list = null;
            active = -1;
        }

        input.addEventListener("focus", open);
        input.addEventListener("timeformatchange", close);
        input.addEventListener("click", open);
        input.addEventListener("blur", () => {
            close();
            normalizeTime(input);
        });
        input.addEventListener("input", () => {
            input.setCustomValidity("");
            if (document.activeElement !== input) return;
            if (!list) open();
            setActive(nearestIndex());
        });
        input.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                close();
            } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                event.preventDefault();
                if (!list) open();
                const step = event.key === "ArrowDown" ? 1 : -1;
                const next = active === -1 ? nearestIndex() : active + step;
                setActive(Math.min(Math.max(next, 0), TIME_OPTIONS.length - 1));
            } else if (event.key === "Enter" && list && active !== -1) {
                event.preventDefault();
                choose(TIME_OPTIONS[active]);
            }
        });
        if (input.form) input.form.addEventListener("submit", () => normalizeTime(input), true);
    }

    function setFormat(input, format) {
        const minutes = parseTime(input.value, uses12Hours(input));
        const hour12 = format === "12h";
        input.dataset.timeFormat = hour12 ? "12h" : "24h";
        input.placeholder = hour12 ? "Г:ХХ AM/PM" : "ГГ:ХХ";
        input.maxLength = hour12 ? 8 : 5;
        input.size = hour12 ? 10 : 6;
        if (typeof minutes === "number") input.value = formatMinutes(minutes, hour12);
        input.dispatchEvent(new Event("timeformatchange"));
        normalizeTime(input);
    }

    window.OnTimeTimeInput = { parseTime, formatMinutes, uses12Hours, attach, setFormat };
    document.addEventListener("DOMContentLoaded", () => {
        document.querySelectorAll("[data-time-input]").forEach(attach);
        const selector = document.querySelector('select[name="time_format"]');
        if (selector?.form) selector.addEventListener("change", () => {
            selector.form.querySelectorAll("[data-time-input]").forEach((input) => {
                setFormat(input, selector.value);
            });
        });
    });
})();
