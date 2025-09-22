# core/migrations/0013_course_course_type_customuser_allowed_tests.py
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        # 0012 is already applied in your DB per showmigrations
        ('core', '0012_add_test_models'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],  # <-- DO NOT touch DB (column already exists)
            state_operations=[
                migrations.AddField(
                    model_name='course',
                    name='course_type',
                    field=models.CharField(
                        max_length=10,
                        choices=[('video', 'Video'), ('test', 'Test')],
                        default='video',
                        db_index=True,
                    ),
                ),
                migrations.AddField(
                    model_name='customuser',
                    name='allowed_tests',
                    field=models.ManyToManyField(
                        to='core.course',
                        blank=True,
                        related_name='users_with_test_access',
                        limit_choices_to={'course_type': 'test'},
                    ),
                ),
            ],
        ),
    ]
