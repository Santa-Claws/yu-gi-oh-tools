-- Seed meta sources
INSERT INTO meta_sources (source_type, source_name, source_url, reliability_score) VALUES
  ('official_api',        'YGOProDeck API',         'https://db.ygoprodeck.com/api/v7', 1.0),
  ('official_site',       'Konami Card Database',   'https://www.db.yugioh-card.com',   0.95),
  ('tournament_results',  'YGOrganization',         'https://ygorganization.com',        0.85),
  ('meta_site',           'Yugipedia',              'https://yugipedia.com',             0.80),
  ('community_deck',      'DuelLinksMeta',          'https://www.duellinksmeta.com',     0.75),
  ('community_deck',      'MasterDuelMeta',         'https://www.masterduelmeta.com',    0.75);
