# Generated by Django 5.0.1 on 2025-05-25 09:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_attendance_shift"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="attendance",
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name="attendance",
            name="is_rest_day",
        ),
        migrations.RemoveField(
            model_name="attendance",
            name="late_minutes",
        ),
        migrations.RemoveField(
            model_name="attendance",
            name="scheduled_end",
        ),
        migrations.RemoveField(
            model_name="attendance",
            name="scheduled_start",
        ),
    ]
