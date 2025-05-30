# Generated by Django 5.0.1 on 2025-05-25 08:24

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_shift"),
    ]

    operations = [
        migrations.AddField(
            model_name="attendance",
            name="shift",
            field=models.ForeignKey(
                blank=True,
                help_text="Associated shift for this attendance record",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="core.shift",
            ),
        ),
    ]
