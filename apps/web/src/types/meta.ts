import type { Card } from "./card";

export interface MetaDeckCard {
  card_id: string;
  zone: string;
  quantity: number;
  ordering: number;
  card: Card | null;
}

export interface MetaDeck {
  id: string;
  name: string;
  archetype: string | null;
  format: string;
  tier: "S" | "A" | "B" | "C" | null;
  source_name: string | null;
  source_url: string | null;
  win_rate: number | null;
  tournament_appearances: number;
  has_full_list: boolean;
  key_cards: Card[];
  main_deck: MetaDeckCard[];
  extra_deck: MetaDeckCard[];
  side_deck: MetaDeckCard[];
  description: string | null;
  scraped_at: string | null;
}

export interface MetaDecksResult {
  decks: MetaDeck[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
