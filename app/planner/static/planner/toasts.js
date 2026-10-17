(() => {
    "use strict";
    const POLL_INTERVAL_MS = 30000;
    const TOAST_DURATION_MS = 10000;

    function getCookie(name) {
        const match = document.cookie.match(
            new RegExp(`(?:^|; )${name}=([^;]*)`),
        );
        return match ? decodeURIComponent(match[1]) : null;
    }

    async function api(url, options = {}) {
        const response = await fetch(url, {
            credentials: "same-origin",
            ...options,
        });
        if (!response.ok) throw new Error("Не вдалося отримати повідомлення.");
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

    async function poll() {
        try {
            const pending = await api("/api/notifications/pending/");
            if (pending.length > 0) {
                pending.forEach(showToast);
                await api("/api/notifications/read/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCookie("csrftoken"),
                    },
                    body: JSON.stringify({
                        ids: pending.map((item) => item.id),
                    }),
                });
            }
            updateBadge(0);
        } catch (error) {
            console.warn("Повідомлення:", error.message);
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        if (!document.getElementById("toast-container")) return;
        poll();
        setInterval(poll, POLL_INTERVAL_MS);
    });
})();
