"""Restore the migration already recorded in existing PostgreSQL databases."""

from django.db import migrations, models


def mark_free_tasks(apps, schema_editor):
    Task = apps.get_model("planner", "Task")
    Task.objects.using(schema_editor.connection.alias).filter(
        deadline__isnull=True
    ).update(is_free=True)


class Migration(migrations.Migration):
    dependencies = [("planner", "0010_optional_task_duration")]

    operations = [
        migrations.RemoveConstraint(
            model_name="task", name="task_free_requires_duration"
        ),
        migrations.AddField(
            model_name="task",
            name="is_free",
            field=models.BooleanField(default=False, verbose_name="Вільне завдання"),
        ),
        migrations.RunPython(mark_free_tasks, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="task",
            constraint=models.CheckConstraint(
                condition=models.Q(is_free=False)
                | models.Q(
                    is_free=True,
                    deadline__isnull=True,
                    estimated_minutes__isnull=False,
                ),
                name="task_free_requires_duration",
                violation_error_message="Для вільного завдання вкажіть орієнтовну тривалість.",
            ),
        ),
    ]
