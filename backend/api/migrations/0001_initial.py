import django.db.models.deletion
import django.utils.timezone
import pgvector.django.vector
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
        migrations.CreateModel(
            name='BusinessUser',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('username', models.CharField(max_length=150, unique=True)),
                ('password', models.CharField(blank=True, max_length=255, null=True)),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'db_table': 'app_user',
            },
        ),
        migrations.CreateModel(
            name='Content',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('tmdb_id', models.BigIntegerField()),
                ('media_type', models.CharField(choices=[('movie', 'Film'), ('tv', 'Serial')], max_length=10)),
                ('title', models.CharField(max_length=500)),
                ('original_title', models.CharField(blank=True, max_length=500, null=True)),
                ('overview', models.TextField(blank=True, null=True)),
                ('release_date', models.DateField(blank=True, null=True)),
                ('original_language', models.CharField(blank=True, max_length=20, null=True)),
                ('poster_path', models.CharField(blank=True, max_length=500, null=True)),
                ('vote_average', models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True)),
                ('popularity', models.DecimalField(blank=True, decimal_places=4, max_digits=14, null=True)),
                ('metadata', models.JSONField(default=dict)),
                ('tmdb_refreshed_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'content',
            },
        ),
        migrations.CreateModel(
            name='Genre',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('tmdb_genre_id', models.IntegerField(unique=True)),
                ('name', models.CharField(max_length=100)),
            ],
            options={
                'db_table': 'genre',
            },
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='profile', serialize=False, to='api.businessuser')),
                ('semantic_summary', models.TextField(blank=True, null=True)),
                ('version', models.PositiveIntegerField(default=1)),
                ('last_rebuilt_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                'db_table': 'user_profile',
            },
        ),
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('title', models.CharField(blank=True, max_length=255, null=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversations', to='api.businessuser')),
            ],
            options={
                'db_table': 'conversation',
            },
        ),
        migrations.CreateModel(
            name='ContentGenre',
            fields=[
                ('pk', models.CompositePrimaryKey('content_id', 'genre_id', blank=True, editable=False, primary_key=True, serialize=False)),
                ('content', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.content')),
                ('genre', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.genre')),
            ],
            options={
                'db_table': 'content_genre',
            },
        ),
        migrations.AddField(
            model_name='content',
            name='genres',
            field=models.ManyToManyField(related_name='contents', through='api.ContentGenre', to='api.genre'),
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('role', models.CharField(choices=[('user', 'Użytkownik'), ('assistant', 'Asystent'), ('system', 'System')], max_length=20)),
                ('content', models.TextField()),
                ('sequence_no', models.PositiveIntegerField()),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='api.conversation')),
            ],
            options={
                'db_table': 'message',
                'unique_together': {('conversation', 'sequence_no')},
            },
        ),
        migrations.CreateModel(
            name='RecommendationRequest',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('mood', models.CharField(blank=True, max_length=100, null=True)),
                ('extracted_context', models.JSONField(default=dict)),
                ('constraints', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recommendation_requests', to='api.conversation')),
                ('trigger_message', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='triggered_requests', to='api.message')),
            ],
            options={
                'db_table': 'recommendation_request',
            },
        ),
        migrations.CreateModel(
            name='RecommendationRun',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('pending', 'Oczekuje'), ('running', 'W toku'), ('completed', 'Zakończony'), ('failed', 'Nieudany'), ('cancelled', 'Anulowany')], default='pending', max_length=20)),
                ('graph_version', models.CharField(blank=True, max_length=100, null=True)),
                ('model_name', models.CharField(blank=True, max_length=255, null=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='runs', to='api.recommendationrequest')),
            ],
            options={
                'db_table': 'recommendation_run',
            },
        ),
        migrations.CreateModel(
            name='RunCandidate',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('source_rank', models.PositiveIntegerField(blank=True, null=True)),
                ('relevance_score', models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
                ('critic_score', models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
                ('final_score', models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
                ('status', models.CharField(choices=[('pending', 'Oczekuje'), ('selected', 'Wybrany'), ('rejected', 'Odrzucony')], default='pending', max_length=20)),
                ('final_rank', models.PositiveIntegerField(blank=True, null=True)),
                ('decision_reason', models.TextField(blank=True, null=True)),
                ('explanation', models.TextField(blank=True, null=True)),
                ('metadata_snapshot', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('content', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='run_candidates', to='api.content')),
                ('run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='candidates', to='api.recommendationrun')),
            ],
            options={
                'db_table': 'run_candidate',
                'unique_together': {('run', 'content')},
            },
        ),
        migrations.CreateModel(
            name='Interaction',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('interaction_type', models.CharField(choices=[('details_opened', 'Otwarto szczegóły'), ('liked', 'Polubiono'), ('disliked', 'Odrzucono'), ('watchlisted', 'Zapisano'), ('watched', 'Obejrzano'), ('rated', 'Oceniono')], max_length=30)),
                ('rating', models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True)),
                ('metadata', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('content', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='interactions', to='api.content')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='interactions', to='api.businessuser')),
                ('source_candidate', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='interactions', to='api.runcandidate')),
            ],
            options={
                'db_table': 'interaction',
            },
        ),
        migrations.CreateModel(
            name='ContentEmbedding',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('embedding', pgvector.django.vector.VectorField(dimensions=768)),
                ('embedding_model', models.CharField(max_length=255)),
                ('model_version', models.CharField(max_length=100)),
                ('source_language', models.CharField(default='pl-PL', max_length=20)),
                ('source_text_hash', models.CharField(max_length=64)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('content', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='embeddings', to='api.content')),
            ],
            options={
                'db_table': 'content_embedding',
                'unique_together': {('content', 'embedding_model', 'model_version', 'source_language')},
            },
        ),
        migrations.AlterUniqueTogether(
            name='content',
            unique_together={('tmdb_id', 'media_type')},
        ),
        migrations.CreateModel(
            name='AgentExecution',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('agent_type', models.CharField(max_length=100)),
                ('sequence_no', models.PositiveIntegerField()),
                ('status', models.CharField(choices=[('pending', 'Oczekuje'), ('running', 'W toku'), ('success', 'Sukces'), ('failed', 'Nieudany')], default='pending', max_length=20)),
                ('input_snapshot', models.JSONField(default=dict)),
                ('output_snapshot', models.JSONField(default=dict)),
                ('duration_ms', models.PositiveIntegerField(blank=True, null=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='agent_executions', to='api.recommendationrun')),
            ],
            options={
                'db_table': 'agent_execution',
                'unique_together': {('run', 'sequence_no')},
            },
        ),
        migrations.CreateModel(
            name='UserPreference',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('preference_type', models.CharField(max_length=100)),
                ('preference_value', models.TextField()),
                ('polarity', models.SmallIntegerField()),
                ('weight', models.DecimalField(decimal_places=3, default=1, max_digits=4)),
                ('confidence', models.DecimalField(decimal_places=3, default=1, max_digits=4)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='preferences', to='api.businessuser')),
            ],
            options={
                'db_table': 'user_preference',
                'unique_together': {('user', 'preference_type', 'preference_value')},
            },
        ),
            ],
        ),
    ]
