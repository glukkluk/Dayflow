from django.shortcuts import render


def permission_denied(request, exception=None):
    return render(request, "error_page.html", {
        "code": "403",
        "heading": "Доступ обмежено",
        "message": "У вас немає дозволу переглядати цю сторінку. Якщо вважаєте, що це помилка, зверніться до адміністратора.",
    }, status=403)


def page_not_found(request, exception=None):
    return render(request, "error_page.html", {
        "code": "404",
        "heading": "Сторінку не знайдено",
        "message": "Можливо, адресу змінено або сторінку видалено. Перевірте посилання або поверніться на головну.",
    }, status=404)
