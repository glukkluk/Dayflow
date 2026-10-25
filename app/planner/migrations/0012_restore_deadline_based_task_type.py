from django.db import migrations, models


def restore_free_flags(apps, schema_editor):
    Task = apps.get_model("planner", "Task")
    Task.objects.using(schema_editor.connection.alias).filter(
        deadline__isnull=True
    ).update(is_free=True)


class Migration(migrations.Migration):
    dependencies = [
        ("planner", "0011_remove_task_task_free_requires_duration_task_is_free_and_more")
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="task", name="task_free_requires_duration"
        ),
        migrations.RunPython(migrations.RunPython.noop, restore_free_flags),
        migrations.RemoveField(model_name="task", name="is_free"),
        migrations.AddConstraint(
            model_name="task",
            constraint=models.CheckConstraint(
                condition=models.Q(deadline__isnull=False)
                | models.Q(estimated_minutes__isnull=False),
                name="task_free_requires_duration",
                violation_error_message="Для вільного завдання вкажіть орієнтовну тривалість.",
            ),
        ),
    ]
