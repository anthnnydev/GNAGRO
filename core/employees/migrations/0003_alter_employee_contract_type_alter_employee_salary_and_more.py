# Generated by Django 5.2.1 on 2025-07-19 00:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0002_alter_employee_contract_type_alter_employee_salary_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employee',
            name='contract_type',
            field=models.CharField(choices=[('permanent', 'Permanente'), ('temporary', 'Temporal'), ('contract', 'Por Contrato'), ('internship', 'Pasantía')], default='permanent', max_length=15, verbose_name='Tipo de Contrato'),
        ),
        migrations.AlterField(
            model_name='employee',
            name='salary',
            field=models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Salario Actual'),
        ),
        migrations.AlterField(
            model_name='employeedocument',
            name='file',
            field=models.FileField(upload_to='employee_documents/', verbose_name='Archivo'),
        ),
    ]
