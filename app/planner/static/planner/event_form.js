// Event form: "all day" toggle, date syncing and time autocompletion.
(() => {
    const STEP = 15;
    const DAY = 1440;

    const { parseTime, formatMinutes, attach } = window.DayflowTimeInput;

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

    function init() {
        document.querySelectorAll("[data-clear-date]").forEach((button) => {
            button.addEventListener("click", () => {
                const input = document.getElementById(button.dataset.clearDate);
                if (!input) return;
                input.value = "";
                input.dispatchEvent(new Event("input", { bubbles: true }));
                input.dispatchEvent(new Event("change", { bubbles: true }));
            });
        });

        const recurrence = document.querySelector('select[name="recurrence"]');
        const recurrenceUntil = document.querySelector('input[name="recurrence_until"]');
        if (recurrence && recurrenceUntil) {
            const recurrenceUntilField = recurrenceUntil.closest(".editor-field");
            const applyRecurrence = () => {
                recurrenceUntilField.hidden = recurrence.value === "none";
            };
            recurrence.addEventListener("change", applyRecurrence);
            applyRecurrence();
        }

        const allDay = document.querySelector('input[name="all_day"]');
        const startDate = document.querySelector('input[name="start_0"]');
        const startTime = document.querySelector('input[name="start_1"]');
        const endDate = document.querySelector('input[name="end_0"]');
        const endTime = document.querySelector('input[name="end_1"]');
        if (!allDay || !startDate || !startTime || !endDate || !endTime) return;

        const timeInputs = [startTime, endTime];

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

        timeInputs.forEach(attach);

        applyAllDay();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
