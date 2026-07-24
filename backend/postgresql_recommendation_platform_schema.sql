BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

       
CREATE TYPE media_type_enum AS ENUM (
    'movie',
    'tv'
);

CREATE TYPE message_role_enum AS ENUM (
    'user',
    'assistant',
    'system'
);

CREATE TYPE recommendation_run_status_enum AS ENUM (
    'pending',
    'running',
    'completed',
    'failed',
    'cancelled'
);

CREATE TYPE candidate_status_enum AS ENUM (
    'pending',
    'selected',
    'rejected'
);

CREATE TYPE agent_execution_status_enum AS ENUM (
    'pending',
    'running',
    'success',
    'failed'
);

CREATE TYPE interaction_type_enum AS ENUM (
    'details_opened',
    'liked',
    'disliked',
    'watchlisted',
    'watched',
    'rated'
);


CREATE TABLE app_user (
    id              BIGSERIAL PRIMARY KEY,
    email           VARCHAR(254) NOT NULL UNIQUE,
    username        VARCHAR(150) NOT NULL UNIQUE,
    password        VARCHAR(255),
    date_joined     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE user_profile (
    user_id          BIGINT PRIMARY KEY,
    semantic_summary TEXT,
    version           INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    last_rebuilt_at   TIMESTAMPTZ,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_user_profile_user
        FOREIGN KEY (user_id)
        REFERENCES app_user(id)
        ON DELETE CASCADE
);

CREATE TABLE user_preference (
    id                BIGSERIAL PRIMARY KEY,
    user_id           BIGINT NOT NULL,
    preference_type   VARCHAR(100) NOT NULL,
    preference_value  TEXT NOT NULL,
    polarity          SMALLINT NOT NULL CHECK (polarity IN (-1, 0, 1)),
    weight            NUMERIC(4,3) NOT NULL DEFAULT 1.000
                      CHECK (weight >= 0 AND weight <= 1),
    confidence        NUMERIC(4,3) NOT NULL DEFAULT 1.000
                      CHECK (confidence >= 0 AND confidence <= 1),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_user_preference_user
        FOREIGN KEY (user_id)
        REFERENCES app_user(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_user_preference
        UNIQUE (user_id, preference_type, preference_value)
);

CREATE TABLE conversation (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL,
    title       VARCHAR(255),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_conversation_user
        FOREIGN KEY (user_id)
        REFERENCES app_user(id)
        ON DELETE CASCADE
);

CREATE TABLE message (
    id               BIGSERIAL PRIMARY KEY,
    conversation_id  BIGINT NOT NULL,
    role             message_role_enum NOT NULL,
    content          TEXT NOT NULL,
    sequence_no      INTEGER NOT NULL CHECK (sequence_no > 0),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_message_conversation
        FOREIGN KEY (conversation_id)
        REFERENCES conversation(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_message_sequence
        UNIQUE (conversation_id, sequence_no)
);

CREATE TABLE recommendation_request (
    id                  BIGSERIAL PRIMARY KEY,
    conversation_id     BIGINT NOT NULL,
    trigger_message_id  BIGINT,
    mood                VARCHAR(100),
    extracted_context   JSONB NOT NULL DEFAULT '{}'::JSONB,
    constraints         JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_recommendation_request_conversation
        FOREIGN KEY (conversation_id)
        REFERENCES conversation(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_recommendation_request_message
        FOREIGN KEY (trigger_message_id)
        REFERENCES message(id)
        ON DELETE SET NULL
);

CREATE TABLE recommendation_run (
    id            BIGSERIAL PRIMARY KEY,
    request_id    BIGINT NOT NULL,
    status        recommendation_run_status_enum NOT NULL DEFAULT 'pending',
    graph_version VARCHAR(100),
    model_name    VARCHAR(255),
    started_at    TIMESTAMPTZ,
    finished_at   TIMESTAMPTZ,

    CONSTRAINT fk_recommendation_run_request
        FOREIGN KEY (request_id)
        REFERENCES recommendation_request(id)
        ON DELETE CASCADE,

    CONSTRAINT chk_recommendation_run_time
        CHECK (
            finished_at IS NULL
            OR started_at IS NULL
            OR finished_at >= started_at
        )
);

CREATE TABLE content (
    id                 BIGSERIAL PRIMARY KEY,
    tmdb_id            BIGINT NOT NULL,
    media_type         media_type_enum NOT NULL,
    title              VARCHAR(500) NOT NULL,
    original_title     VARCHAR(500),
    overview           TEXT,
    release_date       DATE,
    original_language  VARCHAR(20),
    poster_path        VARCHAR(500),
    vote_average       NUMERIC(4,2)
                       CHECK (vote_average IS NULL OR
                              (vote_average >= 0 AND vote_average <= 10)),
    popularity         NUMERIC(14,4)
                       CHECK (popularity IS NULL OR popularity >= 0),
    metadata           JSONB NOT NULL DEFAULT '{}'::JSONB,
    tmdb_refreshed_at  TIMESTAMPTZ,

    CONSTRAINT uq_content_tmdb
        UNIQUE (tmdb_id, media_type)
);

CREATE TABLE genre (
    id             BIGSERIAL PRIMARY KEY,
    tmdb_genre_id  INTEGER NOT NULL UNIQUE,
    name           VARCHAR(100) NOT NULL
);

CREATE TABLE content_genre (
    content_id BIGINT NOT NULL,
    genre_id   BIGINT NOT NULL,

    PRIMARY KEY (content_id, genre_id),

    CONSTRAINT fk_content_genre_content
        FOREIGN KEY (content_id)
        REFERENCES content(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_content_genre_genre
        FOREIGN KEY (genre_id)
        REFERENCES genre(id)
        ON DELETE CASCADE
);

CREATE TABLE content_embedding (
    id                BIGSERIAL PRIMARY KEY,
    content_id        BIGINT NOT NULL,
    embedding         vector(768) NOT NULL,
    embedding_model   VARCHAR(255) NOT NULL,
    model_version     VARCHAR(100) NOT NULL,
    source_language   VARCHAR(20) NOT NULL DEFAULT 'pl-PL',
    source_text_hash  CHAR(64) NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_content_embedding_content
        FOREIGN KEY (content_id)
        REFERENCES content(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_content_embedding_version
        UNIQUE (
            content_id,
            embedding_model,
            model_version,
            source_language
        )
);

CREATE TABLE run_candidate (
    id                 BIGSERIAL PRIMARY KEY,
    run_id             BIGINT NOT NULL,
    content_id         BIGINT NOT NULL,
    source_rank        INTEGER CHECK (source_rank IS NULL OR source_rank > 0),
    relevance_score    NUMERIC(5,4)
                       CHECK (relevance_score IS NULL OR
                              (relevance_score >= 0 AND relevance_score <= 1)),
    critic_score       NUMERIC(5,4)
                       CHECK (critic_score IS NULL OR
                              (critic_score >= 0 AND critic_score <= 1)),
    final_score        NUMERIC(5,4)
                       CHECK (final_score IS NULL OR
                              (final_score >= 0 AND final_score <= 1)),
    status             candidate_status_enum NOT NULL DEFAULT 'pending',
    final_rank         INTEGER CHECK (final_rank IS NULL OR final_rank > 0),
    decision_reason    TEXT,
    explanation        TEXT,
    metadata_snapshot  JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_run_candidate_run
        FOREIGN KEY (run_id)
        REFERENCES recommendation_run(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_run_candidate_content
        FOREIGN KEY (content_id)
        REFERENCES content(id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_run_candidate
        UNIQUE (run_id, content_id)
);

CREATE TABLE interaction (
    id                   BIGSERIAL PRIMARY KEY,
    user_id              BIGINT NOT NULL,
    content_id           BIGINT NOT NULL,
    source_candidate_id  BIGINT,
    interaction_type     interaction_type_enum NOT NULL,
    rating               NUMERIC(3,1)
                         CHECK (rating IS NULL OR
                                (rating >= 0 AND rating <= 10)),
    metadata             JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_interaction_user
        FOREIGN KEY (user_id)
        REFERENCES app_user(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_interaction_content
        FOREIGN KEY (content_id)
        REFERENCES content(id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_interaction_source_candidate
        FOREIGN KEY (source_candidate_id)
        REFERENCES run_candidate(id)
        ON DELETE SET NULL,

    CONSTRAINT chk_interaction_rating
        CHECK (
            (interaction_type = 'rated' AND rating IS NOT NULL)
            OR
            (interaction_type <> 'rated' AND rating IS NULL)
        )
);

CREATE TABLE agent_execution (
    id               BIGSERIAL PRIMARY KEY,
    run_id           BIGINT NOT NULL,
    agent_type       VARCHAR(100) NOT NULL,
    sequence_no      INTEGER NOT NULL CHECK (sequence_no > 0),
    status           agent_execution_status_enum NOT NULL DEFAULT 'pending',
    input_snapshot   JSONB NOT NULL DEFAULT '{}'::JSONB,
    output_snapshot  JSONB NOT NULL DEFAULT '{}'::JSONB,
    duration_ms      INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    started_at       TIMESTAMPTZ,
    finished_at      TIMESTAMPTZ,

    CONSTRAINT fk_agent_execution_run
        FOREIGN KEY (run_id)
        REFERENCES recommendation_run(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_agent_execution_sequence
        UNIQUE (run_id, sequence_no),

    CONSTRAINT chk_agent_execution_time
        CHECK (
            finished_at IS NULL
            OR started_at IS NULL
            OR finished_at >= started_at
        )
);

CREATE INDEX idx_user_preference_user_id
    ON user_preference(user_id);

CREATE INDEX idx_user_preference_type
    ON user_preference(preference_type);

CREATE INDEX idx_conversation_user_id
    ON conversation(user_id);

CREATE INDEX idx_message_conversation_created
    ON message(conversation_id, created_at);

CREATE INDEX idx_recommendation_request_conversation
    ON recommendation_request(conversation_id);

CREATE INDEX idx_recommendation_run_request
    ON recommendation_run(request_id);

CREATE INDEX idx_recommendation_run_status
    ON recommendation_run(status);

CREATE INDEX idx_content_media_type
    ON content(media_type);

CREATE INDEX idx_content_release_date
    ON content(release_date);

CREATE INDEX idx_content_tmdb_refreshed_at
    ON content(tmdb_refreshed_at);

CREATE INDEX idx_content_embedding_model_version
    ON content_embedding(
        embedding_model,
        model_version,
        source_language
    );

CREATE INDEX idx_content_embedding_hnsw_cosine
    ON content_embedding
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX idx_run_candidate_run_id
    ON run_candidate(run_id);

CREATE INDEX idx_run_candidate_content_id
    ON run_candidate(content_id);

CREATE INDEX idx_run_candidate_status
    ON run_candidate(run_id, status);

CREATE INDEX idx_run_candidate_final_rank
    ON run_candidate(run_id, final_rank)
    WHERE final_rank IS NOT NULL;

CREATE INDEX idx_interaction_user_id
    ON interaction(user_id);

CREATE INDEX idx_interaction_content_id
    ON interaction(content_id);

CREATE INDEX idx_interaction_user_created
    ON interaction(user_id, created_at DESC);

CREATE INDEX idx_agent_execution_run_id
    ON agent_execution(run_id);

CREATE INDEX idx_recommendation_request_context_gin
    ON recommendation_request
    USING GIN (extracted_context);

CREATE INDEX idx_recommendation_request_constraints_gin
    ON recommendation_request
    USING GIN (constraints);

CREATE INDEX idx_content_metadata_gin
    ON content
    USING GIN (metadata);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_user_profile_updated_at
BEFORE UPDATE ON user_profile
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_user_preference_updated_at
BEFORE UPDATE ON user_preference
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_conversation_updated_at
BEFORE UPDATE ON conversation
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_content_embedding_updated_at
BEFORE UPDATE ON content_embedding
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

COMMIT;
