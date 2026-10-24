from django.db import migrations

MANAGER_GROUP = "Менеджер"
CODENAME = "view_all_events"


def create_manager_group(apps, schema_editor):
    """Створює групу «Менеджер» з правом переглядати події всіх користувачів."""
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")
    db = schema_editor.connection.alias

    content_type, _ = ContentType.objects.using(db).get_or_create(
        app_label="planner", model="event"
    )
    # Право зазвичай створює сигнал post_migrate, але в нових БД він ще не спрацював.
    permission, _ = Permission.objects.using(db).get_or_create(
        content_type=content_type,
        codename=CODENAME,
        defaults={"name": "Може переглядати події всіх користувачів"},
    )
    group, _ = Group.objects.using(db).get_or_create(name=MANAGER_GROUP)
    group.permissions.add(permission)


def remove_manager_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.using(schema_editor.connection.alias).filter(name=MANAGER_GROUP).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("planner", "0008_event_view_all_events_permission"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [migrations.RunPython(create_manager_group, remove_manager_group)]
