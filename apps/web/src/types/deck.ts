import type { Card } from "./card";

export interface DeckCard {
  id: string;
  card_id: string;
  zone: "main" | "extra" | "side";
  quantity: number;
  ordering: number;
  notes: string | null;
  card?: Card;
}

export interface Deck {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  format: string;
  visibility: string;
  archetype: string | null;
  tags: string[] | null;
  main_count: number;
  extra_count: number;
  side_count: number;
  created_at: string;
  updated_at: string;
}

export interface DeckDetail extends Deck {
  cards: DeckCard[];
}

export interface DeckVersion {
  id: string;
  deck_id: string;
  version_number: number;
  note: string | null;
  deck_snapshot: Record<string, unknown>;
  created_at: string;
}
