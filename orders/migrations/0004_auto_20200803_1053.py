# Generated by Django 3.0.8 on 2020-08-03 05:23

from django.db import migrations
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_auto_20200803_0857'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='address',
            options={'ordering': ['id'], 'verbose_name_plural': 'Addresses'},
        ),
        migrations.AlterField(
            model_name='address',
            name='country',
            field=django_countries.fields.CountryField(max_length=2),
        ),
    ]
