import random
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from planner.models import Category, Event, Task

DEMO_USERS = ("demo_user", "demo_manager")

EVENT_TITLES = (
    "Планування тижня",
    "Зустріч з командою",
    "Лекція з баз даних",
    "Тренування",
    "Обід з колегою",
    "Консультація з керівником практики",
    "Прийом у лікаря",
    "Читання статті",
    "Підготовка звіту",
    "Прогулянка в парку",
    "Розбір пошти",
    "Код-рев'ю",
    "Заняття з англійської",
    "Покупки",
    "Дзвінок рідним",
)
TASK_TITLES = (
    "Написати розділ звіту",
    "Налаштувати PostgreSQL",
    "Здати лабораторну",
    "Оновити резюме",
    "Прибрати на столі",
    "Підготувати презентацію",
    "Прочитати документацію Django",
    "Купити подарунок",
    "Записатися до стоматолога",
    "Оплатити рахунки",
    "Скласти план на місяць",
    "Пройти онлайн-курс",
    "Розібрати фото",
    "Написати тести",
    "Відповісти на листи",
)


class Command(BaseCommand):
    help = "Створює демонстраційних користувачів, події та завдання (ідемпотентно)."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="demo-pass-2026")
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Спершу видалити демо-користувачів разом з їхніми даними.",
        )
        parser.add_argument("--seed", type=int, default=2026)

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        rng = random.Random(options["seed"])
        if options["reset"]:
            deleted, _ = User.objects.filter(username__in=DEMO_USERS).delete()
            self.stdout.write(f"Видалено об'єктів: {deleted}")

        for username in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=username, defaults={"email": f"{username}@example.com"}
            )
            if not created:
                self.stdout.write(
                    f"{username}: уже існує, пропускаю (--reset для перестворення)"
                )
                continue
            user.set_password(options["password"])
            user.save()
            self.fill(user, rng)
            self.stdout.write(self.style.SUCCESS(f"{username}: дані створено"))
        self.stdout.write(f"Пароль демо-користувачів: {options['password']}")

    def fill(self, user, rng):
        tz = ZoneInfo(user.profile.timezone)
        categories = list(Category.objects.filter(user=user))  # ty: ignore[unresolved-attribute]
        today = timezone.localdate()

        def at(day, hour, minute=0):
            return datetime.combine(day, time(hour, minute), tzinfo=tz)

        events = []
        for i in range(25):
            day = today + timedelta(days=rng.randint(-10, 14))
            start = at(day, rng.randint(8, 18), rng.choice((0, 15, 30, 45)))
            all_day = i % 12 == 0
            if all_day:
                start = at(day, 0)
            events.append(
                Event(
                    user=user,
                    title=rng.choice(EVENT_TITLES),
                    description="Демонстраційна подія." if i % 3 else "",
                    start=start,
                    end=start
                    + (
                        timedelta(days=1)
                        if all_day
                        else timedelta(minutes=rng.choice((30, 45, 60, 90)))
                    ),
                    all_day=all_day,
                    recurrence=rng.choice(
                        ("none",) * 3 + ("weekly", "daily", "monthly")
                    )
                    if i % 5 == 0
                    else "none",
                    reminder_minutes=rng.choice((None, 15, 60, 1440))
                    if not all_day
                    else rng.choice((None, 1440)),
                    category=rng.choice(categories),
                )
            )
        Event.objects.bulk_create(events)  # ty: ignore[unresolved-attribute]

        for i in range(25):
            status = rng.choice(Task.Status.values)
            free = i % 5 == 0
            if free and status == Task.Status.IN_PROGRESS:
                status = Task.Status.TODO
            deadline = (
                None
                if free
                else at(today + timedelta(days=rng.randint(-5, 20)), rng.randint(9, 20))
            )
            Task.objects.create(  # ty: ignore[unresolved-attribute]
                user=user,
                title=rng.choice(TASK_TITLES),
                description="Демонстраційне завдання." if i % 2 else "",
                deadline=deadline,
                priority=rng.choice(Task.Priority.values),
                estimated_minutes=rng.choice((15, 30, 45, 60, 90, 120)),
                status=status,
                category=rng.choice(categories),
            )
