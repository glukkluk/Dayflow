from django.db import migrations


def create_existing_profiles(apps, schema_editor):
    Profile = apps.get_model("accounts", "Profile")
    user_model = Profile._meta.get_field("user").remote_field.model
    database = schema_editor.connection.alias
    for user_id in (
        user_model.objects.using(database).values_list("pk", flat=True).iterator()
    ):
        Profile.objects.using(database).get_or_create(user_id=user_id)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.RunPython(create_existing_profiles, migrations.RunPython.noop),
    ]
