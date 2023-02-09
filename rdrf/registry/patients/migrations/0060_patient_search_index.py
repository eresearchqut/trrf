# Generated by Django 3.2.16 on 2023-02-10 08:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0059_living_status_column_permission'),
        ('rdrf', '0152_apply_unaccent_extension'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE FUNCTION sanitise_text_for_search(text) RETURNS text LANGUAGE SQL IMMUTABLE AS
            'SELECT unaccent(REPLACE($1, '''''''', ''''));'
            """,
            reverse_sql="DROP FUNCTION sanitise_text_for_search;"
        ),
        migrations.RunSQL(
            sql='''
            CREATE INDEX patient_family_name_idx ON patients_patient 
            USING gin ((to_tsvector('simple'::regconfig, 
            COALESCE(sanitise_text_for_search("family_name"), '') || ' ' || COALESCE(sanitise_text_for_search("given_names"), ''))));
            ''',
            reverse_sql="DROP INDEX patient_family_name_idx;"
        )
    ]
