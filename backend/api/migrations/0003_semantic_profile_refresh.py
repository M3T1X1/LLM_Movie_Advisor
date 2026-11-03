from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('api', '0002_normalize_genres')]
    operations = [migrations.SeparateDatabaseAndState(
        # Business tables are initialized from SQL (including in integration tests).
        database_operations=[migrations.RunSQL(
            "ALTER TABLE IF EXISTS user_profile "
            "ADD COLUMN IF NOT EXISTS semantic_source_hash VARCHAR(64) NOT NULL DEFAULT '', "
            "ADD COLUMN IF NOT EXISTS semantic_pending_hash VARCHAR(64) NOT NULL DEFAULT '', "
            "ADD COLUMN IF NOT EXISTS semantic_rebuild_after TIMESTAMPTZ",
            "ALTER TABLE IF EXISTS user_profile DROP COLUMN IF EXISTS semantic_source_hash, "
            "DROP COLUMN IF EXISTS semantic_pending_hash, DROP COLUMN IF EXISTS semantic_rebuild_after")],
        state_operations=[
            migrations.AddField('userprofile', 'semantic_source_hash', models.CharField(max_length=64, default='', blank=True)),
            migrations.AddField('userprofile', 'semantic_pending_hash', models.CharField(max_length=64, default='', blank=True)),
            migrations.AddField('userprofile', 'semantic_rebuild_after', models.DateTimeField(null=True, blank=True)),
        ],
    )]
