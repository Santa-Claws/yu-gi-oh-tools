-- ─── Enums ────────────────────────────────────────────────────────────────────

CREATE TYPE card_type AS ENUM (
  'monster', 'spell', 'trap'
);

CREATE TYPE monster_type AS ENUM (
  'normal', 'effect', 'ritual', 'fusion', 'synchro', 'xyz', 'link',
  'pendulum', 'token', 'flip', 'spirit', 'union', 'gemini', 'tuner'
);

CREATE TYPE card_attribute AS ENUM (
  'dark', 'light', 'earth', 'water', 'fire', 'wind', 'divine'
);

CREATE TYPE ban_status AS ENUM (
  'unlimited', 'semi-limited', 'limited', 'forbidden'
);

CREATE TYPE deck_zone AS ENUM (
  'main', 'extra', 'side'
);

CREATE TYPE job_status AS ENUM (
  'pending', 'running', 'completed', 'failed', 'cancelled'
);

CREATE TYPE job_type AS ENUM (
  'scrape', 'import', 'index', 'embed'
);

CREATE TYPE source_type AS ENUM (
  'official_api', 'official_site', 'tournament_results', 'meta_site',
  'forum', 'reddit', 'community_deck'
);

CREATE TYPE user_role AS ENUM (
  'user', 'admin'
);

-- ─── Users ────────────────────────────────────────────────────────────────────

CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email         TEXT NOT NULL UNIQUE,
  password_hash TEXT,
  display_name  TEXT,
  role          user_role NOT NULL DEFAULT 'user',
  preferences   JSONB NOT NULL DEFAULT '{}',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Cards ────────────────────────────────────────────────────────────────────

