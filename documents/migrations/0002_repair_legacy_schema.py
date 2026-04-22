from pathlib import Path
import mimetypes

from django.conf import settings
from django.db import migrations


def repair_legacy_schema(apps, schema_editor):
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        existing_tables = set(connection.introspection.table_names())

        if 'documents_category' not in existing_tables:
            cursor.execute(
                '''
                CREATE TABLE documents_category (
                    id bigint NOT NULL AUTO_INCREMENT,
                    name varchar(100) NOT NULL,
                    description longtext NOT NULL,
                    created_at datetime(6) NOT NULL,
                    PRIMARY KEY (id),
                    UNIQUE KEY documents_category_name_uniq (name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )

        if 'documents_tag' not in existing_tables:
            cursor.execute(
                '''
                CREATE TABLE documents_tag (
                    id bigint NOT NULL AUTO_INCREMENT,
                    name varchar(50) NOT NULL,
                    PRIMARY KEY (id),
                    UNIQUE KEY documents_tag_name_uniq (name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )

        if 'documents_document_tags' not in existing_tables:
            cursor.execute(
                '''
                CREATE TABLE documents_document_tags (
                    id bigint NOT NULL AUTO_INCREMENT,
                    document_id bigint NOT NULL,
                    tag_id bigint NOT NULL,
                    PRIMARY KEY (id),
                    UNIQUE KEY documents_document_tags_document_id_tag_id_uniq (document_id, tag_id),
                    KEY documents_document_tags_document_id_idx (document_id),
                    KEY documents_document_tags_tag_id_idx (tag_id),
                    CONSTRAINT documents_document_tags_document_fk
                        FOREIGN KEY (document_id) REFERENCES documents_document (id)
                        ON DELETE CASCADE,
                    CONSTRAINT documents_document_tags_tag_fk
                        FOREIGN KEY (tag_id) REFERENCES documents_tag (id)
                        ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                '''
            )

        if 'documents_document' in existing_tables:
            existing_columns = {
                column.name for column in connection.introspection.get_table_description(cursor, 'documents_document')
            }

            if 'file_name' not in existing_columns:
                cursor.execute('ALTER TABLE documents_document ADD COLUMN file_name varchar(255) NULL')
            if 'uploaded_by_id' not in existing_columns:
                cursor.execute('ALTER TABLE documents_document ADD COLUMN uploaded_by_id int NULL')
            if 'upload_date' not in existing_columns:
                cursor.execute('ALTER TABLE documents_document ADD COLUMN upload_date datetime(6) NULL')
            if 'file_data' not in existing_columns:
                cursor.execute('ALTER TABLE documents_document ADD COLUMN file_data longblob NULL')
            if 'file_mime_type' not in existing_columns:
                cursor.execute('ALTER TABLE documents_document ADD COLUMN file_mime_type varchar(100) NULL')
            if 'category_id' not in existing_columns:
                cursor.execute('ALTER TABLE documents_document ADD COLUMN category_id bigint NULL')
            if 'notes' not in existing_columns:
                cursor.execute('ALTER TABLE documents_document ADD COLUMN notes longtext NULL')
            if 'updated_at' not in existing_columns:
                cursor.execute('ALTER TABLE documents_document ADD COLUMN updated_at datetime(6) NULL')

            cursor.execute(
                '''
                SELECT id, `file`, uploaded_at, user_id, file_type, file_name, uploaded_by_id,
                       upload_date, file_mime_type, updated_at, file_data
                FROM documents_document
                '''
            )
            rows = cursor.fetchall()

            for row in rows:
                (
                    document_id,
                    legacy_file,
                    legacy_uploaded_at,
                    legacy_user_id,
                    legacy_file_type,
                    current_file_name,
                    current_uploaded_by_id,
                    current_upload_date,
                    current_file_mime_type,
                    current_updated_at,
                    current_file_data,
                ) = row

                file_name = current_file_name or legacy_file or ''
                uploaded_by_id = current_uploaded_by_id or legacy_user_id
                upload_date = current_upload_date or legacy_uploaded_at
                file_mime_type = current_file_mime_type or ''

                if not file_mime_type:
                    if legacy_file_type and '/' in legacy_file_type:
                        file_mime_type = legacy_file_type
                    else:
                        file_mime_type = mimetypes.guess_type(file_name)[0] or ''

                updated_at = current_updated_at or upload_date

                file_data = current_file_data
                if not file_data and file_name:
                    candidate_path = Path(settings.MEDIA_ROOT) / file_name
                    if candidate_path.exists():
                        file_data = candidate_path.read_bytes()

                cursor.execute(
                    '''
                    UPDATE documents_document
                    SET file_name = %s,
                        uploaded_by_id = %s,
                        upload_date = %s,
                        file_mime_type = %s,
                        notes = COALESCE(notes, ''),
                        updated_at = %s,
                        file_data = %s
                    WHERE id = %s
                    ''',
                    [
                        file_name,
                        uploaded_by_id,
                        upload_date,
                        file_mime_type,
                        updated_at,
                        file_data,
                        document_id,
                    ],
                )


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(repair_legacy_schema, migrations.RunPython.noop),
    ]