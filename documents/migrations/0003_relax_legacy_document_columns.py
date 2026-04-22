from django.db import migrations


def relax_legacy_document_columns(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('ALTER TABLE documents_document MODIFY COLUMN `file` varchar(100) NULL')
        cursor.execute('ALTER TABLE documents_document MODIFY COLUMN `uploaded_at` datetime(6) NULL')
        cursor.execute('ALTER TABLE documents_document MODIFY COLUMN `user_id` int NULL')


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('documents', '0002_repair_legacy_schema'),
    ]

    operations = [
        migrations.RunPython(relax_legacy_document_columns, migrations.RunPython.noop),
    ]