CREATE TABLE cards (
  id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  -- source IDs from external APIs
  ygoprodeck_id    INTEGER UNIQUE,
  konami_id        TEXT,

  name_en          TEXT NOT NULL,
  name_ja          TEXT,
  card_type        card_type NOT NULL,
  monster_type     monster_type,
  race             TEXT,          -- e.g. "Warrior", "Dragon", "Continuous"
  attribute        card_attribute,
  level            SMALLINT,
  rank             SMALLINT,
  link_rating      SMALLINT,
  link_markers     TEXT[],        -- ["Top", "Bottom-Left", ...]
  pendulum_scale   SMALLINT,
  atk              INTEGER,
  def              INTEGER,
  effect_text      TEXT,
  pendulum_text    TEXT,
  flavor_text      TEXT,          -- for normal monsters
  archetype        TEXT,
  tcg_ban_status   ban_status NOT NULL DEFAULT 'unlimited',
  ocg_ban_status   ban_status NOT NULL DEFAULT 'unlimited',
  is_extra_deck    BOOLEAN NOT NULL DEFAULT FALSE,
  views            INTEGER NOT NULL DEFAULT 0,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_cards_name_en ON cards USING GIN (name_en gin_trgm_ops);
CREATE INDEX idx_cards_name_ja ON cards USING GIN (name_ja gin_trgm_ops);
CREATE INDEX idx_cards_archetype ON cards (archetype);
CREATE INDEX idx_cards_card_type ON cards (card_type);
CREATE INDEX idx_cards_attribute ON cards (attribute);
CREATE INDEX idx_cards_level ON cards (level);
CREATE INDEX idx_cards_rank ON cards (rank);
CREATE INDEX idx_cards_link_rating ON cards (link_rating);
CREATE INDEX idx_cards_tcg_ban_status ON cards (tcg_ban_status);
CREATE INDEX idx_cards_ocg_ban_status ON cards (ocg_ban_status);
CREATE INDEX idx_cards_ygoprodeck_id ON cards (ygoprodeck_id);
CREATE INDEX idx_cards_views ON cards (views DESC);

-- ─── Card Prints (sets) ───────────────────────────────────────────────────────

CREATE TABLE card_prints (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  card_id      UUID NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
  set_code     TEXT,
  set_name     TEXT,
  card_number  TEXT,
  rarity       TEXT,
  region       TEXT,             -- 'TCG', 'OCG'
  language     TEXT DEFAULT 'en',
  release_date DATE,
  image_url    TEXT,
  image_url_small TEXT,
  image_url_cropped TEXT,
  official_url TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_card_prints_card_id ON card_prints (card_id);
CREATE INDEX idx_card_prints_set_code ON card_prints (set_code);
CREATE INDEX idx_card_prints_card_number ON card_prints (card_number);

-- ─── Card Embeddings (pgvector) ───────────────────────────────────────────────

CREATE TABLE card_embeddings (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  card_id    UUID NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
  chunk_type TEXT NOT NULL,  -- 'effect', 'name', 'full', 'archetype_note'
  chunk_text TEXT NOT NULL,
  embedding  vector(768),
  metadata   JSONB NOT NULL DEFAULT '{}',
  source     TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_card_embeddings_card_id ON card_embeddings (card_id);
CREATE INDEX idx_card_embeddings_chunk_type ON card_embeddings (chunk_type);
-- HNSW index for fast approximate nearest-neighbor search
CREATE INDEX idx_card_embeddings_vec ON card_embeddings
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- ─── Decks ────────────────────────────────────────────────────────────────────

CREATE TABLE decks (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  description TEXT,
  format      TEXT NOT NULL DEFAULT 'tcg',  -- 'tcg', 'ocg', 'goat', 'speed'
  visibility  TEXT NOT NULL DEFAULT 'private',  -- 'private', 'public'
  archetype   TEXT,
  tags        TEXT[],
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_decks_user_id ON decks (user_id);
CREATE INDEX idx_decks_archetype ON decks (archetype);
CREATE INDEX idx_decks_visibility ON decks (visibility);

-- ─── Deck Versions ────────────────────────────────────────────────────────────

CREATE TABLE deck_versions (
  id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  deck_id        UUID NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
  version_number INTEGER NOT NULL,
  note           TEXT,
  deck_snapshot  JSONB NOT NULL DEFAULT '{}',
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (deck_id, version_number)
);

CREATE INDEX idx_deck_versions_deck_id ON deck_versions (deck_id);

-- ─── Deck Cards ───────────────────────────────────────────────────────────────

CREATE TABLE deck_cards (
  id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  deck_id  UUID NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
  card_id  UUID NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
  zone     deck_zone NOT NULL DEFAULT 'main',
  quantity SMALLINT NOT NULL DEFAULT 1,
  ordering INTEGER NOT NULL DEFAULT 0,
  notes    TEXT
);

CREATE INDEX idx_deck_cards_deck_id ON deck_cards (deck_id);
CREATE INDEX idx_deck_cards_card_id ON deck_cards (card_id);

-- ─── Meta Sources ────────────────────────────────────────────────────────────

CREATE TABLE meta_sources (
  id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_type      source_type NOT NULL,
  source_name      TEXT NOT NULL,
  source_url       TEXT,
  is_active        BOOLEAN NOT NULL DEFAULT TRUE,
  last_scraped_at  TIMESTAMPTZ,
  reliability_score NUMERIC(3,2) NOT NULL DEFAULT 0.5 CHECK (reliability_score BETWEEN 0 AND 1),
  config           JSONB NOT NULL DEFAULT '{}',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Scraped Documents ───────────────────────────────────────────────────────

CREATE TABLE scraped_documents (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_id    UUID NOT NULL REFERENCES meta_sources(id) ON DELETE CASCADE,
  title        TEXT,
  url          TEXT,
  raw_text     TEXT,
  cleaned_text TEXT,
  published_at TIMESTAMPTZ,
  scraped_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  chunk_count  INTEGER NOT NULL DEFAULT 0,
  metadata     JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX idx_scraped_docs_source_id ON scraped_documents (source_id);
CREATE INDEX idx_scraped_docs_scraped_at ON scraped_documents (scraped_at DESC);

-- ─── Document Embeddings (meta/community content) ────────────────────────────

CREATE TABLE document_embeddings (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  doc_id      UUID NOT NULL REFERENCES scraped_documents(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  chunk_text  TEXT NOT NULL,
  embedding   vector(768),
  metadata    JSONB NOT NULL DEFAULT '{}',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_doc_embeddings_doc_id ON document_embeddings (doc_id);
CREATE INDEX idx_doc_embeddings_vec ON document_embeddings
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- ─── Background Jobs ─────────────────────────────────────────────────────────

CREATE TABLE background_jobs (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  job_type     job_type NOT NULL,
  status       job_status NOT NULL DEFAULT 'pending',
  celery_id    TEXT,
  progress     NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
  logs         TEXT,
  error        TEXT,
  payload      JSONB NOT NULL DEFAULT '{}',
  result       JSONB,
  started_at   TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_background_jobs_status ON background_jobs (status);
CREATE INDEX idx_background_jobs_job_type ON background_jobs (job_type);

-- ─── Analytics ───────────────────────────────────────────────────────────────

CREATE TABLE analytics_events (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
  event_type  TEXT NOT NULL,
  payload     JSONB NOT NULL DEFAULT '{}',
  token_count INTEGER,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_analytics_events_user_id ON analytics_events (user_id);
CREATE INDEX idx_analytics_events_event_type ON analytics_events (event_type);
CREATE INDEX idx_analytics_events_created_at ON analytics_events (created_at DESC);

CREATE TABLE search_logs (
  id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id        UUID REFERENCES users(id) ON DELETE SET NULL,
  query_text     TEXT,
  intent         TEXT,
  result_count   INTEGER,
  clicked_card_id UUID REFERENCES cards(id) ON DELETE SET NULL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_search_logs_user_id ON search_logs (user_id);
CREATE INDEX idx_search_logs_created_at ON search_logs (created_at DESC);

-- ─── Updated_at triggers ─────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER cards_updated_at BEFORE UPDATE ON cards
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER decks_updated_at BEFORE UPDATE ON decks
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
