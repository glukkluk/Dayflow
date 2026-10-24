// Shared time dropdown and autocompletion for event and task forms.
(() => {
    const pad = (n) => String(n).padStart(2, "0");
    const formatMinutes = (total) => `${pad(Math.floor(total / 60))}:${pad(total % 60)}`;

    // Mirrors parse_time_text() in planner/forms.py: 13 -> 13:00, 930 -> 09:30.
    function parseTime(text) {
        text = (text || "").trim();
        if (!text) return null;
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
        if (hour > 23 || minute > 59) return undefined;
        return hour * 60 + minute;
    }

    function normalizeTime(input) {
        input.setCustomValidity("");
        if (input.disabled || input.hidden) return;
        const minutes = parseTime(input.value);
        if (minutes === null) return;
        if (minutes === undefined) {
            input.setCustomValidity("Вкажіть час у форматі ГГ:ХХ, наприклад 13 або 13:30.");
            return;
        }
        input.value = formatMinutes(minutes);
    }

    const TIME_OPTIONS = Array.from({ length: 96 }, (_, i) => formatMinutes(i * 15));

    function attach(input) {
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
            const minutes = parseTime(input.value);
            if (typeof minutes !== "number") return -1;
            const index = TIME_OPTIONS.findIndex((option) => parseTime(option) >= minutes);
            return index === -1 ? TIME_OPTIONS.length - 1 : index;
        }

        function choose(value) {
            input.value = value;
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
                item.textContent = option;
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
        input.form.addEventListener("submit", () => normalizeTime(input), true);
    }

    window.DayflowTimeInput = { parseTime, formatMinutes, attach };
})();
