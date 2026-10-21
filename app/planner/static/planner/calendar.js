function main() {
    "use strict";
    const status = document.getElementById("calendar-status");
    if (!window.FullCalendar?.Calendar || !window.luxon?.DateTime) {
        status.textContent =
            "Не вдалося завантажити календар. Оновіть сторінку або відкрийте список подій.";
        return;
    }
    const config = JSON.parse(
        document.getElementById("calendar-config").textContent,
    );
    const DateTime = luxon.DateTime;
    const csrf = document.querySelector("#calendar-csrf input").value;
    const detail = document.getElementById("event-dialog");
    const conflictDialog = document.getElementById("conflict-dialog");
    let pending = false;

    function displayTime(value) {
        return DateTime.fromISO(value, { zone: config.timezone })
            .setLocale("uk")
            .toFormat(config.dateTimeFormat);
    }

    async function jsonRequest(url, options = {}) {
        const response = await fetch(url, {
            credentials: "same-origin",
            ...options,
        });
        if (response.redirected)
            throw new Error(
                "Сесія завершилася. Увійдіть у систему та оновіть календар.",
            );
        let data;
        try {
            data = await response.json();
        } catch {
            throw new Error("Не вдалося отримати відповідь сервера.");
        }
        if (!response.ok && response.status !== 409) {
            throw new Error(
                data.error ||
                    (data.errors || []).join(" ") ||
                    "Не вдалося зберегти зміни.",
            );
        }
        return { response, data };
    }

    function confirmConflicts(data) {
        const list = document.getElementById("conflict-list");
        list.replaceChildren();
        for (const item of data.conflicts) {
            const li = document.createElement("li");
            li.textContent = `${item.title}: ${displayTime(item.start)} — ${displayTime(item.end)}`;
            list.append(li);
        }
        document.getElementById("conflict-range").textContent =
            `Перевірено: ${displayTime(data.checked_start)} — ${displayTime(data.checked_end)}`;
        return new Promise((resolve) => {
            conflictDialog.oncancel = (event) => {
                event.preventDefault();
                finish(false);
            };
            function finish(value) {
                conflictDialog.close();
                resolve(value);
            }
            document.getElementById("conflict-save").onclick = () =>
                finish(true);
            document.getElementById("conflict-cancel").onclick = () =>
                finish(false);
            conflictDialog.showModal();
        });
    }

    async function moveEvent(info) {
        if (pending) {
            info.revert();
            return;
        }
        pending = true;
        calendar.setOption("editable", false);
        status.textContent = "Перевірка та збереження…";
        const payload = {
            start: DateTime.fromISO(info.event.startStr, {
                zone: config.timezone,
            })
                .toUTC()
                .toISO(),
            end: DateTime.fromISO(info.event.endStr, { zone: config.timezone })
                .toUTC()
                .toISO(),
            occurrence_start: info.oldEvent.extendedProps.occurrence_start,
            force: false,
        };
        const send = () =>
            jsonRequest(info.event.extendedProps.move_url, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrf,
                },
                body: JSON.stringify(payload),
            });
        try {
            let result = await send();
            if (result.response.status === 409) {
                if (!(await confirmConflicts(result.data))) {
                    info.revert();
                    status.textContent = "Зміну скасовано.";
                    return;
                }
                payload.force = true;
                result = await send();
            }
            if (!result.response.ok)
                throw new Error("Не вдалося зберегти зміни.");
            status.textContent = "Подію збережено.";
            calendar.refetchEvents();
        } catch (error) {
            info.revert();
            status.textContent = error.message;
        } finally {
            pending = false;
            calendar.setOption("editable", true);
        }
    }

    const phone = window.matchMedia("(max-width: 700px)");
    const calendar = new FullCalendar.Calendar(
        document.getElementById("calendar"),
        {
            locale: "uk",
            timeZone: config.timezone,
            eventTimeFormat: {
                hour: "numeric",
                minute: "2-digit",
                hour12: config.hour12,
            },
            slotLabelFormat: {
                hour: "numeric",
                minute: "2-digit",
                hour12: config.hour12,
            },
            initialView: window.matchMedia("(max-width: 700px)").matches ? "timeGridDay" : "timeGridWeek",
            headerToolbar: {
                left: "prev,next today",
                center: "title",
                right: "dayGridMonth,timeGridWeek,timeGridDay,listWeek",
            },
            buttons: {
                today: { text: "Сьогодні" },
                dayGridMonth: { text: "Місяць" },
                timeGridWeek: { text: "Тиждень" },
                timeGridDay: { text: "День" },
                listWeek: { text: "Список" },
            },
            height: "auto",
            // Phones: month cells are tiny, so a day with events shows one
            // "view events (N)" link that opens the day view instead of the events.
            dayMaxEvents: phone.matches ? 0 : true,
            moreLinkContent: (arg) =>
                phone.matches
                    ? {
                          html: `<span class="wd-more-label">Подивитися події</span><span class="wd-more-count" aria-hidden="true">${arg.num}</span><span class="wd-more-sr">(${arg.num})</span>`,
                      }
                    : `+ ще ${arg.num}`,
            moreLinkClick: (arg) => {
                if (!phone.matches) return "popover";
                calendar.changeView("timeGridDay", arg.date);
            },
            firstDay: 1,
            nowIndicator: true,
            editable: true,
            forceEventDuration: true,
            eventDurationEditable: true,
            businessHours: {
                daysOfWeek: [0, 1, 2, 3, 4, 5, 6],
                startTime: config.workStart,
                endTime: config.workEnd,
            },
            eventAllow: (drop, event) =>
                !pending && drop.allDay === event.allDay,
            events: async (range) => {
                try {
                    const url = new URL(config.feedUrl, window.location.origin);
                    url.searchParams.set("start", range.startStr);
                    url.searchParams.set("end", range.endStr);
                    const { data } = await jsonRequest(url);
                    return data;
                } catch (error) {
                    status.textContent = error.message;
                    throw error;
                }
            },
            dateClick: (info) => {
                if (pending) return;
                const start = DateTime.fromISO(info.dateStr, {
                    zone: config.timezone,
                });
                const end = start.plus(
                    info.allDay ? { days: 1 } : { hours: 1 },
                );
                const url = new URL(config.createUrl, window.location.origin);
                url.searchParams.set("start", start.toISO());
                url.searchParams.set("end", end.toISO());
                url.searchParams.set("all_day", String(info.allDay));
                window.location.assign(url);
            },
            eventClick: (info) => {
                const event = info.event;
                document.getElementById("event-dialog-title").textContent =
                    event.title;
                document.getElementById("event-dialog-time").textContent =
                    event.allDay
                        ? `${event.startStr} — ${event.endStr} (кінець не включено, весь день)`
                        : `${displayTime(event.startStr)} — ${displayTime(event.endStr)}`;
                const chip = document.getElementById("event-dialog-category");
                chip.textContent = event.extendedProps.category || "Без категорії";
                chip.style.setProperty("--dot", event.backgroundColor || event.borderColor || "var(--c-accent)");
                document.getElementById(
                    "event-dialog-description",
                ).textContent = event.extendedProps.description;
                document.getElementById("event-dialog-series").textContent =
                    event.extendedProps.is_recurring
                        ? "Редагування та видалення стосуються всієї серії."
                        : "";
                document.getElementById("event-edit").href =
                    event.extendedProps.edit_url;
                document.getElementById("event-delete").href =
                    event.extendedProps.delete_url;
                detail.showModal();
            },
            eventDrop: moveEvent,
            eventResize: moveEvent,
        },
    );
    document.getElementById("event-close").onclick = () => detail.close();
    document.getElementById("event-close-x").onclick = () => detail.close();
    // Click on the dimmed backdrop closes the dialog.
    detail.addEventListener("click", (e) => {
        const r = detail.getBoundingClientRect();
        if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) detail.close();
    });
    phone.addEventListener("change", () => calendar.setOption("dayMaxEvents", phone.matches ? 0 : true));
    calendar.render();

    // FullCalendar's sticky day header has hashed class names and a transparent
    // background; tag it so our CSS can pin it under the app header and make it opaque.
    const root = document.getElementById("calendar");
    let tagTimer = 0;
    const tagSticky = () => {
        root.querySelectorAll(".wd-sticky").forEach((el) => el.classList.remove("wd-sticky"));
        root.querySelectorAll("*").forEach((el) => {
            if (getComputedStyle(el).position === "sticky") el.classList.add("wd-sticky");
        });
    };
    new MutationObserver(() => {
        clearTimeout(tagTimer);
        tagTimer = setTimeout(tagSticky, 80);
    }).observe(root, { childList: true, subtree: true });
    tagSticky();
}
document.addEventListener("DOMContentLoaded", main);
