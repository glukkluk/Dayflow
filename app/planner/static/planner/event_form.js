// Event form: "all day" toggle, date syncing and time autocompletion.
(() => {
    const STEP = 15;
    const DAY = 1440;

    const pad = (n) => String(n).padStart(2, "0");

    // Mirrors parse_time_text() in planner/forms.py: 13 -> 13:00, 930 -> 09:30.
    function parseTime(text) {
        text = (text || "").trim();
        if (!text) return null;
        let hour, minute;
        let match = text.match(/^(\d{1,2})[:.\s](\d{1,2})$/);
        if (match) {
            hour = Number(match[1]);
            minute = Number(match[2]);
        } else if (/^\d{1,4}$/.test(text)) {
            if (text.length <= 2) {
                hour = Number(text);
                minute = 0;
            } else if (text.length === 3) {
                hour = Number(text[0]);
                minute = Number(text.slice(1));
            } else {
                hour = Number(text.slice(0, 2));
                minute = Number(text.slice(2));
            }
        } else {
            return undefined;
        }
        if (hour > 23 || minute > 59) return undefined;
        return hour * 60 + minute;
    }

    const formatMinutes = (total) => `${pad(Math.floor(total / 60))}:${pad(total % 60)}`;

    // 13:07 -> 13:15, 13:51 -> 14:00, 13:15 -> 13:15 (may reach 1440 = next day 00:00).
    const roundUp = (total) => Math.ceil(total / STEP) * STEP;

    function nowMinutes(timeZone) {
        const parts = new Intl.DateTimeFormat("en-GB", {
            timeZone,
            hour: "2-digit",
            minute: "2-digit",
            hourCycle: "h23",
        }).formatToParts(new Date());
        const get = (type) => Number(parts.find((p) => p.type === type).value);
        return get("hour") * 60 + get("minute");
    }

    const dayIndex = (iso) => {
        const [y, m, d] = iso.split("-").map(Number);
        return Math.round(Date.UTC(y, m - 1, d) / 86400000);
    };
    const dayToIso = (index) => new Date(index * 86400000).toISOString().slice(0, 10);

    // Google Calendar-style dropdown with 00:00 ... 23:45 in 15-minute steps.
    const TIME_OPTIONS = Array.from({ length: DAY / STEP }, (_, i) => formatMinutes(i * STEP));

    function attachTimeList(input) {
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

        // Index of the entered time, or of the first slot after it.
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
            if (list || input.hidden) return;
            list = document.createElement("ul");
            list.className = "time-list";
            list.setAttribute("role", "listbox");
            TIME_OPTIONS.forEach((option) => {
                const item = document.createElement("li");
                item.textContent = option;
                item.setAttribute("role", "option");
                // mousedown keeps focus in the input so blur does not close the list early.
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
        input.addEventListener("blur", close);
        input.addEventListener("input", () => {
            if (!list) open();
            const index = nearestIndex();
            if (index !== -1) setActive(index);
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
                // Pick the highlighted slot instead of submitting the form.
                event.preventDefault();
                choose(TIME_OPTIONS[active]);
            }
        });
    }

    function init() {
        const allDay = document.querySelector('input[name="all_day"]');
        const startDate = document.querySelector('input[name="start_0"]');
        const startTime = document.querySelector('input[name="start_1"]');
        const endDate = document.querySelector('input[name="end_0"]');
        const endTime = document.querySelector('input[name="end_1"]');
        if (!allDay || !startDate || !startTime || !endDate || !endTime) return;

        const timeInputs = [startTime, endTime];

        function normalizeTime(input) {
            input.setCustomValidity("");
            const minutes = parseTime(input.value);
            if (minutes === null) return;
            if (minutes === undefined) {
                input.setCustomValidity("Вкажіть час у форматі ГГ:ХХ, наприклад 13 або 13:30.");
                return;
            }
            input.value = formatMinutes(minutes);
        }

        // "Remind me" offers different lead times for timed and all-day events.
        const reminder = document.querySelector('select[name="reminder_minutes"]');
        const reminderOptions = reminder ? Array.from(reminder.options) : [];
        const parseList = (text) => (text || "").split(",").filter(Boolean);
        function applyReminders() {
            if (!reminder) return;
            const allowed = parseList(
                allDay.checked ? allDay.dataset.remindersAllDay : allDay.dataset.remindersTimed,
            );
            const current = reminder.value;
            reminder.replaceChildren(
                ...reminderOptions.filter(
                    (option) => option.value === "" || allowed.includes(option.value),
                ),
            );
            reminder.value = allowed.includes(current) ? current : "";
        }

        function applyAllDay() {
            applyReminders();
            timeInputs.forEach((input) => {
                input.hidden = allDay.checked;
                if (allDay.checked) input.setCustomValidity("");
            });
        }

        // Switching to "all day": only dates, and both fields get the same date.
        function enterAllDay() {
            if (!startDate.value && endDate.value) startDate.value = endDate.value;
            if (startDate.value && (!endDate.value || endDate.value < startDate.value)) {
                endDate.value = startDate.value;
            }
        }

        // Switching back: times become the current/entered time rounded up to 15 minutes.
        function leaveAllDay() {
            const fallback = nowMinutes(allDay.dataset.timezone || undefined);
            const valid = (input) => {
                const minutes = parseTime(input.value);
                return typeof minutes === "number" ? minutes : null;
            };
            if (!startDate.value) return;
            let start = dayIndex(startDate.value) * DAY + roundUp(valid(startTime) ?? fallback);
            if (!endDate.value) endDate.value = startDate.value;
            const endClock = valid(endTime);
            let end =
                dayIndex(endDate.value) * DAY +
                (endClock !== null
                    ? roundUp(endClock)
                    : endDate.value === startDate.value
                      ? start % DAY + 60
                      : roundUp(fallback));
            if (end <= start) end = start + 60;
            startDate.value = dayToIso(Math.floor(start / DAY));
            startTime.value = formatMinutes(start % DAY);
            endDate.value = dayToIso(Math.floor(end / DAY));
            endTime.value = formatMinutes(end % DAY);
            timeInputs.forEach((input) => input.setCustomValidity(""));
        }

        allDay.addEventListener("change", () => {
            if (allDay.checked) enterAllDay();
            else leaveAllDay();
            applyAllDay();
        });

        // In "all day" mode picking a date in one field fills the other one.
        startDate.addEventListener("change", () => {
            if (allDay.checked && startDate.value) endDate.value = startDate.value;
        });
        endDate.addEventListener("change", () => {
            if (!allDay.checked || !endDate.value) return;
            if (!startDate.value || startDate.value > endDate.value) {
                startDate.value = endDate.value;
            }
        });

        timeInputs.forEach(attachTimeList);

        timeInputs.forEach((input) => {
            input.addEventListener("input", () => input.setCustomValidity(""));
            input.addEventListener("blur", () => normalizeTime(input));
        });
        // Enter submits without blur, so complete the times before the form is sent.
        allDay.form.addEventListener("submit", () => timeInputs.forEach(normalizeTime), true);

        applyAllDay();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
