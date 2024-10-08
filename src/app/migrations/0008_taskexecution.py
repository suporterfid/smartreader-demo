# Generated by Django 3.2.25 on 2024-09-30 19:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0007_scheduledcommand'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaskExecution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_name', models.CharField(max_length=255)),
                ('is_executed', models.BooleanField(default=False)),
            ],
        ),
    ]
