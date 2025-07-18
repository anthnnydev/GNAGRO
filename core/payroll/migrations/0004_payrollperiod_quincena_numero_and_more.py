# Generated by Django 5.2.1 on 2025-07-04 15:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0003_remove_obsolete_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollperiod',
            name='quincena_numero',
            field=models.IntegerField(blank=True, choices=[(1, 'Primera Quincena'), (2, 'Segunda Quincena')], help_text='Solo aplica para períodos quincenales', null=True, verbose_name='Número de Quincena'),
        ),
        migrations.AlterField(
            model_name='payrollperiod',
            name='period_type',
            field=models.CharField(choices=[('monthly', 'Mensual'), ('biweekly', 'Quincenal')], max_length=15, verbose_name='Tipo de Período'),
        ),
    ]
