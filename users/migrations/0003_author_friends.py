# Generated by Django 3.0.2 on 2020-02-28 21:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20200223_0238'),
    ]

    operations = [
        migrations.AddField(
            model_name='author',
            name='friends',
            field=models.ManyToManyField(related_name='followers', to='users.Author'),
        ),
    ]
