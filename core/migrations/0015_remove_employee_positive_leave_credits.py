# Generated by Django 5.1.7 on 2025-06-01 22:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_employee_status'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='employee',
            name='positive_leave_credits',
        ),
    ]
