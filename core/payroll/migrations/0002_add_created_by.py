from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('payroll', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='payroll',
            name='created_by',
            field=models.ForeignKey(
                blank=True, 
                null=True, 
                on_delete=django.db.models.deletion.SET_NULL, 
                to=settings.AUTH_USER_MODEL, 
                verbose_name='Creado por'
            ),
        ),
    ]