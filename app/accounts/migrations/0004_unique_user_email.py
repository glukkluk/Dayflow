from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_profile_avatar_and_formats"),
        ("auth", "0012_alter_user_first_name_max_length"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunSQL(
            sql='CREATE UNIQUE INDEX auth_user_email_unique ON auth_user (email)',
            reverse_sql='DROP INDEX auth_user_email_unique',
        ),
    ]
