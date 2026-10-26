// Recheck the session when Back/Forward restores a cached authentication page.
window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
        window.location.reload();
    }
});
