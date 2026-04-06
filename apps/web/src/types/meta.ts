import type { Card } from "./card";

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
  key_cards: Card[];
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
