from django.db import migrations


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('documents', '0003_relax_legacy_document_columns'),
    ]

    operations = [
        migrations.RunSQL(
            sql='''
                ALTER TABLE documents_document_tags
                DROP FOREIGN KEY documents_document_tags_tag_id_4f4a71e9_fk_tags_tag_id;

                ALTER TABLE documents_document_tags
                ADD CONSTRAINT documents_document_tags_tag_id_fk_documents_tag_id
                FOREIGN KEY (tag_id) REFERENCES documents_tag (id)
                ON DELETE CASCADE;
            ''',
            reverse_sql='''
                ALTER TABLE documents_document_tags
                DROP FOREIGN KEY documents_document_tags_tag_id_fk_documents_tag_id;

                ALTER TABLE documents_document_tags
                ADD CONSTRAINT documents_document_tags_tag_id_4f4a71e9_fk_tags_tag_id
                FOREIGN KEY (tag_id) REFERENCES tags_tag (id)
                ON DELETE CASCADE;
            ''',
        ),
    ]