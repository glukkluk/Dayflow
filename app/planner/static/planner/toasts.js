(() => {
    "use strict";
    const POLL_INTERVAL_MS = 30000;
    const TOAST_DURATION_MS = 10000;

    async function poll(silent) {
        const url = silent
            ? "/api/notifications/pending/?silent=true"
            : "/api/notifications/pending/";
        const response = await fetch(url, { credentials: "same-origin" });
        if (!response.ok) {
            throw new Error("Не вдалося отримати повідомлення.");
        }
        return response.json();
    }

    function showToast(notification) {
        const container = document.getElementById("toast-container");
        if (!container) return;
        const toast = document.createElement("div");
        toast.className = "toast";
        toast.setAttribute("role", "alert");
        const title = document.createElement("strong");
        title.textContent = notification.kind_display;
        const message = document.createElement("p");
        message.textContent = notification.message;
        const close = document.createElement("button");
        close.type = "button";
        close.textContent = "Закрити";
        close.setAttribute("aria-label", "Закрити повідомлення");
        close.onclick = () => toast.remove();
        toast.append(title, message, close);
        container.append(toast);
        setTimeout(() => toast.remove(), TOAST_DURATION_MS);
    }

    function updateBadge(unread) {
        const badge = document.getElementById("notification-badge");
        if (!badge) return;
        badge.hidden = unread === 0;
        badge.textContent = unread > 99 ? "99+" : String(unread);
    }

    async function refresh(silent) {
        try {
            const data = await poll(silent);
            // Show toasts for reminders that arrived while the user was here.
            // Notifications that came due earlier only move the badge.
            data.notifications.forEach(showToast);
            updateBadge(data.unread);
        } catch (error) {
            console.warn("Повідомлення:", error.message);
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        if (!document.getElementById("toast-container")) return;
        // The first call of the page only syncs the badge: anything that came
        // due before the user arrived must not replay as a toast.
        refresh(true);
        setInterval(() => refresh(false), POLL_INTERVAL_MS);
    });
})();