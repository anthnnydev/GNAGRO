# core/payroll/migrations/0003_remove_obsolete_fields.py
from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0002_add_created_by'),
    ]

    operations = [
        # Remover campos que ahora son properties
        migrations.RunSQL(
            """
            CREATE TABLE payroll_payroll_new (
                id INTEGER PRIMARY KEY,
                employee_id INTEGER NOT NULL,
                period_id INTEGER NOT NULL,
                base_salary DECIMAL(10,2) NOT NULL,
                overtime_hours DECIMAL(5,2) NOT NULL DEFAULT 0,
                overtime_rate DECIMAL(3,2) NOT NULL DEFAULT 1.5,
                is_paid BOOLEAN NOT NULL DEFAULT 0,
                payment_date DATE NULL,
                payment_method VARCHAR(100) DEFAULT 'Transferencia bancaria',
                notes TEXT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                created_by_id INTEGER NULL,
                UNIQUE(employee_id, period_id)
            );
            
            INSERT INTO payroll_payroll_new (
                id, employee_id, period_id, base_salary,
                overtime_hours, overtime_rate, is_paid,
                payment_date, payment_method, notes,
                created_at, updated_at, created_by_id
            )
            SELECT 
                id, employee_id, period_id, base_salary,
                COALESCE(overtime_hours, 0),
                COALESCE(overtime_rate, 1.5),
                is_paid, payment_date, payment_method, notes,
                created_at, updated_at, created_by_id
            FROM payroll_payroll;
            
            DROP TABLE payroll_payroll;
            ALTER TABLE payroll_payroll_new RENAME TO payroll_payroll;
            """,
            reverse_sql="SELECT 1;" # Irreversible
        ),
    ]