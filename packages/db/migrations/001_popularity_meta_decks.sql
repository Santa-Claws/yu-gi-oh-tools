-- Migration 001: Add popularity_score to cards + meta_decks table
-- Run via: docker compose exec db psql -U postgres -d yugioh_tools -f /migrations/001_popularity_meta_decks.sql

ALTER TABLE cards
  ADD COLUMN IF NOT EXISTS popularity_score FLOAT NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_cards_popularity_score ON cards (popularity_score DESC);

CREATE TABLE IF NOT EXISTS meta_decks (
  id                     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name                   TEXT NOT NULL,
  archetype              TEXT,
  format                 TEXT NOT NULL DEFAULT 'tcg',
  tier                   TEXT,
  source_name            TEXT,
  source_url             TEXT,
  win_rate               FLOAT,
  tournament_appearances INTEGER NOT NULL DEFAULT 0,
  key_card_ids           UUID[],
  description            TEXT,
  extra_data             JSONB NOT NULL DEFAULT '{}',
  scraped_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_meta_decks_format_tier ON meta_decks (format, tier);
CREATE INDEX IF NOT EXISTS idx_meta_decks_scraped_at  ON meta_decks (scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_meta_decks_archetype   ON meta_decks (archetype);
